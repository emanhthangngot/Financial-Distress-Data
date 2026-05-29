# Mini-Coursework Idea Handoff — Financial Distress Data Engineering System

## 0. Document Purpose

This document is the **full idea handoff** for the mini-coursework project.

It is written so that another AI agent, teammate, or developer can understand the complete project direction without reading the previous chat window.

The project is currently in the **mini-coursework phase**, so the scope is intentionally limited to:

```text
01_data_generator.md
02_schema_design.md
```

This document should be used as the main context file for continuing implementation, writing design docs, creating code, or splitting tasks.

---

## 1. One-Sentence Summary

This mini-coursework project builds a **local-first and low-cost Data Engineering system for Financial Distress analytics**, using **Airflow + Kafka + PySpark + PostgreSQL + MinIO + DuckDB locally**. Instead of relying only on synthetic data, the Phase 1 design now uses online Vietnamese market data collectors that call public APIs, supported libraries such as `vnstock`, and WebSocket/polling feeds where available, while still keeping all storage, processing, metadata, and evidence local.

## 2. Project Objective

The objective is to design and implement a mini end-to-end data pipeline that collects and processes financial data for Vietnamese listed companies.

The system prepares a clean, queryable, business-ready data foundation that can later support ML or LLM use cases such as:

```text
Financial distress prediction
Company risk scoring
Early warning system
Financial health monitoring
Investor screening
```

For the mini-coursework, the project does **not** need to train a model yet. It focuses on the data foundation.

---

## 3. Current Mini-Coursework Scope

The mini-coursework focuses only on:

```text
Section 01 — Data Generator
Section 02 — Schema Design and Data Pipeline
```

### Section 01 should include

```text
Offline dataset design
Streaming dataset design
Schema definitions
Data grain
Generation controls
Realistic data issues
Sample generated outputs
```

### Section 02 should include

```text
Bronze/Silver/Gold schema design
Pipeline contracts
Data quality checks
SLA targets
Update policy
Backfill strategy
Gold serving tables/views
Evidence from running pipelines
```

---

## 4. Future Scope, Not Mini-Coursework

These are future extensions only:

```text
03_data_generator_improvement.md
04.1_ml_design_example.md
04.2_llm_design_example.md
```

Do not implement these unless explicitly requested.

Future possible extensions:

```text
Feature drift simulation
ML model training
Batch scoring
Model monitoring
Retraining policy
LLM assistant over financial data
Prediction API
Dashboard
Kubernetes deployment
```

---

## 5. Domain: Financial Distress

The domain is **Financial Distress Prediction / Financial Risk Analytics**.

The project collects financial and market data for listed companies from online sources, then processes that data into clean analytical tables and feature tables.

A company may be labeled as financially distressed if it shows signals such as:

```text
Net loss for multiple periods
Negative equity
Negative retained earnings
Weak operating cash flow
High debt-to-asset ratio
Low current ratio
EBIT not enough to cover interest expense
Strong market price decline
High volatility
Negative financial news
```

The business goal is to identify companies that may be financially risky.

---

## 6. Why This Domain Fits the Coursework

Financial Distress is a good fit because it naturally contains both offline and streaming data.

### Offline/API batch data examples

```text
Company master data
Financial statements
Balance sheet
Income statement
Cash flow statement
Historical market prices
Distress labels
```

### Streaming/WebSocket data examples

```text
Stock price events
Market alert events
News sentiment events
Sudden price drops
Negative news bursts
High-volume trading events
```

This satisfies the mini-coursework requirement that both offline and streaming paths exist. If a source does not expose a reliable WebSocket, the system may use scheduled API polling and publish the normalized event to Kafka; the streaming contract remains Kafka-first inside the local platform.

---

## 7. Reference Inspiration

The project is inspired by the architecture style of this repository:

```text
https://github.com/dongtd6/Sentiment-Classifier-ML-System-on-K8S
```

However, the mini-coursework should **not copy the full complexity** of that repository.

The useful ideas to borrow are:

```text
Local-first development
Docker-based services
Clear pipeline boundaries
Production-oriented mindset
Observability
Data quality checks
CI/CD intent
Service/pipeline separation
```

The project should avoid over-engineering.

---

## 8. Final Architecture Decision

The final architecture is:

```text
100% Local-first Engineering Layer (Docker-based)
+
100% Free Local Object Storage (MinIO) & Local Analytics (DuckDB)
```

### Local layer

```text
Airflow
Kafka single-node KRaft
PySpark local mode
PostgreSQL local
DBeaver
Python scripts
API/WebSocket collectors
MinIO (S3-compatible Object Storage in Docker)
DuckDB (Local SQL Query Engine for Parquet/S3 API)
```

### Removed from mini-coursework (No Cloud Costs)

```text
AWS S3 (Replaced by local MinIO)
AWS Glue Catalog (Replaced by local DuckDB schema/metastore)
AWS Athena (Replaced by local DuckDB/Spark SQL queries)
AWS RDS (Replaced by local PostgreSQL)
EMR
MSK
Redshift
SageMaker
EKS
Full Spark cluster
Kubernetes deployment
```

Important correction:

```text
Do NOT use AWS RDS for metadata or AWS S3 for storage.
Use local PostgreSQL and local MinIO in Docker, and inspect them using DBeaver and DuckDB.
```

---

## 9. Canonical Architecture Statement

The mini-coursework architecture uses a local-first data platform with Airflow, Kafka, PySpark, PostgreSQL, MinIO, and DuckDB running locally in Docker. Airflow orchestrates online API batch collection, WebSocket or polling-based streaming ingestion, Bronze-to-Silver cleaning, PySpark Silver-to-Gold transformation, data quality checks, and metadata publishing. Kafka runs as a lightweight single-node KRaft broker for normalized market/news/alert events collected from online sources. PySpark runs in local mode to build Gold dimension tables, fact tables, OBT tables, and feature tables, writing directly to MinIO.

Local PostgreSQL stores pipeline run logs, quality check results, freshness metrics, failed records, schema versions, and checkpoint state. DBeaver is used to inspect these local metadata tables as coursework evidence.

MinIO is used as the local S3-compatible object storage layer, hosting Bronze, Silver, and Gold Parquet datasets. DuckDB acts as the local query engine, allowing high-performance, Athena-style serverless SQL queries on top of MinIO Parquet files using the DuckDB `httpfs` extension, with results displayed inside DBeaver.

This design demonstrates production-oriented data engineering concepts while remaining local-first and simple to run. The online collectors are isolated behind source adapters so the rest of the lakehouse can still be tested with fixtures when an external API is unavailable.

---

## 10. High-Level Architecture Diagram

```text
                    ┌────────────────────────────────────────────┐
                    │              Local Docker Layer             │
                    │ Airflow + Kafka + PySpark + PostgreSQL +   │
                    │               MinIO + DuckDB               │
                    └─────────────────────┬──────────────────────┘
                                          │
        ┌─────────────────────────────────┼─────────────────────────────────┐
        │                                 │                                 │
┌───────▼────────┐              ┌─────────▼────────┐              ┌─────────▼────────┐
│ API Batch      │              │ WebSocket/API    │              │ Local Metadata   │
│ Financial data │              │ Stock/news feed  │              │ PostgreSQL       │
└───────┬────────┘              └─────────┬────────┘              └─────────┬────────┘
        │                                 │                                 │
        │                                 ▼                                 │
        │                        Kafka Single-Node KRaft                    │
        │             financial.price_events, financial.news_events         │
        │                                 │                                 │
        └────────────────┬────────────────┴────────────────┬────────────────┘
                         │                                 │
                         ▼                                 ▼
                ┌────────────────┐              ┌──────────────────────┐
│ MinIO Bronze   │              │ DBeaver              │
│ raw API payload│              │ inspect PostgreSQL   │
                └───────┬────────┘              └──────────────────────┘
                        │
                        ▼
                ┌────────────────┐
                │ MinIO Bronze   │
                │ raw parquet    │
                └───────┬────────┘
                        │
                        ▼
                ┌────────────────┐
                │ MinIO Silver   │
                │ cleaned data   │
                └───────┬────────┘
                        │
                        ▼
              ┌──────────────────────────────┐
              │ Local PySpark Transform Layer │
              │ Silver → Gold                 │
              │ dims, facts, OBT, features    │
              └───────┬──────────────────────┘
                      │
                      ▼
              ┌────────────────┐
              │ MinIO Gold     │
              │ Parquet tables │
              └───────┬────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
┌────────────────┐         ┌────────────────┐
│ DuckDB Views   │         │ DBeaver SQL    │
│ local metadata │         │ local queries  │
└────────────────┘         └────────────────┘
```

---

## 11. Tool Stack

| Layer | Tool | Purpose |
|---|---|---|
| Data collection | Python, requests/httpx, pandas, vnstock optional | Collect company lists, financial statements, market prices, and raw API payloads |
| Streaming | WebSocket or polling adapters + Kafka KRaft single-node | Collect market/news/alert events and publish normalized events to Kafka |
| Orchestration | Airflow local Docker | Run DAGs and pipeline tasks |
| Batch transformation | PySpark local mode | Build Gold tables from Silver |
| Local metadata | PostgreSQL Docker | Store pipeline logs, DQ results, checkpoints, source requests, and failed tickers |
| DB inspection | DBeaver | Inspect local metadata and query MinIO/DuckDB |
| Local S3 Storage | MinIO Docker | Store Bronze/Silver/Gold Parquet (S3-compatible) |
| Local SQL Queries | DuckDB | Query MinIO Parquet files with Athena-like serverless SQL |
| Data quality | Custom Python checks | Validate data and write logs to Postgres |
| Version control | GitHub | Store code and collaborate |
| IDE | VS Code | Development environment |

---

## 12. Why Local PostgreSQL Instead of AWS RDS

AWS RDS was considered but removed from the mini-coursework architecture.

### Reason

RDS adds unnecessary complexity for a mini-coursework:

```text
VPC setup
Security group setup
Public/private access issue
Cost management
Credential management
Docker-to-AWS database connection
More failure points
```

### Final decision

Use local PostgreSQL in Docker.

It stores:

```text
pipeline_run_log
data_quality_result
dataset_freshness
schema_version_registry
failed_records
backfill_request
```

Use DBeaver to inspect those tables.

This is enough evidence for the mini-coursework.

---

## 13. PostgreSQL and DBeaver

### PostgreSQL role

Local PostgreSQL is used as the operational metadata database.

It should store:

```text
Pipeline run history
Task status
Input/output row counts
DQ check results
Freshness status
Failed records
Schema versions
Backfill requests
```

### Active Schema Registry Runtime Enforcement

The `project_metadata.schema_version_registry` table is not just for logging, but actively enforced by the pipeline during execution:
1. **Dynamic Schema Retrieval**: When `transform_bronze_to_silver` runs, the Python/PySpark script queries `schema_version_registry` using the `dataset_name` and checks for `is_current = TRUE`.
2. **Runtime Validation**: The retrieved `schema_json` is parsed. The script then dynamically casts the incoming Bronze columns to the registered data types and validates that all mandatory fields are present.
3. **Dead-Letter Queue (DLQ) Routing**: If a record has structurally malformed fields or cannot be cast to the registered schema, the record is extracted, the failure reason is written to `failed_records`, and the valid records continue downstream. This protects the Silver layer from corruption.

### DBeaver role

DBeaver is used to inspect PostgreSQL like in the reference architecture image.

For evidence, capture screenshots of:

```text
pipeline_run_log
data_quality_result
dataset_freshness
failed_records
schema_version_registry
source_request_log
collector_checkpoint
```

---

## 14. Metadata Tables

### pipeline_run_log

```sql
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
```

### data_quality_result

```sql
CREATE TABLE IF NOT EXISTS project_metadata.data_quality_result (
    check_id TEXT PRIMARY KEY,
    run_id TEXT,
    dataset_name TEXT NOT NULL,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    metric_value DOUBLE PRECISION,
    threshold_value DOUBLE PRECISION,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT
);
```

### dataset_freshness

```sql
CREATE TABLE IF NOT EXISTS project_metadata.dataset_freshness (
    dataset_name TEXT PRIMARY KEY,
    latest_event_timestamp TIMESTAMP,
    latest_ingest_ts TIMESTAMP,
    freshness_lag_minutes DOUBLE PRECISION,
    sla_minutes DOUBLE PRECISION,
    status TEXT,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### schema_version_registry

```sql
CREATE TABLE IF NOT EXISTS project_metadata.schema_version_registry (
    dataset_name TEXT,
    schema_version TEXT,
    effective_from TIMESTAMP,
    effective_to TIMESTAMP,
    schema_json JSONB,
    is_current BOOLEAN,
    PRIMARY KEY (dataset_name, schema_version)
);
```

### failed_records

```sql
CREATE TABLE IF NOT EXISTS project_metadata.failed_records (
    record_id TEXT PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    run_id TEXT,
    failure_reason TEXT,
    raw_payload JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### backfill_request

```sql
CREATE TABLE IF NOT EXISTS project_metadata.backfill_request (
    backfill_id TEXT PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    status TEXT,
    requested_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### source_request_log

```sql
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
```

### collector_checkpoint

```sql
CREATE TABLE IF NOT EXISTS project_metadata.collector_checkpoint (
    collector_name TEXT NOT NULL,
    source_system TEXT NOT NULL,
    checkpoint_key TEXT NOT NULL,
    checkpoint_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (collector_name, source_system, checkpoint_key)
);
```

---

## 15. Section 01 — Online Data Collector

The collector must create both offline/API-batch and streaming/WebSocket data paths.

Phase 1 no longer depends on synthetic-only generation as the primary source. Synthetic fixtures are still allowed for tests and fallback smoke runs, but the architecture target is online collection for Vietnamese listed companies.

---

## 16. Offline/API Batch Data Design

The offline path is a scheduled batch collector. It calls public or semi-public Vietnamese market data sources such as `vnstock`, HOSE/HNX/UPCOM lists, Vietstock, CafeF, FireAnt, SSI iBoard, TCBS, or VCI endpoints when legally and technically accessible.

Collector requirements:

```text
Use source adapters so each external source has isolated parsing logic.
Use environment variables for credentials, tokens, cookies, and rate-limit settings.
Persist raw API responses to Bronze before normalization.
Record request status, retry count, source URL/key, and failed tickers in PostgreSQL metadata.
Respect robots.txt, website terms, and rate limits; do not bypass authentication or paywalls.
```

Recommended collector modules:

```text
src/collectors/company_list_collector.py
src/collectors/financial_statement_collector.py
src/collectors/market_price_collector.py
src/collectors/source_adapters/vnstock_adapter.py
src/collectors/source_adapters/http_json_adapter.py
src/collectors/source_adapters/html_table_adapter.py
```

### 16.1 companies

Grain:

```text
One row per company / ticker
```

Purpose:

```text
Master data for listed companies.
```

Online source examples:

```text
vnstock listing helpers
HOSE / HNX / UPCOM public lists
SSI / TCBS / VCI / CafeF / Vietstock company endpoints
```

Example columns:

```text
ticker
company_name
exchange
industry
sector
listing_date
delisted_flag
company_size
source_system
source_url
ingest_run_id
raw_payload_hash
created_ts
```

---

### 16.2 financial_statements

Grain:

```text
One row per ticker per report_period
```

Purpose:

```text
Collect quarterly/yearly financial reports from online sources.
```

Example columns:

```text
ticker
report_period
fiscal_year
fiscal_quarter
total_assets
current_assets
cash_and_equivalents
inventory
total_liabilities
current_liabilities
long_term_debt
equity
revenue
gross_profit
ebit
interest_expense
net_income
operating_cash_flow
retained_earnings
report_release_date
event_timestamp
created_ts
schema_version
source_system
source_report_type
source_url
ingest_run_id
raw_payload_hash
```

---

### 16.3 market_prices_daily

Grain:

```text
One row per ticker per trading_day
```

Purpose:

```text
Collect daily stock market data through API/library calls.
```

Example columns:

```text
ticker
trading_date
open_price
high_price
low_price
close_price
volume
market_cap
shares_outstanding
event_timestamp
created_ts
source_system
source_url
ingest_run_id
raw_payload_hash
```

---

### 16.4 distress_labels

Grain:

```text
One row per ticker per report_period
```

Purpose:

```text
Rule-based label table for future ML, derived locally from collected financial data.
```

Example columns:

```text
ticker
report_period
event_timestamp
created_ts
distress_label
distress_reason
z_score
rule_version
```

---

## 17. Streaming Data Design

Streaming data should go through Kafka topics first inside the local platform. The external source may be a WebSocket feed if available, or an API polling adapter that converts fresh market/news observations into Kafka events.

Recommended Kafka topics:

```text
financial.price_events
financial.news_events
financial.alert_events
```

---

### 17.1 stock_price_events

Grain:

```text
One event per ticker per collected market tick or polling interval
```

Example columns:

```text
event_id
event_type
ticker
event_timestamp
created_ts
price
volume
price_change_pct
source
source_system
source_sequence
raw_payload_hash
```

Example event types:

```text
price_update
price_spike
price_drop
volume_spike
```

---

### 17.2 news_sentiment_events

Grain:

```text
One event per news article / ticker mention
```

Example columns:

```text
event_id
event_type
ticker
event_timestamp
created_ts
news_source
headline
sentiment_score
sentiment_label
risk_keyword_flag
```

Example sentiment labels:

```text
positive
neutral
negative
```

---

### 17.3 market_alert_events

Grain:

```text
One event per detected abnormal market signal
```

Example columns:

```text
event_id
event_type
ticker
event_timestamp
created_ts
alert_type
severity
description
```

Example alert types:

```text
large_price_drop
high_volatility
negative_news_cluster
liquidity_warning
```

---

## 18. Realistic Data Issues to Inject

The collectors should expect and handle realistic online data challenges. Synthetic test fixtures should deliberately reproduce these issues so tests remain deterministic.

### 18.1 Skew

```text
70% of companies belong to a few major industries.
Some tickers produce more market events.
Some sectors have higher distress probability.
```

### 18.2 High cardinality

```text
ticker
event_id
news_id
report_period
```

### 18.3 Schema evolution

Older financial statement partitions may not include:

```text
retained_earnings
interest_expense
operating_cash_flow
```

Newer partitions include them.

### 18.4 Duplicates

```text
Duplicate financial statements for same ticker + report_period.
Duplicate Kafka events with same event_id.
Duplicate source payloads from repeated API retries.
```

### 18.5 Missing values

```text
Missing interest_expense.
Missing operating_cash_flow.
Missing market_cap.
Missing industry.
```

### 18.6 Late arrivals

```text
Some streaming events have created_ts later than event_timestamp.
Some financial reports arrive after report period end date.
Some WebSocket events arrive out of order or reconnect with replayed messages.
```

### 18.7 Outliers

```text
Extremely high revenue growth.
Negative equity.
Very high debt ratio.
Sudden price crash.
```

### 18.8 Bursty traffic

```text
Market open/close has high event volume.
Negative news creates event bursts.
WebSocket reconnects create short bursts after downtime.
```

---

## 19. Suggested Collector Config

```yaml
source_mode: online
primary_library: vnstock
fallback_sources:
  - cafe_f
  - vietstock
  - tcbs
  - ssi

markets:
  - HOSE
  - HNX
  - UPCOM
exclude_financial_sector: true

max_companies: 300
start_year: 2018
end_year: 2025
report_frequency: quarterly
trading_days_per_year: 250

request_timeout_seconds: 30
max_retries: 3
retry_backoff_seconds: 5
min_request_delay_seconds: 1
random_delay_jitter_seconds: 2
checkpoint_every_tickers: 25

persist_raw_payload: true
raw_payload_format: json
failed_ticker_policy: write_to_project_metadata_failed_records

stream_source_mode: websocket_or_polling
websocket_reconnect_seconds: 10
poll_interval_seconds: 60
stream_topics:
  price: financial.price_events
  news: financial.news_events
  alert: financial.alert_events

stream_flush_interval_seconds: 60
stream_flush_record_count: 1000

fixture_mode_enabled: true
fixture_seed: 42
```

---

## 20. Kafka Design

Kafka should be simple.

Final decision:

```text
Use single-node Kafka in KRaft mode.
Do not use Zookeeper.
Replication factor = 1.
Small number of partitions.
```

Reason:

```text
Kafka is used to prove the streaming path exists inside the local platform.
It should not become the heaviest part of the mini-coursework.
```

The Kafka consumer should micro-batch events before writing to Bronze.

Recommended flushing rule:

```text
Flush every 1 minute
OR every 1000 records
```

Avoid writing one file per event.

Recommended streaming collector pattern:

```text
External WebSocket/API feed
→ source adapter validates raw payload
→ normalize to canonical event schema
→ publish to Kafka topic
→ consumer micro-batches events
→ write raw and normalized payloads to MinIO Bronze
```

Do not add Debezium or Flink for Phase 1. Debezium is only useful for CDC from an operational database, and Flink is only needed for advanced stream processing. Phase 1 keeps streaming simple: source adapter → Kafka → micro-batch consumer → Bronze.

---

## 21. Section 02 — Data Architecture

Use Medallion Architecture:

```text
Bronze → Silver → Gold
```

### Bronze

```text
Raw source data
Minimal transformation
Append-only
```

### Silver

```text
Cleaned
Deduplicated
Standardized
Schema-enforced
```

### Gold

```text
Business-ready
Facts
Dimensions
OBT
Feature tables
```

---

## 22. Bronze Layer

MinIO S3A paths:

```text
s3a://financial-distress-lake/bronze/companies/
s3a://financial-distress-lake/bronze/financial_statements/
s3a://financial-distress-lake/bronze/market_prices_daily/
s3a://financial-distress-lake/bronze/kafka/price_events/
s3a://financial-distress-lake/bronze/kafka/news_events/
s3a://financial-distress-lake/bronze/kafka/alert_events/
```

Bronze rules:

```text
Append-only
Preserve raw columns
Add ingest_ts
Add source_name
Add batch_id
Add source_offset or file_name
No heavy cleaning
```

Partition suggestions:

```text
financial_statements: fiscal_year, fiscal_quarter
market_prices_daily: trading_date
streaming events: event_date, event_hour
```

---

## 23. Silver Layer

Silver tables:

```text
stg_companies
stg_financial_statements
stg_market_prices
stg_price_events
stg_news_events
stg_alert_events
```

Silver rules:

```text
Deduplicate
Standardize column names
Normalize data types
Normalize currency units
Parse timestamps
Handle missing fields
Handle schema evolution
Filter impossible values
```

Dedup keys:

```text
stg_financial_statements:
ticker + report_period, keep latest created_ts

stg_market_prices:
ticker + trading_date, keep latest created_ts

stg_price_events:
event_id, keep latest created_ts

stg_news_events:
event_id, keep latest created_ts
```

---

## 24. Gold Layer

Gold schema/database name:

```text
gold_finance
```

Gold tables:

```text
dim_company
dim_date
fact_financial_statement
fact_market_price
fact_news_sentiment
obt_company_quarter_risk
feat_company_financial_4q
feat_company_market_30d
feat_company_news_30d
feat_company_unified
```

Gold should be built by:

```text
PySpark local mode
Silver Parquet → Gold Parquet
```

---

## 25. Gold Dimension Tables

### dim_company

Grain:

```text
One row per company
```

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

### dim_date

Grain:

```text
One row per calendar date
```

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

---

## 26. Gold Fact Tables

### fact_financial_statement

Grain:

```text
One row per company per report_period
```

Measures:

```text
total_assets
total_liabilities
equity
revenue
ebit
interest_expense
net_income
operating_cash_flow
current_assets
current_liabilities
retained_earnings
```

### fact_market_price

Grain:

```text
One row per company per trading date
```

Measures:

```text
open_price
high_price
low_price
close_price
volume
market_cap
daily_return
volatility_signal
```

### fact_news_sentiment

Grain:

```text
One row per news event
```

Measures:

```text
sentiment_score
risk_keyword_flag
severity_score
```

---

## 27. Gold OBT Table

### obt_company_quarter_risk

Grain:

```text
One row per company per report_period
```

Purpose:

```text
Denormalized business-ready table for DuckDB SQL analysis and future ML dataset creation.
```

Columns:

```text
ticker
company_name
exchange
industry
report_period
fiscal_year
fiscal_quarter

total_assets
total_liabilities
equity
revenue
net_income
operating_cash_flow

current_ratio
debt_to_asset
debt_to_equity
roa
roe
ebit_interest_coverage
working_capital_to_assets
retained_earnings_to_assets

market_cap
quarter_return
volatility_30d
negative_news_count_30d
avg_sentiment_30d

distress_label
distress_reason
event_timestamp
created_ts
```

---

## 28. Gold Feature Tables

### feat_company_financial_4q

Grain:

```text
ticker + event_timestamp
```

Features:

```text
f_revenue_growth_4q
f_net_income_growth_4q
f_avg_roa_4q
f_avg_debt_to_asset_4q
f_current_ratio_latest
f_interest_coverage_latest
f_negative_equity_flag
```

### feat_company_market_30d

Grain:

```text
ticker + event_timestamp
```

Features:

```text
f_return_30d
f_volatility_30d
f_volume_change_30d
f_max_drawdown_30d
f_market_cap_latest
```

### feat_company_news_30d

Grain:

```text
ticker + event_timestamp
```

Features:

```text
f_negative_news_count_30d
f_avg_sentiment_30d
f_risk_keyword_count_30d
f_news_burst_flag
```

### feat_company_unified

Grain:

```text
ticker + event_timestamp
```

Purpose:

```text
Unified feature table for future ML training/scoring.
```

Important rule:

```text
Maintain point-in-time correctness.
Do not use features created after the label/reference timestamp.
```

---

## 29. PySpark Transform Design

PySpark is used specifically for:

```text
Silver → Gold
```

Recommended script:

```text
src/transforms/silver_to_gold.py
```

It should:

```text
Create SparkSession
Read Silver Parquet
Build dimension tables
Build fact tables
Build OBT table
Build feature tables
Write local Gold Parquet
Print row counts
Return success/failure status to Airflow
```

### Technical Design: Handling Schema Evolution in Spark
When processing historical or new partitions with varying schemas (e.g., older partitions missing the `retained_earnings` field), the PySpark job implements the following robust patterns:
1. **Schema Merging**: When reading multiple partitions of Silver Parquet files, we explicitly enable schema merging:
   ```python
   df = spark.read.option("mergeSchema", "true").parquet("s3a://financial-distress-lake/silver/financial_statements/")
   ```
2. **Missing Field Alignment**: When constructing OBT or feature tables from different eras, the script uses Spark's `unionByName` with `allowMissingColumns=True` to automatically fill missing columns with `NULL` rather than failing the execution:
   ```python
   aligned_df = old_df.unionByName(new_df, allowMissingColumns=True)
   ```

### Technical Design: Point-in-Time (PIT) Window Joins
To ensure strict analytical correctness and prevent **data leakage** (preventing future features from leaking into past labels), PySpark implements a Point-in-Time join using window functions over timestamps:
1. For each reference timestamp (event release), we join features that were active strictly *before or at* that timestamp.
2. Under Spark, we define a window partitioned by `ticker`, ordered by `event_timestamp DESC`, and extract the first record where the feature timestamp is less than or equal to the label timestamp:
   ```python
   from pyspark.sql.window import Window
   import pyspark.sql.functions as F

   # Combine labels and features with a temporal boundary
   joined_df = label_df.join(feature_df, "ticker") \
                       .filter(feature_df.event_timestamp <= label_df.event_timestamp)

   # Extract the closest feature record prior to the label
   window_spec = Window.partitionBy("ticker", label_df.event_timestamp).orderBy(feature_df.event_timestamp.desc())
   pit_dataset = joined_df.withColumn("rank", F.row_number().over(window_spec)) \
                          .filter("rank == 1") \
                          .drop("rank")
   ```

Example Spark submit:

```bash
spark-submit --master local[*] /opt/airflow/src/transforms/silver_to_gold.py
```

Example SparkSession:

```python
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .appName("financial-distress-silver-to-gold")
    .master("local[*]")
    .getOrCreate()
)
```

---

## 30. PySpark and MinIO Local Integration

In our 100% local architecture, PySpark reads and writes directly to local MinIO using Spark's native S3A connector.

### Spark MinIO Configuration

During the SparkSession construction, we configure the Hadoop S3A properties to target the local Docker MinIO container:

```python
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .appName("financial-distress-silver-to-gold")
    .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4")
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin")
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin")
    .config("spark.hadoop.fs.s3a.path.style.access", "true")
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
    .getOrCreate()
)
```

### PySpark Read/Write Execution

With this setup, we read directly from and write to MinIO buckets using standard `s3a://` paths:

```python
# Reading from Silver in MinIO
silver_df = spark.read.parquet("s3a://financial-distress-lake/silver/financial_statements/")

# Writing to Gold in MinIO
gold_df.write.mode("overwrite") \
    .partitionBy("fiscal_year", "fiscal_quarter") \
    .parquet("s3a://financial-distress-lake/gold/fact_financial_statement/")
```

---

## 31. Idempotency Policy

Avoid duplicate data when DAGs rerun.

### Bronze

```text
Append-only is acceptable.
```

### Silver

```text
Overwrite affected partitions.
Deduplicate by business key + latest created_ts.
```

### Gold

```text
Use overwrite for affected partitions.
Do not blindly append.
```

Example:

```python
df.write.mode("overwrite").partitionBy("fiscal_year", "fiscal_quarter").parquet(output_path)
```

For small demo tables:

```text
Full overwrite is acceptable.
```

---

## 32. Data Quality Checks

DQ checks should cover:

```text
Schema checks
Null checks
Uniqueness checks
Referential integrity checks
Value range checks
Freshness checks
Volume checks
```

Examples:

```text
ticker must not be null
financial_statement ticker + report_period must be unique
market price ticker + trading_date must be unique
event_id must be unique after dedup
total_assets >= 0
sentiment_score between -1 and 1
Gold table freshness <= SLA
```

All DQ results should be written to:

```text
project_metadata.data_quality_result
```

### DQ Action & Severity Policy
To avoid breaking the entire system for minor data anomalies while protecting the analytical tables from severe corruption, we define a tiered action policy:
* **Severity: CRITICAL (Hard Fail)**:
  * *Applies to*: Schema structural changes, primary key nulls, or severe primary key duplicates.
  * *Action*: Write fail status to `data_quality_result`, raise an exception to **immediately halt** downstream Airflow tasks, and send a Slack/email alert to the operational team.
* **Severity: WARNING (Soft Fail)**:
  * *Applies to*: Value out-of-range checks (e.g., negative assets, stock price drops > 90%), referential integrity mismatches on new tickers, or mild freshness lag.
  * *Action*: Write check status to `data_quality_result`, route flagged records to `failed_records` DLQ table, but **allow downstream tasks to proceed** so the business BI dashboard is not blocked.

---

## 33. SLA Targets

Suggested mini-coursework SLA targets:

```text
Bronze offline ingestion freshness: manual or daily batch
Bronze streaming ingestion freshness: <= 10 minutes
Silver refresh: <= 30 minutes
Gold refresh: <= 60 minutes
Feature table refresh: <= 60 minutes
Pipeline success rate target: >= 95% for demo runs
```

These are target values for documentation and evidence, not strict production SLAs.

---

## 34. Backfill Strategy

For mini-coursework:

```text
No large automatic backfill by default.
Allow manual backfill for selected date range or last 1 day / last 1 quarter.
Backfill jobs must be idempotent.
Backfill should not create duplicate records.
```

### Technical Design: Dynamic Airflow Backfill Execution
When running historical reprocessing, the pipeline avoids hardcoded parameters. Airflow coordinates backfills via execution date macros:
1. **Dynamic Partitions**: Airflow passes the execution date partition `{{ ds }}` or quarterly boundaries dynamically to the Spark submit operator:
   ```bash
   spark-submit --master local[*] \
     /opt/airflow/src/transforms/silver_to_gold.py \
     --execution_date "{{ ds }}" \
     --target_year "{{ dag_run.conf.get('year', execution_date.year) }}" \
     --target_quarter "{{ dag_run.conf.get('quarter', (execution_date.month-1)//3 + 1) }}"
   ```
2. **Idempotent Write**: The PySpark script parses these arguments and strictly overwrites the matching partition target on MinIO (or local output) rather than appending:
   ```python
   df.write.mode("overwrite") \
     .parquet(f"s3a://financial-distress-lake/gold/fact_financial_statement/year={target_year}/quarter={target_quarter}/")
   ```

Example:

```text
If a late financial statement update arrives for ticker AAA in 2024Q4:
1. Reprocess Bronze partition for 2024Q4.
2. Rebuild Silver financial statement for AAA 2024Q4.
3. Recompute Gold fact and feature rows using PySpark.
4. Update DQ and run metadata in local PostgreSQL.
5. Inspect result in DBeaver.
```

---

## 35. Airflow DAG Design

Recommended DAG files:

```text
dags/
├── 01_collect_company_master_data.py
├── 02_collect_financial_statement_api.py
├── 03_collect_market_price_api.py
├── 04_stream_market_events_to_kafka.py
├── 05_transform_bronze_to_silver.py
├── 06_pyspark_silver_to_gold.py
├── 07_run_data_quality_checks.py
└── 08_minio_duckdb_register_tables.py
```

### DAG 1 — collect_company_master_data

Tasks:

```text
fetch_company_list_from_primary_source
filter_non_financial_listed_companies
persist_raw_company_payload_to_bronze
normalize_company_master_to_bronze
checkpoint_successful_tickers
write_run_metadata_to_local_postgres
```

### DAG 2 — collect_financial_statement_api

Tasks:

```text
read_company_checkpoint
for_each_ticker_and_period
call_balance_sheet_api
call_income_statement_api
call_cash_flow_api
retry_failed_requests
persist_raw_financial_payload_to_bronze
write_failed_tickers_to_project_metadata
write_run_metadata_to_local_postgres
```

### DAG 3 — collect_market_price_api

Tasks:

```text
read_company_checkpoint
call_historical_price_api
call_market_cap_or_shares_api_when_available
persist_raw_market_payload_to_bronze
write_run_metadata_to_local_postgres
```

### DAG 4 — stream_market_events_to_kafka

Tasks:

```text
connect_websocket_or_start_polling_adapter
normalize_price_news_alert_events
publish_events_to_kafka_topics
consume_events_microbatch
write_stream_events_to_minio_bronze
write_checkpoint_and_failed_records_to_postgres
```

### DAG 5 — transform_bronze_to_silver

Tasks:

```text
read_bronze
validate_schema
clean_and_standardize
deduplicate
write_local_silver_parquet
sync_silver_to_minio
write_run_metadata_to_local_postgres
```

### DAG 6 — pyspark_silver_to_gold

Tasks:

```text
spark_build_dim_company
spark_build_dim_date
spark_build_fact_financial_statement
spark_build_fact_market_price
spark_build_fact_news_sentiment
spark_build_obt_company_quarter_risk
spark_build_feature_tables
write_gold_to_minio
write_run_metadata_to_local_postgres
```

### DAG 5 — run_data_quality_checks

Tasks:

```text
run_schema_checks
run_null_checks
run_uniqueness_checks
run_referential_checks
run_freshness_checks
run_volume_checks
write_dq_results_to_local_postgres
fail_pipeline_if_critical_check_fails
```

### DAG 6 — minio_duckdb_register_tables

Tasks:

```text
create_or_update_duckdb_views
register_external_minio_parquet
run_duckdb_smoke_queries
save_query_results_as_evidence
```

---

## 36. DuckDB Evidence Queries

To query the local MinIO Parquet files with Athena-like high-performance serverless SQL, we run DuckDB (via DBeaver or Python API) with the `httpfs` extension configured to target MinIO:

```sql
-- 1. Install and load S3 support in DuckDB
INSTALL httpfs;
LOAD httpfs;

-- 2. Configure MinIO S3 credentials and local endpoint
SET s3_endpoint='localhost:9000';
SET s3_access_key_id='minioadmin';
SET s3_secret_access_key='minioadmin';
SET s3_use_ssl=false;
SET s3_url_style='path';

-- 3. Query the Gold Parquet files directly in MinIO
SELECT COUNT(*) AS total_rows
FROM read_parquet('s3://financial-distress-lake/gold/fact_financial_statement/**/*.parquet');

-- 4. Check for duplicate financial reports
SELECT ticker, report_period, COUNT(*) AS cnt
FROM read_parquet('s3://financial-distress-lake/gold/fact_financial_statement/**/*.parquet')
GROUP BY ticker, report_period
HAVING COUNT(*) > 1;

-- 5. Query company dimensions
SELECT industry, COUNT(*) AS companies
FROM read_parquet('s3://financial-distress-lake/gold/dim_company/**/*.parquet')
GROUP BY industry;

-- 6. Inspect company quarter risk and distress labels
SELECT distress_label, COUNT(*) AS row_count
FROM read_parquet('s3://financial-distress-lake/gold/obt_company_quarter_risk/**/*.parquet')
GROUP BY distress_label;

-- 7. View sample features for ML
SELECT *
FROM read_parquet('s3://financial-distress-lake/gold/feat_company_unified/**/*.parquet')
LIMIT 20;
```

---

## 37. DBeaver Evidence Queries

```sql
SELECT *
FROM project_metadata.pipeline_run_log
ORDER BY started_at DESC
LIMIT 20;
```

```sql
SELECT dataset_name, check_name, status, metric_value, threshold_value, checked_at
FROM project_metadata.data_quality_result
ORDER BY checked_at DESC
LIMIT 50;
```

```sql
SELECT *
FROM project_metadata.dataset_freshness
ORDER BY checked_at DESC;
```

```sql
SELECT dataset_name, schema_version, is_current
FROM project_metadata.schema_version_registry
ORDER BY dataset_name, effective_from DESC;
```

```sql
SELECT dataset_name, failure_reason, created_at
FROM project_metadata.failed_records
ORDER BY created_at DESC
LIMIT 20;
```

---

## 38. Evidence Checklist

The mini-coursework should include evidence such as:

```text
Collected API batch Parquet files
Collected Kafka streaming events
Kafka producer/consumer logs
Airflow DAG run screenshots
PySpark Silver-to-Gold logs
Local Gold Parquet output
MinIO Bronze/Silver/Gold screenshots
DuckDB view registration screenshots
DuckDB query result screenshots
DBeaver screenshot of pipeline_run_log
DBeaver screenshot of data_quality_result
DBeaver screenshot of failed_records or collector_checkpoint
DQ report CSV/JSON
README run instructions
Final 01_data_generator.md
Final 02_schema_design.md
```

---

## 39. Repository Structure

Recommended structure:

```text
financial-distress-data-system/
├── README.md
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── configs/
│   ├── collector_config.yaml
│   ├── source_mapping.yaml
│   ├── spark_config.yaml
│   └── dq_rules.yaml
├── dags/
│   ├── 01_collect_company_master_data.py
│   ├── 02_collect_financial_statement_api.py
│   ├── 03_collect_market_price_api.py
│   ├── 04_stream_market_events_to_kafka.py
│   ├── 05_transform_bronze_to_silver.py
│   ├── 06_pyspark_silver_to_gold.py
│   ├── 07_run_data_quality_checks.py
│   └── 08_minio_duckdb_register_tables.py
├── src/
│   ├── collectors/
│   │   ├── company_list_collector.py
│   │   ├── financial_statement_collector.py
│   │   ├── market_price_collector.py
│   │   ├── collector_checkpoint.py
│   │   └── source_adapters/
│   │       ├── vnstock_adapter.py
│   │       ├── http_json_adapter.py
│   │       └── html_table_adapter.py
│   ├── streaming/
│   │   ├── websocket_market_event_producer.py
│   │   ├── polling_market_event_producer.py
│   │   ├── news_event_producer.py
│   │   └── kafka_to_bronze_consumer.py
│   ├── transforms/
│   │   ├── bronze_to_silver.py
│   │   ├── silver_to_gold.py
│   │   ├── build_dimensions.py
│   │   ├── build_facts.py
│   │   ├── build_obt.py
│   │   └── build_features.py
│   ├── quality/
│   │   ├── dq_checks.py
│   │   └── dq_report.py
│   ├── catalog/
│   │   ├── glue_catalog.py
│   │   └── athena_queries.py
│   └── metadata/
│       ├── postgres_client.py
│       └── metadata_writer.py
├── sql/
│   ├── init_project_metadata.sql
│   ├── athena_create_external_tables.sql
│   └── athena_validation_queries.sql
├── docs/
│   ├── 01_data_generator.md
│   ├── 02_schema_design.md
│   └── evidence/
├── tests/
│   ├── test_generator.py
│   ├── test_schema_contracts.py
│   ├── test_silver_to_gold.py
│   └── test_dq_checks.py
└── outputs/
    ├── bronze/
    ├── silver/
    ├── gold/
    ├── sample_data/
    ├── dq_reports/
    └── athena_results/
```

---

## 40. Docker Compose Services

Recommended Docker services:

```text
postgres
airflow-webserver
airflow-scheduler
kafka
kafka-ui optional
```

Spark does not need a separate long-running cluster.

Use:

```text
spark-submit --master local[*]
```

inside the Airflow/Python environment.

---

## 41. Scope Boundary

### In scope

```text
Online API batch collection for company, financial statement, and market price data
WebSocket or polling-based streaming market/news events
Local Kafka KRaft single-node
Local Airflow orchestration
Local PySpark Silver-to-Gold transformation
Local PostgreSQL metadata and DQ storage
DBeaver inspection of local PostgreSQL
MinIO Bronze/Silver/Gold storage
DuckDB view registration
DuckDB SQL validation
Data quality checks
Pipeline run evidence
01 and 02 documentation
```

### Out of scope

```text
AWS RDS
Kubernetes deployment
Full Spark cluster
Full MLOps model registry
Real-time model serving
SageMaker
EMR
MSK
Redshift
Production alerting stack
Full Terraform multi-env infra
Advanced dashboard
LLM chatbot
```

---

## 42. Suggested Team Split

For a 5-member team:

### Member 1 — Online Data Collector

```text
company list collector
financial statement API collector
market price API collector
source adapters
retry and checkpoint policy
failed ticker handling
```

### Member 2 — Streaming/Kafka

```text
Kafka KRaft setup
price_event_producer
news_event_producer
kafka_to_bronze_consumer
micro-batching
```

### Member 3 — Local Infra/Airflow

```text
docker-compose
Airflow setup
PostgreSQL setup
DAG skeletons
local environment
```

### Member 4 — PySpark Transform

```text
Bronze-to-Silver
Silver-to-Gold
dims/facts/OBT/features
idempotent overwrite
```

### Member 5 — DQ/Evidence

```text
MinIO layout
DuckDB SQL
DQ checks
DBeaver evidence
screenshots
```

---

## 43. Implementation Order

Recommended order:

```text
1. Create repository structure.
2. Write docker-compose.yml with Airflow, Kafka KRaft, PostgreSQL, and MinIO.
3. Create local PostgreSQL project_metadata schema and MinIO buckets.
4. Connect DBeaver to local PostgreSQL and MinIO.
5. Write collector config YAML and source mapping.
6. Implement company, financial statement, and market price API collectors.
7. Implement WebSocket or polling producers for price/news events.
8. Implement Kafka consumer with micro-batching.
9. Write Bronze output to MinIO using PySpark.
10. Implement Bronze-to-Silver cleaning job.
11. Write Silver Parquet output to MinIO.
12. Implement local PySpark Silver-to-Gold transform.
13. Write Gold Parquet outputs to MinIO.
14. Configure DuckDB to mount and read MinIO Parquet files.
15. Run DuckDB validation queries inside DBeaver.
16. Add DQ checks and write results to local PostgreSQL.
17. Capture DBeaver screenshots of Postgres metadata tables.
18. Capture Airflow DAG and MinIO console screenshots.
19. Capture DuckDB SQL query execution evidence.
20. Add README run instructions.
21. Finalize 01_data_generator.md.
22. Finalize 02_schema_design.md.
```

---

## 44. Report Paragraph

Use this paragraph in the final report:

```text
This project designs and implements a local-first end-to-end data engineering system for Financial Distress analytics. The system collects offline/API-batch financial datasets and streaming market events from online Vietnamese market data sources, then processes them through a production-oriented local data platform.

The main objective is to build a reliable data foundation for future AI/ML development. The system collects Vietnamese listed-company data from online APIs, libraries such as vnstock, and WebSocket or polling feeds where available. Local Docker services such as Airflow, Kafka, PostgreSQL, MinIO, and PySpark are used for orchestration, streaming, metadata management, object storage, and Silver-to-Gold transformations. PostgreSQL runs locally and is inspected through DBeaver for pipeline metadata, source request status, data quality results, freshness metrics, checkpoints, failed tickers, and dead-letter queue records.

MinIO is utilized as a local, secure S3-compatible object storage layer to store Bronze, Silver, and Gold Parquet datasets. DuckDB acts as the serverless local query engine, allowing high-performance, Athena-style SQL validation and analytical queries directly over MinIO datasets inside DBeaver.

In the mini-coursework phase, the project focuses on Section 01 and Section 02: online data collection, schema design, Bronze/Silver/Gold data modeling, PySpark transformation jobs, data quality checks, update policies, and reproducible pipeline evidence.
```

---

## 45. Key Design Principles

```text
Simple but production-oriented
Local-first for storage, processing, metadata, and evidence
Online data collection through source adapters
No AWS credit card/billing required
No AWS RDS or S3 Cloud dependencies
Local PostgreSQL + MinIO + DuckDB + DBeaver for full pipeline evidence
PySpark for scalable-style Silver-to-Gold transformations
Kafka kept minimal with KRaft single-node
Micro-batch streaming output to avoid small files
Retry, checkpoint, and failed ticker recovery for online collection
Clear data contracts
Clear Bronze/Silver/Gold separation
Idempotent pipelines
Observable pipeline runs
Explicit data quality checks
Future-ready for ML/LLM
```

---

## 46. Final Agent Instructions

Any agent continuing this project should follow these instructions:

```text
1. Treat this as a mini-coursework idea document.
2. Keep implementation limited to Section 01 and Section 02.
3. Do not add AWS RDS or S3 Cloud back.
4. Use local PostgreSQL for metadata and DQ results.
5. Mention DBeaver as the inspection tool for local PostgreSQL and DuckDB.
6. Use Kafka single-node KRaft, not multi-node Kafka.
7. Use PySpark local mode with S3A connector for Silver-to-Gold transformation.
8. Write Parquet outputs directly to local MinIO bucket.
9. Configure PySpark to target the local http://minio:9000 endpoint.
10. Use DuckDB to query MinIO Parquet files with serverless SQL.
11. Produce runnable evidence and screenshots.
12. Use source adapters for vnstock/API/WebSocket collection and keep credentials in environment variables.
13. Respect API terms, rate limits, authentication boundaries, and robots.txt.
14. Leave ML/LLM/Kubernetes as future extension.
```

---

## 47. Security Design (Core Requirement)

To protect the financial platform's metadata, raw data, and credentials, the design implements the following security protocols:

### 1. Secrets Management
* **No Hardcoding**: DB passwords, MinIO access keys, and Kafka connection strings are strictly read from environment variables.
* **Environment Configuration**: A local secure `.env` file (excluded from Git via `.gitignore`) is utilized to configure the Docker containers at runtime:
  ```env
  POSTGRES_PASSWORD=secure_postgres_pass_2026
  AWS_ACCESS_KEY_ID=minioadmin
  AWS_SECRET_ACCESS_KEY=minioadmin
  MINIO_ROOT_USER=minioadmin
  MINIO_ROOT_PASSWORD=minioadmin
  ```

### 2. IAM Roles & RBAC (Role-Based Access Control)
* **MinIO Bucket Policies**: MinIO is configured with read/write access policies that restrict access to the `financial-distress-lake` bucket, strictly mimicking production AWS S3 IAM security policies:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ],
        "Resource": "arn:aws:s3:::financial-distress-lake/*"
      }
    ]
  }
  ```
* **Database RBAC**: Local PostgreSQL is configured with two distinct roles:
  * `airflow_writer`: Granted read/write access to `project_metadata` for DAG state logging and DQ reports.
  * `dbeaver_reader`: Restricted strictly to read-only access on the operational schemas, preventing accidental deletion of run history during analytical inspection.

### 3. Sensitive Data Handling
* **Data Masking**: To protect corporate confidentiality where required, sensitive institutional indices or proprietary ticker details are scrubbed or hashed using `SHA-256` salts at the Silver transformation layer prior to MinIO storage.

---

## 48. CI/CD Pipeline Design (Core Requirement)

The development lifecycle enforces automated code quality gates and pipeline validation using **Jenkins** as the central automation server:

### 1. Code Quality Gates (Linter & Formatter)
Every pull request or merge trigger on the `main` or `develop` branches triggers a webhook in Jenkins to execute syntax and stylistic compliance checks:
* **Linter**: **Ruff** executes static code analysis to check for unused imports, syntax errors, and standard Python best practices.
* **Formatter**: **Black** checks for consistent code formatting and rejects commits that do not conform to PEP 8 standards.

### 2. Automated Test Suite (PyTest)
The Jenkins Agent spins up a lightweight Spark instance locally to run the test suite under the `tests/` directory:
* **Unit Tests**:
  * Verify PySpark logic for computing financial ratios (current ratio, debt-to-asset ratio).
  * Validate target schema casting rules.
* **Integration Tests**:
  * Execute a mock data generation, push it to a mock Kafka topic, micro-batch consume it to a temporary local Bronze directory, and perform a Silver-to-Gold Spark job using a tiny test dataset (~100 records).

### 3. CI/CD Declarative Jenkinsfile Schema
```groovy
// Jenkinsfile
pipeline {
    agent any

    environment {
        PYTHONPATH = "${WORKSPACE}"
        SPARK_HOME = "/opt/spark"
        PATH       = "${SPARK_HOME}/bin:${PATH}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup Environment') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install ruff black pytest pyspark findspark pandas pyyaml
                '''
            }
        }

        stage('Lint & Format Check') {
            steps {
                sh '''
                    . venv/bin/activate
                    ruff check src/ dags/
                    black --check src/ dags/
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    pytest tests/
                '''
            }
            post {
                always {
                    junit '**/test-reports/*.xml' // Publish JUnit test results
                }
            }
        }

        stage('Artifact Archiving') {
            steps {
                archiveArtifacts artifacts: 'src/**/*.py, dags/**/*.py', onlyIfSuccessful: true
            }
        }
    }

    post {
        failure {
            echo "CI/CD Pipeline failed on Jenkins. Please check console output."
        }
        success {
            echo "CI/CD Pipeline completed successfully on Jenkins."
        }
    }
}
```
