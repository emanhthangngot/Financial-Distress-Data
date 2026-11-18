CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE IF NOT EXISTS ops.pipeline_run_log (
    run_id TEXT PRIMARY KEY,
    dag_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    dataset_name TEXT,
    status TEXT NOT NULL,
    started_ts TIMESTAMPTZ,
    ended_ts TIMESTAMPTZ,
    input_rows BIGINT,
    output_rows BIGINT,
    error_message TEXT,
    created_ts TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'UTC')
);

-- Merged with ml.data_quality_result (F4): one table, `track` names which rubric
-- track produced the row. PK is `check_id` alone — it is already a deterministic
-- hash of (run_id, dataset_name, check_name), so a composite (track, check_id) PK
-- would constrain nothing and only poison the index prefix.
CREATE TABLE IF NOT EXISTS ops.data_quality_result (
    check_id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES ops.pipeline_run_log (run_id),
    track TEXT NOT NULL CHECK (track IN ('mini', 'ml', 'llm')),
    dataset_name TEXT NOT NULL,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    metric_value DOUBLE PRECISION,
    threshold_value DOUBLE PRECISION,
    checked_ts TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'UTC'),
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_data_quality_result_track_checked
    ON ops.data_quality_result (track, checked_ts);

CREATE TABLE IF NOT EXISTS ops.dataset_freshness (
    dataset_name TEXT PRIMARY KEY,
    latest_event_ts TIMESTAMPTZ,
    latest_ingest_ts TIMESTAMPTZ,
    freshness_lag_minutes DOUBLE PRECISION,
    sla_minutes DOUBLE PRECISION,
    status TEXT,
    checked_ts TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'UTC')
);

CREATE TABLE IF NOT EXISTS ops.schema_version_registry (
    dataset_name TEXT,
    schema_version TEXT,
    effective_from_ts TIMESTAMPTZ,
    effective_to_ts TIMESTAMPTZ,
    schema_json JSONB,
    is_current BOOLEAN,
    PRIMARY KEY (dataset_name, schema_version)
);
-- is_current is derived, enforced by a partial unique index — never a write-time
-- filter (mirrors gold.dim_company's uq_dim_company_current).
CREATE UNIQUE INDEX IF NOT EXISTS uq_schema_version_registry_current
    ON ops.schema_version_registry (dataset_name) WHERE is_current;

CREATE TABLE IF NOT EXISTS ops.failed_records (
    record_id TEXT PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    run_id TEXT REFERENCES ops.pipeline_run_log (run_id),
    failure_reason TEXT,
    raw_payload JSONB,
    created_ts TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'UTC')
);

CREATE TABLE IF NOT EXISTS ops.backfill_request (
    backfill_id TEXT PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    status TEXT,
    requested_by TEXT,
    created_ts TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'UTC')
);

CREATE TABLE IF NOT EXISTS ops.source_request_log (
    request_id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES ops.pipeline_run_log (run_id),
    source_system TEXT NOT NULL,
    source_endpoint TEXT,
    ticker TEXT,
    report_period TEXT,
    request_status TEXT NOT NULL,
    http_status_code INTEGER,
    retry_count INTEGER DEFAULT 0,
    raw_payload_hash TEXT,
    error_message TEXT,
    requested_ts TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'UTC')
);

CREATE TABLE IF NOT EXISTS ops.collector_checkpoint (
    collector_name TEXT NOT NULL,
    source_system TEXT NOT NULL,
    checkpoint_key TEXT NOT NULL,
    checkpoint_value TEXT,
    updated_ts TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'UTC'),
    PRIMARY KEY (collector_name, source_system, checkpoint_key)
);

-- v2 contract seed. v1 rows are retained, not deleted (schema_version_registry
-- exists precisely to keep both; this is the first real use of that mechanism).
INSERT INTO ops.schema_version_registry
    (dataset_name, schema_version, effective_from_ts, effective_to_ts, schema_json, is_current)
VALUES
    (
        'companies',
        'v1',
        (now() AT TIME ZONE 'UTC'),
        NULL,
        '{"required": ["ticker", "company_name", "exchange", "created_ts"], "nullable": ["industry", "sector", "listing_date", "delisted_flag", "company_size"]}'::jsonb,
        FALSE
    ),
    (
        'financial_statements',
        'v1',
        (now() AT TIME ZONE 'UTC'),
        NULL,
        '{"required": ["ticker", "report_period", "fiscal_year", "fiscal_quarter", "total_assets", "total_liabilities", "equity", "created_ts"], "nullable": ["current_assets", "current_liabilities", "revenue", "ebit", "interest_expense", "net_income", "operating_cash_flow", "retained_earnings", "statement_type", "report_release_date", "event_timestamp"]}'::jsonb,
        FALSE
    ),
    (
        'market_prices_daily',
        'v1',
        (now() AT TIME ZONE 'UTC'),
        NULL,
        '{"required": ["ticker", "trading_date", "close_price", "volume", "created_ts"], "nullable": ["open_price", "high_price", "low_price", "market_cap", "shares_outstanding", "event_timestamp"]}'::jsonb,
        FALSE
    ),
    (
        'stream_events',
        'v1',
        (now() AT TIME ZONE 'UTC'),
        NULL,
        '{"required": ["event_id", "event_type", "ticker", "event_timestamp", "created_ts"], "nullable": ["source_sequence", "raw_payload_hash"]}'::jsonb,
        FALSE
    ),
    (
        'raw_companies',
        'v2',
        (now() AT TIME ZONE 'UTC'),
        NULL,
        '{"required": ["ticker", "source_name", "source_unit", "created_ts", "ingest_batch_id"], "nullable": ["company_name", "exchange"]}'::jsonb,
        TRUE
    ),
    (
        'raw_financial_statements',
        'v2',
        (now() AT TIME ZONE 'UTC'),
        NULL,
        '{"required": ["ticker", "report_period", "source_name", "source_unit", "known_from_ts", "created_ts", "ingest_batch_id"], "nullable": ["total_assets", "total_liabilities", "total_equity"]}'::jsonb,
        TRUE
    ),
    (
        'raw_market_prices_daily',
        'v2',
        (now() AT TIME ZONE 'UTC'),
        NULL,
        '{"required": ["ticker", "trading_date", "source_name", "source_unit", "known_from_ts", "created_ts", "ingest_batch_id"], "nullable": ["close_price"]}'::jsonb,
        TRUE
    )
ON CONFLICT (dataset_name, schema_version) DO NOTHING;

-- W10: hot-path indexes for batch lookups on pipeline_run_log, data_quality_result, failed_records.
-- Created idempotently so re-running init is safe.

CREATE INDEX IF NOT EXISTS idx_pipeline_run_log_dag_status_created
    ON ops.pipeline_run_log (dag_id, status, created_ts);

CREATE INDEX IF NOT EXISTS idx_pipeline_run_log_dataset_created
    ON ops.pipeline_run_log (dataset_name, created_ts);

CREATE INDEX IF NOT EXISTS idx_data_quality_result_dataset_checked
    ON ops.data_quality_result (dataset_name, checked_ts);

CREATE INDEX IF NOT EXISTS idx_data_quality_result_run_id
    ON ops.data_quality_result (run_id);

CREATE INDEX IF NOT EXISTS idx_failed_records_dataset_created
    ON ops.failed_records (dataset_name, created_ts);

CREATE INDEX IF NOT EXISTS idx_failed_records_run_id
    ON ops.failed_records (run_id);
