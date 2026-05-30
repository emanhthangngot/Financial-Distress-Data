# 02 Schema Design — Stage 1

## Objective

Stage 1 uses a local Medallion Architecture with MinIO Parquet, PySpark local mode, PostgreSQL operational metadata, and DuckDB query views.

## Storage Layers

Bronze is append-only and preserves raw payload fields with `ingest_ts`, `source_name`, `batch_id`, and source offset or file name.

Silver standardizes names, casts types, handles schema evolution, deduplicates by business key plus latest `created_ts`, and routes invalid records to `project_metadata.failed_records`.

Gold provides dimensions, facts, OBT, and feature tables for DuckDB analysis and Phase 2 readiness.

## Deterministic Keys

`company_key` is deterministic:

```text
company_key = sha256(ticker).hexdigest()[:16]
```

Facts store `company_key` and `date_key` only. Facts do not store `company_version_key`.

`date_key` is deterministic integer `YYYYMMDD`.

`dim_company` uses SCD Type 2 rows. Analysts and OBT builders resolve company history by joining:

```text
dim_company.company_key = fact.company_key
AND dim_company.valid_from_ts <= fact_reference_ts
AND (fact_reference_ts < dim_company.valid_to_ts OR dim_company.valid_to_ts IS NULL)
```

`fact_reference_ts`:

- `report_release_date` for financial statement facts
- `trading_date` for market price facts
- `event_timestamp` for news sentiment facts

## Gold Tables

### dim_company

Grain: one row per company SCD2 version.

Columns: `company_key`, `ticker`, `company_name`, `exchange`, `industry`, `sector`, `listing_date`, `delisted_flag`, `valid_from_ts`, `valid_to_ts`, `is_current`.

SCD2 tracked fields: `industry`, `sector`, `exchange`, `delisted_flag`.

Stage 1 may rebuild the dimension deterministically from snapshots, but `company_key` must not change across runs.

### dim_date

Grain: one row per date.

Columns: `date_key`, `calendar_date`, `day_of_week`, `month`, `quarter`, `year`, `is_weekend`.

### fact_financial_statement

Grain: one row per company per report period.

Columns include `company_key`, `date_key`, `ticker`, `report_period`, `fiscal_year`, `fiscal_quarter`, `total_assets`, `total_liabilities`, `equity`, `revenue`, `ebit`, `interest_expense`, `net_income`, `operating_cash_flow`, `current_assets`, `current_liabilities`, `retained_earnings`, `statement_type`, `report_release_date`, `event_timestamp`, `created_ts`.

`statement_type` is nullable and distinguishes consolidated from standalone statements when the source exposes that field.

### fact_market_price

Grain: one row per company per trading date.

Columns include `company_key`, `date_key`, `ticker`, `trading_date`, `open_price`, `high_price`, `low_price`, `close_price`, `volume`, `market_cap`, `daily_return`, `volatility_signal`, `event_timestamp`, `created_ts`.

### fact_news_sentiment

Grain: one row per news event.

Columns include `company_key`, `date_key`, `event_id`, `ticker`, `event_timestamp`, `sentiment_score`, `risk_keyword_flag`, `severity_score`, `created_ts`.

### obt_company_quarter_risk

Grain: one row per ticker per report period.

The OBT joins financial facts to market and news aggregates using a 30-day window ending at `report_release_date`. It includes financial ratios, 30-day market signals, 30-day news signals, and `distress_labels`.

Distress label fields include `distress_label`, `distress_reason`, `z_score`, `label_source`, `label_confidence`, and `training_eligible`. `label_source = rule_based_v1` marks these labels as proxy indicators rather than ground-truth bankruptcy outcomes.

### Feature Tables

- `feat_company_financial_4q`
- `feat_company_market_30d`
- `feat_company_news_30d`
- `feat_company_unified`

`feat_company_unified` must enforce point-in-time correctness: no feature row with `feature.event_timestamp > reference.event_timestamp`.

## Schema Registry

`project_metadata.schema_version_registry` is seeded during bootstrap and read by Bronze-to-Silver jobs at runtime. Older Bronze partitions missing evolved nullable fields, such as `retained_earnings`, are accepted and written to Silver with nulls.

## Data Quality

Critical checks halt downstream tasks:

- schema matches current registry
- primary keys are not null
- primary keys are unique
- fact `company_key` exists in `dim_company`
- fact `date_key` exists in `dim_date`

Warning checks route flagged records to `failed_records` and allow processing:

- non-critical value ranges
- mild freshness lag
- new ticker referential mismatch during collector catch-up
- Silver ticker retention below 80 percent of Bronze
- row-count drop above 50 percent from prior run

All checks write rows to `project_metadata.data_quality_result`.
Freshness checks also upsert the latest dataset status into `project_metadata.dataset_freshness`.

## SLA And Backfill

Targets:

- Bronze offline freshness: manual or daily
- Bronze streaming freshness: <= 10 minutes
- Silver refresh: <= 30 minutes
- Gold refresh: <= 60 minutes
- Feature refresh: <= 60 minutes

Backfill is manual for selected dates or quarters. Silver and Gold backfills overwrite affected partitions and must not duplicate records.

## Serving And Evidence

DuckDB uses `httpfs` to query MinIO Parquet. Evidence includes DuckDB query outputs, DBeaver screenshots of PostgreSQL metadata, MinIO screenshots, Kafka logs, Airflow DAG run evidence, DQ reports, and row counts.
