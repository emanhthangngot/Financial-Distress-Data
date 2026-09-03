# Data Model

Unified data-model contract for the platform. This document is the single source of truth for bronze/silver/gold zones, the surrogate-key scheme, SCD2 semantics, and the feature/event_timestamp convention.

## Summary

# Schema Design

## Zones And Naming

Physical datasets use `bronze.<noun>`, `silver.<noun>`, and Gold prefixes
`dim_`, `fact_`, `obt_`, or `feat_`. The generated reviewer database contains
three Bronze, three Silver, and nine Gold tables.

## Relationships

Gold facts and the quarterly risk OBT reference both
`dim_company.company_version_key` and `dim_date.date_key`. Stable
`company_key` identifies a company across history; `company_version_key`
identifies one SCD2 version.

## SCD Type 2

`dim_company` retains `valid_from_ts`, nullable `valid_to_ts`, and
`is_current`. The evidence fixture contains two versions for `AAA` and exactly
one current row.

## Feature Contract

Every `feat_company_*` table includes literal `event_timestamp` and
`created_ts` columns. The unified table also has `feature_event_timestamp` and a
database check enforcing it is not later than the reference event.

## Reproduction

```bash
python scripts/build_schema_evidence.py \
  --output warehouse.db \
  --report docs/evidence/schema/phase8-schema-audit.json
```

Open `warehouse.db` in DBeaver and inspect the `bronze`, `silver`, and `gold`
schemas. The generated audit records 15 tables, six foreign keys, feature
timestamp coverage, and SCD2 history.

---

## Full specification

# 02 Schema Design - Stage 1 As-Built Contract

## Objective

Stage 1 implements a local Medallion lakehouse using MinIO Parquet, PySpark local mode, PostgreSQL operational metadata, and DuckDB `httpfs` views. The schema is designed for coursework evidence first: every table, key, and quality rule must be inspectable locally through tests, Airflow, MinIO, PostgreSQL, DuckDB, or DBeaver.

This document is constrained to Phase 1. It must not introduce AWS services, Kubernetes, ML training, drift monitoring, or online inference.

## Storage And Runtime Layout

Default bucket:

```text
financial-distress-lake
```

Default local MinIO endpoint:

```text
http://minio:9000
```

Host-side DuckDB evidence uses:

```text
s3_endpoint='localhost:9000'
s3_url_style='path'
s3_use_ssl=false
```

Implemented object layout:

```text
bronze/companies/data.parquet
bronze/financial_statements/data.parquet
bronze/market_prices_daily/data.parquet
bronze/kafka/{topic}/event_date=YYYY-MM-DD/event_hour=HH/batch_id={uuid}/data.parquet

silver/companies/
silver/financial_statements/
silver/market_prices_daily/

gold/dim_company/
gold/dim_date/
gold/fact_financial_statement/
gold/fact_market_price/
gold/fact_market_alert/
gold/fact_news_sentiment/
gold/distress_labels/
gold/obt_company_quarter_risk/
gold/feat_company_financial_4q/
gold/feat_company_market_30d/
gold/feat_company_news_30d/
gold/feat_company_unified/

evidence/stage1/run_id={run_id}/
```

Bronze is append-compatible and preserves source fields plus ingestion metadata. The current batch evidence writer uses deterministic `data.parquet` objects for small fixtures; the streaming path uses event date, event hour, and batch ID partitions.

Silver and Gold jobs overwrite their output prefixes in the current real E2E runner. Spark runtime config enables dynamic partition overwrite for future partitioned writes.

Acceptance criteria:

```text
Spark lakehouse job -> reruns Silver and Gold build -> output prefixes are overwritten before new Gold evidence is written.
DuckDB validation runner -> reads Gold objects -> uses local MinIO through httpfs and path-style S3 access.
Maintainer -> lists MinIO objects -> sees Bronze, Silver, Gold, and evidence prefixes under financial-distress-lake.
```

## Gold Naming Convention

The Gold layer uses a single naming rule, enforced by
`tests/test_naming_convention.py`. Both the DuckDB-side view names and
the MinIO-side storage paths follow the same rule, so the two never
drift apart.

### DuckDB View Names

Every `CREATE OR REPLACE VIEW` statement in
`sql/duckdb_create_views.sql` matches
`gold_{dim_|fact_|obt_|feat_}*`:

| View prefix | Layer | Example |
| --- | --- | --- |
| `gold_dim_` | Conformed dimension | `gold_dim_company`, `gold_dim_date` |
| `gold_fact_` | Event or measurement fact | `gold_fact_financial_statement`, `gold_fact_market_price`, `gold_fact_market_alert`, `gold_fact_news_sentiment` |
| `gold_obt_` | One-big-table denormalized join | `gold_obt_company_quarter_risk` |
| `gold_feat_` | Model-ready feature | `gold_feat_company_financial_4q`, `gold_feat_company_market_30d`, `gold_feat_company_news_30d`, `gold_feat_company_unified` |

### MinIO Storage Paths

Gold writes in `src/jobs/stage1_spark_lakehouse_job.py` go to one of
the allowed layer folders under `gold/`:

```text
s3a://financial-distress-lake/gold/dim_*/
s3a://financial-distress-lake/gold/fact_*/
s3a://financial-distress-lake/gold/obt_*/
s3a://financial-distress-lake/gold/feat_*/
s3a://financial-distress-lake/gold/distress_labels/
```

`distress_labels` is the only Gold folder that does not use the
`dim_/fact_/obt_/feat_` family because it carries the label targets
that the platform .L training reads; it is intentionally a single
top-level folder so the labels are easy to discover and audit.

### Bronze And Silver Naming

The rubric convention for Bronze and Silver is the `raw_` / `stg_`
prefix (or equivalent). This project satisfies it with a
**schema-qualified layer prefix** instead of a per-table prefix: the
layer is the leading name segment, so `raw_<noun>` maps to
`bronze.<noun>` and `stg_<noun>` maps to `silver.<noun>`. The mapping
is enforced by `tests/test_naming_convention.py`.

| Rubric equivalent | This project | Physical object |
| --- | --- | --- |
| `raw_companies` | `bronze.companies` | `s3a://financial-distress-lake/bronze/companies/data.parquet` |
| `raw_financial_statements` | `bronze.financial_statements` | `s3a://financial-distress-lake/bronze/financial_statements/data.parquet` |
| `raw_market_prices_daily` | `bronze.market_prices_daily` | `s3a://financial-distress-lake/bronze/market_prices_daily/data.parquet` |
| `stg_companies` | `silver.companies` | `s3a://financial-distress-lake/silver/companies/` |
| `stg_financial_statements` | `silver.financial_statements` | `s3a://financial-distress-lake/silver/financial_statements/` |
| `stg_market_prices_daily` | `silver.market_prices_daily` | `s3a://financial-distress-lake/silver/market_prices_daily/` |

Bronze and Silver storage paths do not enforce a per-table prefix
inside the layer folder — the dataset name is the only segment:

```text
s3a://financial-distress-lake/bronze/{dataset}/data.parquet
s3a://financial-distress-lake/silver/{dataset}/
```

This keeps the raw ingest and dedup layers flexible enough to absorb
new source adapters without forcing a schema rename on every
addition. Gold uses the explicit `dim_`/`fact_`/`obt_`/`feat_`
prefixes documented above, so the three zones are unambiguous:
`raw_`-equivalent (Bronze), `stg_`-equivalent (Silver), and the four
Gold families.

## Schema Registry

Authoritative files:

```text
src/metadata/schema_registry.py
sql/init_ops.sql
```

Current registry datasets:

- `companies`
- `financial_statements`
- `market_prices_daily`
- `stream_events`

`ops.schema_version_registry` is seeded during PostgreSQL bootstrap. Bronze-to-Silver code accepts older Bronze rows missing nullable fields and writes those nullable fields as nulls in Silver.

## Bronze To Silver Semantics

Implemented helpers:

```text
src/transforms/silver/core.py
src/transforms/silver/bronze_to_silver_spark.py
src/transforms/bronze_to_silver.py
```

Silver processing:

- lowercases and trims column names
- checks required fields
- adds missing nullable fields in Spark mode
- routes invalid rows to a failed-record structure
- deduplicates by business key using the latest `created_ts`

Business keys:

| Dataset | Business key |
|---|---|
| `companies` | `ticker` |
| `financial_statements` | `ticker`, `report_period` |
| `market_prices_daily` | `ticker`, `trading_date` |
| streaming events | `event_id` for event facts |

Failed records are persisted to `ops.failed_records` when DQ or metadata writers are invoked by runtime jobs.

## Deterministic Keys

Implemented in `src/transforms/keys.py`.

`company_key`:

```text
company_key = sha256(upper(ticker)).hexdigest()[:16]
```

`date_key`:

```text
date_key = YYYYMMDD integer
```

Facts store `company_key` and `date_key`. They do not store a separate `company_version_key`.

`dim_company` uses SCD Type 2 semantics. Analysts and OBT builders resolve company history with:

```text
dim_company.company_key = fact.company_key
AND dim_company.valid_from_ts <= fact_reference_ts
AND (fact_reference_ts < dim_company.valid_to_ts OR dim_company.valid_to_ts IS NULL)
```

Reference timestamps:

- financial statement facts: `report_release_date`, then `event_timestamp`, then fiscal-year fallback
- market price facts: `trading_date`
- news and alert facts: `event_timestamp`

## Gold Tables

Implemented builders live under `src/transforms/gold/` and are exported by `src/transforms/silver_to_gold.py`.

### dim_company

Builder: `src/transforms/gold/dim_company.py`.

Grain: one row per company SCD2 version.

Columns:

```text
company_key
ticker
company_name
exchange
industry
sector
listing_date
delisted_flag
valid_from_ts
valid_to_ts
is_current
```

SCD2 tracked fields:

```text
industry
sector
exchange
delisted_flag
```

### dim_date

Builder: `src/transforms/gold/dim_company.py`.

Grain: one row per calendar date.

Columns:

```text
date_key
calendar_date
day_of_week
month
quarter
year
is_weekend
```

### fact_financial_statement

Builder: `src/transforms/gold/fact_financial_statement.py`.

Grain: one row per company per report period.

The builder uppercases `ticker`, adds deterministic `company_key`, and derives `date_key` from `report_release_date`, `event_timestamp`, or fiscal-year fallback.

Key columns include:

```text
company_key
date_key
ticker
report_period
fiscal_year
fiscal_quarter
total_assets
total_liabilities
equity
current_assets
current_liabilities
revenue
ebit
interest_expense
net_income
operating_cash_flow
retained_earnings
statement_type
report_release_date
event_timestamp
created_ts
```

### fact_market_price

Builder: `src/transforms/gold/fact_market_price.py`.

Grain: one row per company per trading date.

The builder uppercases `ticker`, adds deterministic keys, calculates `daily_return` from the previous close per ticker, and flags `volatility_signal` when absolute daily return is greater than `0.07`.

Key columns include:

```text
company_key
date_key
ticker
trading_date
open_price
high_price
low_price
close_price
volume
market_cap
daily_return
volatility_signal
event_timestamp
created_ts
```

### fact_news_sentiment

Builder: `src/transforms/gold/fact_news_sentiment.py`.

Grain: one row per news event.

Key columns:

```text
company_key
date_key
event_id
ticker
event_timestamp
sentiment_score
risk_keyword_flag
severity_score
created_ts
source_url
```

### fact_market_alert

Builder: `src/transforms/gold/fact_market_alert.py`.

Grain: one row per alert event.

The builder deduplicates by `event_id`, uppercases `ticker`, adds deterministic keys, and defaults missing `alert_type` to `unknown`.

Key columns:

```text
company_key
date_key
event_id
ticker
event_timestamp
event_type
alert_type
created_ts
```

### distress_labels

Builder: `src/transforms/compute_distress_labels.py`.

Grain: one row per ticker per report period.

This table stores rule-based proxy labels:

```text
ticker
report_period
event_timestamp
created_ts
distress_label
distress_reason
z_score
label_source
label_confidence
training_eligible
rule_version
```

### obt_company_quarter_risk

Builder: `src/transforms/gold/obt_company_quarter_risk.py`.

Grain: one row per ticker per report period.

The current implementation joins financial facts to `distress_labels` and computes financial ratios:

```text
current_ratio
debt_to_asset
debt_to_equity
roa
roe
ebit_interest_coverage
distress_label
distress_reason
z_score
label_source
label_confidence
training_eligible
```

The function accepts market facts for extension, but the currently implemented ratio builder does not yet aggregate market windows inside the OBT.

### Feature Tables

Implemented in `src/transforms/features/point_in_time.py`.

Tables:

- `feat_company_financial_4q`
- `feat_company_market_30d`
- `feat_company_news_30d`
- `feat_company_unified`

`feat_company_unified` enforces point-in-time correctness by excluding feature rows whose `feature_event_timestamp` is greater than the reference row `event_timestamp`.

Acceptance criteria:

```text
Feature builder -> receives market rows after a report event_timestamp -> excludes those future rows from feat_company_unified.
DuckDB validation query -> checks future_feature_leakage_rows -> returns zero rows for valid evidence.
```

## PostgreSQL Operational Metadata

DDL file:

```text
sql/init_ops.sql
```

Schema:

```text
ops
```

Implemented tables:

| Table | Purpose |
|---|---|
| `pipeline_run_log` | records DAG/task run status and row counts |
| `data_quality_result` | records DQ check status, severity, metrics, thresholds, and errors |
| `dataset_freshness` | stores latest dataset freshness status |
| `schema_version_registry` | stores current and historical schema contracts |
| `failed_records` | stores invalid or warning-routed payloads |
| `backfill_request` | records local backfill requests and status |
| `source_request_log` | records collector/source calls, retries, raw payload hashes, and errors |
| `collector_checkpoint` | stores collector checkpoints per source and checkpoint key |

Metadata writers:

```text
src/metadata/metadata_writer.py
```

The repository includes both in-memory and PostgreSQL metadata writers. Tests use in-memory writers where possible; runtime evidence uses `PostgresMetadataWriter`.

## Data Quality

Implemented checks:

```text
src/quality/dq_checks.py
src/quality/dq_runner.py
src/jobs/stage1_dq_job.py
configs/dq_rules.yaml
```

Critical checks:

- required keys are not null
- primary or business keys are unique
- fact foreign keys exist in dimensions where referential checks are configured

Warning checks:

- freshness lag exceeds SLA
- Silver retention below configured threshold
- non-critical quality gates configured in `configs/dq_rules.yaml`

All runtime checks write to `ops.data_quality_result` through the metadata writer. Freshness checks can also update `ops.dataset_freshness`.

Policy:

```text
DQ runner -> sees a critical failure -> raises RuntimeError and halts downstream processing.
DQ runner -> sees warning results only -> logs warnings and allows downstream processing.
DQ writer -> records any DQ result -> persists dataset_name, check_name, status, severity, metric_value, threshold_value, checked_at, and error_message.
```

## DuckDB Serving And Validation

DuckDB artifacts:

```text
src/catalog/duckdb_catalog.py
src/catalog/duckdb_runner.py
sql/duckdb_create_views.sql
sql/duckdb_validation_queries.sql
```

Implemented DuckDB Gold views:

- `gold_dim_company`
- `gold_dim_date`
- `gold_fact_financial_statement`
- `gold_fact_market_price`
- `gold_fact_market_alert`
- `gold_fact_news_sentiment`
- `gold_obt_company_quarter_risk`
- `gold_feat_company_financial_4q`
- `gold_feat_company_market_30d`
- `gold_feat_company_news_30d`
- `gold_feat_company_unified`

`gold_dim_company` is exposed for DBeaver ER inspection and SCD2 temporal joins.

Validation queries check:

- financial statement row counts
- duplicate financial statement keys
- distress label distribution
- `dim_company` row counts
- `dim_date` row counts
- news and alert fact row counts
- feature table row counts
- future feature leakage in `gold_feat_company_unified`

## Airflow Evidence DAGs

Implemented DAGs:

| DAG | Purpose |
|---|---|
| `stage1_local_evidence_pipeline` | lightweight fixture-backed evidence materialization |
| `stage1_real_e2e_pipeline` | local service E2E through Bronze, Kafka, Spark, DQ, PostgreSQL, DuckDB, and MinIO evidence |

The real E2E DAG task chain is:

```text
materialize_bronze_batch_objects
produce_fixture_stream_events_to_kafka
consume_kafka_events_to_bronze
run_spark_bronze_to_silver_gold
run_silver_gold_dq_gate
write_project_metadata_rows
run_duckdb_validation_and_publish_evidence
```

## SLA And Backfill

platform .argets:

- Bronze offline freshness: manual or daily
- Bronze streaming freshness: <= 10 minutes
- Silver refresh: <= 30 minutes
- Gold refresh: <= 60 minutes
- Feature refresh: <= 60 minutes

Backfill is manual for selected dates or quarters. Silver and Gold backfills must overwrite affected output prefixes or partitions and must not duplicate records.

## Evidence Targets

Committed and generated evidence may include:

- `docs/evidence/stage1_row_counts.json`
- `docs/evidence/stage1_minio_objects.txt`
- `docs/evidence/stage1_stream_batches.json`
- `docs/evidence/stage1_real_postgres_summary.json`
- `docs/evidence/stage1_real_duckdb_validation.json`
- `docs/evidence/stage1_real_minio_objects.json`
- `docs/evidence/stage1_real_kafka_offsets.json`
- `docs/evidence/stage1_runtime_audit_summary.json`
- MinIO evidence artifacts under `evidence/stage1/run_id=...`
- DBeaver screenshots or query exports from PostgreSQL and DuckDB when required for coursework submission

Verification commands:

```text
pytest
python scripts/run_stage1_quality_gate.py
python scripts/run_stage1_real_e2e.py
```

Use the smallest command that verifies the changed behavior. Documentation-only changes can be verified by reviewing this file against the listed source artifacts.
