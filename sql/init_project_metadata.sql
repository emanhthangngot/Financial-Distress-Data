CREATE SCHEMA IF NOT EXISTS project_metadata;

CREATE TABLE IF NOT EXISTS project_metadata.pipeline_run_log (
    run_id TEXT PRIMARY KEY,
    dag_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    dataset_name TEXT,
    status TEXT NOT NULL,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    input_rows BIGINT,
    output_rows BIGINT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_metadata.data_quality_result (
    check_id TEXT PRIMARY KEY,
    run_id TEXT,
    dataset_name TEXT NOT NULL,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    metric_value DOUBLE PRECISION,
    threshold_value DOUBLE PRECISION,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS project_metadata.dataset_freshness (
    dataset_name TEXT PRIMARY KEY,
    latest_event_timestamp TIMESTAMP,
    latest_ingest_ts TIMESTAMP,
    freshness_lag_minutes DOUBLE PRECISION,
    sla_minutes DOUBLE PRECISION,
    status TEXT,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_metadata.schema_version_registry (
    dataset_name TEXT,
    schema_version TEXT,
    effective_from TIMESTAMP,
    effective_to TIMESTAMP,
    schema_json JSONB,
    is_current BOOLEAN,
    PRIMARY KEY (dataset_name, schema_version)
);

CREATE TABLE IF NOT EXISTS project_metadata.failed_records (
    record_id TEXT PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    run_id TEXT,
    failure_reason TEXT,
    raw_payload JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_metadata.backfill_request (
    backfill_id TEXT PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    status TEXT,
    requested_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_metadata.source_request_log (
    request_id TEXT PRIMARY KEY,
    run_id TEXT,
    source_system TEXT NOT NULL,
    source_endpoint TEXT,
    ticker TEXT,
    report_period TEXT,
    request_status TEXT NOT NULL,
    http_status_code INTEGER,
    retry_count INTEGER DEFAULT 0,
    raw_payload_hash TEXT,
    error_message TEXT,
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_metadata.collector_checkpoint (
    collector_name TEXT NOT NULL,
    source_system TEXT NOT NULL,
    checkpoint_key TEXT NOT NULL,
    checkpoint_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (collector_name, source_system, checkpoint_key)
);

INSERT INTO project_metadata.schema_version_registry
    (dataset_name, schema_version, effective_from, effective_to, schema_json, is_current)
VALUES
    (
        'companies',
        'v1',
        CURRENT_TIMESTAMP,
        NULL,
        '{"required": ["ticker", "company_name", "exchange", "created_ts"], "nullable": ["industry", "sector", "listing_date", "delisted_flag", "company_size"]}'::jsonb,
        TRUE
    ),
    (
        'financial_statements',
        'v1',
        CURRENT_TIMESTAMP,
        NULL,
        '{"required": ["ticker", "report_period", "fiscal_year", "fiscal_quarter", "total_assets", "total_liabilities", "equity", "created_ts"], "nullable": ["current_assets", "current_liabilities", "revenue", "ebit", "interest_expense", "net_income", "operating_cash_flow", "retained_earnings", "statement_type", "report_release_date", "event_timestamp"]}'::jsonb,
        TRUE
    ),
    (
        'market_prices_daily',
        'v1',
        CURRENT_TIMESTAMP,
        NULL,
        '{"required": ["ticker", "trading_date", "close_price", "volume", "created_ts"], "nullable": ["open_price", "high_price", "low_price", "market_cap", "shares_outstanding", "event_timestamp"]}'::jsonb,
        TRUE
    ),
    (
        'stream_events',
        'v1',
        CURRENT_TIMESTAMP,
        NULL,
        '{"required": ["event_id", "event_type", "ticker", "event_timestamp", "created_ts"], "nullable": ["source_sequence", "raw_payload_hash"]}'::jsonb,
        TRUE
    )
ON CONFLICT (dataset_name, schema_version) DO NOTHING;

-- W10: hot-path indexes for batch lookups on pipeline_run_log, data_quality_result, failed_records.
-- Created idempotently so re-running init is safe.

CREATE INDEX IF NOT EXISTS idx_pipeline_run_log_dag_status_created
    ON project_metadata.pipeline_run_log (dag_id, status, created_at);

CREATE INDEX IF NOT EXISTS idx_pipeline_run_log_dataset_created
    ON project_metadata.pipeline_run_log (dataset_name, created_at);

CREATE INDEX IF NOT EXISTS idx_data_quality_result_dataset_checked
    ON project_metadata.data_quality_result (dataset_name, checked_at);

CREATE INDEX IF NOT EXISTS idx_data_quality_result_run_id
    ON project_metadata.data_quality_result (run_id);

CREATE INDEX IF NOT EXISTS idx_failed_records_dataset_created
    ON project_metadata.failed_records (dataset_name, created_at);

CREATE INDEX IF NOT EXISTS idx_failed_records_run_id
    ON project_metadata.failed_records (run_id);
