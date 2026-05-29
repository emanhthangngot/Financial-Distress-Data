# Full Coursework Vision — Financial Distress Data + AI Engineering System

## 0. Purpose of This Document

This document is the **main full coursework idea handoff** for the Financial Distress Data + AI Engineering project.

It consolidates all decisions discussed so far and expands them from the **mini-coursework phase** into the **full coursework vision**.

The mini-coursework is not a separate idea. It is **Phase 1** of this larger coursework system.

The final system should be understood as:

```text
Mini-coursework Phase:
01_data_generator.md
02_schema_design.md

Full Coursework Extension:
03_data_generator_improvement.md
04.1_ml_design.md OR 04.2_llm_design.md
```

This file should be used by another AI agent, developer, or teammate to understand the whole direction of the coursework.

---

## 1. One-Sentence Summary

This coursework designs and implements a **local-first Data + AI Engineering system for Financial Distress analytics**, using **Airflow, Kafka, PySpark, PostgreSQL, MinIO, and DuckDB locally in Docker**. The data source strategy is online-first: collectors call Vietnamese market data APIs/libraries such as `vnstock`, plus WebSocket or polling feeds where available, while storage, processing, metadata, and evidence remain local.

---

## 2. Project Objective

The goal is to build an end-to-end Data + AI system that collects and processes financial data for Vietnamese listed companies, then prepares business-ready datasets and feature tables for future AI/ML use.

The system supports the following long-term use cases:

```text
Financial distress prediction
Company risk scoring
Early warning system
Investor risk screening
Financial health monitoring
Financial feature store
Future LLM financial assistant
```

The current mini-coursework implements the data foundation. The full coursework extends that foundation with collector robustness, source-change/drift scenarios, labels, ML training, scoring, and optional LLM use cases.

---

## 3. Final Coursework Structure

The full coursework should follow this structure:

```text
01_data_generator.md
02_schema_design.md
03_data_generator_improvement.md
04.1_ml_design.md OR 04.2_llm_design.md
```

Recommended final path:

```text
Complete 01
Complete 02
Complete 03
Choose 04.1 ML track as the primary AI track
Optionally describe 04.2 LLM as future extension
```

Why choose ML track first:

```text
Financial Distress naturally fits supervised ML.
The Gold feature tables from 02 directly support model training.
The drift scenarios from 03 directly support retraining and monitoring.
```

---

## 4. Phase Mapping

## Phase 1 — Mini-Coursework

Scope:

```text
01_data_generator.md
02_schema_design.md
```

Main outputs:

```text
Offline/API batch collectors
Streaming WebSocket/API collectors
Bronze/Silver/Gold data lake in MinIO
PySpark Silver-to-Gold transforms
Data quality checks
Local PostgreSQL metadata
DBeaver Postgres evidence
MinIO / DuckDB data lake evidence
```

Phase 1 proves that the data foundation is correct.

---

## Phase 2 — Full Coursework Extension

Scope:

```text
03_data_generator_improvement.md
04.1_ml_design.md
```

Main outputs:

```text
Feature drift scenarios
Improved generator realism
Gold monitoring tables
ML label table
Training table
Model training pipeline
Evaluation metrics
Batch scoring pipeline
Retraining policy
Model/version artifact storage
Monitoring and rollback design
```

Phase 2 proves that the system can support AI/ML workflows.

---

## Phase 3 — Optional Future Extension

Scope:

```text
04.2_llm_design.md
```

Optional idea:

```text
LLM assistant for asking questions about company risk, financial ratios, and distress signals.
```

This should not be implemented unless there is enough time.

---

## 5. Domain: Financial Distress

The selected domain is **Financial Distress Prediction / Financial Risk Analytics**.

The system works with collected financial and market data for listed companies.

A company may be considered financially distressed if it has signals such as:

```text
Net loss for multiple reporting periods
Negative equity
Negative retained earnings
Weak operating cash flow
High debt-to-asset ratio
Low current ratio
Poor EBIT-to-interest coverage
Falling market capitalization
High stock volatility
Negative financial news sentiment
```

The mini phase now targets real online collection through APIs, supported libraries, and WebSocket/polling feeds where available. Synthetic data is acceptable only as deterministic fixtures for tests, demos, or external-source outage fallback.

---

## 6. Business Motivation

The project builds a platform concept that helps analysts or investors answer questions such as:

```text
Which companies show financial distress signals?
Which industries have the highest distress risk?
Which financial ratios are deteriorating?
Which companies have weak liquidity?
Which companies have negative news and falling stock prices?
Which features are useful for distress prediction?
When should a model be retrained due to drift?
```

Long-term product idea:

```text
A financial risk intelligence platform for listed companies.
```

---

## 7. Architecture Philosophy

The project should be:

```text
Local-first
Cloud-light
Production-oriented
Simple enough for coursework
Expandable to ML/LLM
```

Avoid over-engineering.

Do not add managed cloud services unless they directly support coursework goals.

The architecture should show production thinking without becoming too complex.

---

## 8. Final Architecture Decision

The final architecture is:

```text
Local Engineering Layer:
Airflow + Kafka + PySpark + PostgreSQL + DBeaver

Local Object Storage & Query Layer:
MinIO (Local S3 API) + DuckDB (Local Serverless SQL)

AI Extension Layer:
Local ML training/scoring jobs
Optional FastAPI scoring API
Optional MLflow-like local model registry directory
```

Important fixed decision:

```text
Do NOT use AWS RDS or S3 Cloud in this coursework.
Use local PostgreSQL for metadata and local MinIO/DuckDB for storage and queries.
Inspect local PostgreSQL and DuckDB schemas using DBeaver.
```

---

## 9. Canonical Full Architecture Statement

The coursework architecture uses a local-first data platform with Airflow, Kafka, PySpark, PostgreSQL, MinIO, and DuckDB running locally in Docker. Airflow orchestrates online API batch collection, WebSocket or polling-based streaming ingestion, Bronze-to-Silver cleaning, PySpark Silver-to-Gold transformation, data quality checks, drift monitoring, ML training, and batch scoring. Kafka runs as a lightweight single-node KRaft broker for normalized market/news/alert events collected from online sources. PySpark runs in local mode to build Gold dimension tables, fact tables, OBT tables, feature tables, training tables, and scoring outputs, reading from and writing directly to local MinIO storage.

Local PostgreSQL stores pipeline run logs, quality check results, freshness metrics, failed records, schema versions, checkpoint state, drift metrics, and ML run metadata. DBeaver is used to inspect these local metadata tables as coursework evidence.

MinIO is utilized as the local S3-compatible object storage layer to store Bronze, Silver, Gold, model artifacts, and scoring outputs. DuckDB acts as the local query engine, allowing high-performance, Athena-style serverless SQL queries on top of MinIO Parquet files using the DuckDB `httpfs` extension, with results displayed inside DBeaver.

The mini-coursework implements the data foundation. The full coursework extends the same architecture with drift simulation, ML labels, training data, model training, evaluation, scoring, monitoring, and retraining design.

---

## 10. High-Level Full Architecture Diagram

```text
                             ┌──────────────────────────────────────────────┐
                             │                Local Docker Layer             │
                             │ Airflow + Kafka + PySpark + PostgreSQL +     │
                             │               MinIO + DuckDB                 │
                             └───────────────────────┬──────────────────────┘
                                                     │
        ┌────────────────────────────────────────────┼────────────────────────────────────────────┐
        │                                            │                                            │
┌───────▼────────┐                         ┌─────────▼────────┐                         ┌─────────▼────────┐
│ API Batch      │                         │ WebSocket/API    │                         │ Local Metadata   │
│ Financial data │                         │ Stock/news feed  │                         │ PostgreSQL       │
└───────┬────────┘                         └─────────┬────────┘                         └─────────┬────────┘
        │                                            │                                            │
        │                                            ▼                                            │
        │                                  Kafka Single-Node KRaft                                │
        │                    financial.price_events / news_events / alert_events                  │
        │                                            │                                            │
        └─────────────────────┬──────────────────────┴──────────────────────┬─────────────────────┘
                              │                                             │
                              ▼                                             ▼
                     ┌────────────────┐                           ┌──────────────────────┐
                     │ output files   │                           │ DBeaver              │
                     └───────┬────────┘                           │ inspect PostgreSQL   │
                             │                                    └──────────────────────┘
                             ▼
                     ┌────────────────┐
                     │ MinIO Bronze   │
                     │ Raw Parquet    │
                     └───────┬────────┘
                             │
                             ▼
                     ┌────────────────┐
                     │ MinIO Silver   │
                     │ Cleaned data   │
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
                     │ analytics +    │
                     │ feature tables │
                     └───────┬────────┘
                             │
         ┌───────────────────┼────────────────────┐
         │                   │                    │
         ▼                   ▼                    ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐
│ DuckDB Views   │  │ DBeaver SQL    │  │ ML / AI Extension       │
│ local metadata │  │ local queries  │  │ training/scoring/drift  │
└────────────────┘  └────────────────┘  └───────────┬────────────┘
                                                     │
                                                     ▼
                                      │ model.pkl, metrics, scores │
                                      └────────────────────────────┘
```

---

## 11. Tool Stack

| Layer | Tool | Purpose |
|---|---|---|
| Data collection | Python, requests/httpx, pandas, vnstock optional | Collect company lists, financial statements, market prices, and raw API payloads |
| Streaming | WebSocket or polling adapters + Kafka KRaft single-node | Collect market/news/alert events and publish normalized events to Kafka |
| Orchestration | Airflow local Docker | Run DAGs and pipeline tasks |
| Batch transformation | PySpark local mode | Build Gold tables and ML datasets |
| Local metadata | PostgreSQL Docker | Store run logs, DQ results, checkpoints, drift/ML metadata |
| DB inspection | DBeaver | Inspect metadata tables |
| Local S3-compatible storage | MinIO | Store Bronze/Silver/Gold/model/score artifacts |
| Local catalog/views | DuckDB SQL views | Register queryable local analytical views |
| SQL validation | DuckDB through DBeaver | Query Gold outputs and evidence |
| Data quality | Custom Python checks or Great Expectations | Validate data |
| ML training | scikit-learn / XGBoost / LightGBM optional | Train distress classifier |
| Model artifacts | Local folder + MinIO | Store trained model, metrics, version metadata |
| Optional API | FastAPI local | Serve prediction endpoint if needed |
| Version control | GitHub | Store code and collaborate |
| IDE | VS Code | Development environment |

---

## 12. Explicit Non-Goals

Do not implement these unless explicitly required:

```text
AWS RDS
AWS EMR
AWS MSK
AWS Redshift
AWS SageMaker
AWS EKS
Full Kubernetes deployment
Full Spark cluster
Production Terraform multi-account infra
Production monitoring stack
Real-time online model serving at scale
Complex LLM multi-agent system
```

---

# PART A — MINI-COURSEWORK FOUNDATION

---

## 13. Mini-Coursework Scope

Mini-coursework includes:

```text
01_data_generator.md
02_schema_design.md
```

The goal is to build and prove the data foundation.

Mini-coursework deliverables:

```text
Online API batch financial data
Online WebSocket/API streaming market/news events
Kafka streaming path
Bronze/Silver/Gold data lake
PySpark Silver-to-Gold transformation
Local PostgreSQL metadata
DBeaver evidence
MinIO evidence
DuckDB SQL evidence
Data quality reports
Run instructions
```

---

## 14. Section 01 — Online Data Collector

The collector must create both offline/API-batch and streaming/WebSocket data paths. Synthetic fixtures remain allowed for deterministic tests, but online collection is the target design.

---

## 15. Offline/API Batch Data Design

The offline path collects scheduled company, financial statement, and historical market data from online Vietnamese market data sources. Recommended source options include `vnstock`, HOSE/HNX/UPCOM lists, Vietstock, CafeF, FireAnt, SSI iBoard, TCBS, and VCI endpoints when legally and technically accessible.

### 15.1 companies

Grain:

```text
One row per company / ticker
```

Purpose:

```text
Master data for listed companies.
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
created_ts
```

---

### 15.2 financial_statements

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
```

---

### 15.3 market_prices_daily

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
```

---

### 15.4 distress_labels

Grain:

```text
One row per ticker per report_period
```

Purpose:

```text
Rule-based label table for future ML.
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

## 16. Streaming Data Design

Streaming data should go through Kafka topics first inside the local platform. The external source may be WebSocket if available, or API polling that emits normalized Kafka events.

Recommended Kafka topics:

```text
financial.price_events
financial.news_events
financial.alert_events
```

---

### 16.1 stock_price_events

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
```

Example event types:

```text
price_update
price_spike
price_drop
volume_spike
```

---

### 16.2 news_sentiment_events

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

### 16.3 market_alert_events

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

## 17. Realistic Data Issues to Inject

The collectors should expect and handle realistic online data challenges. Synthetic fixtures should reproduce these issues for deterministic testing.

### 17.1 Skew

```text
70% of companies belong to a few major industries.
Some tickers produce more market events.
Some sectors have higher distress probability.
```

### 17.2 High cardinality

```text
ticker
event_id
news_id
report_period
```

### 17.3 Schema evolution

Older financial statement partitions may not include:

```text
retained_earnings
interest_expense
operating_cash_flow
```

Newer partitions include them.

### 17.4 Duplicates

```text
Duplicate financial statements for same ticker + report_period.
Duplicate Kafka events with same event_id.
```

### 17.5 Missing values

```text
Missing interest_expense.
Missing operating_cash_flow.
Missing market_cap.
Missing industry.
```

### 17.6 Late arrivals

```text
Some streaming events have created_ts later than event_timestamp.
Some financial reports arrive after report period end date.
```

### 17.7 Outliers

```text
Extremely high revenue growth.
Negative equity.
Very high debt ratio.
Sudden price crash.
```

### 17.8 Bursty traffic

```text
Market open/close has high event volume.
Negative news creates event bursts.
```

---

## 18. Suggested Collector Config

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
checkpoint_every_tickers: 25
persist_raw_payload: true
failed_ticker_policy: write_to_project_metadata_failed_records

stream_source_mode: websocket_or_polling
websocket_reconnect_seconds: 10
poll_interval_seconds: 60

stream_flush_interval_seconds: 60
stream_flush_record_count: 1000

fixture_mode_enabled: true
fixture_seed: 42
```

---

## 19. Kafka Design

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
Kafka is used to prove the streaming path exists.
It should not become the heaviest part of the mini-coursework.
```

The Kafka consumer should micro-batch events before writing to Bronze.

Recommended flushing rule:

```text
Flush every 1 minute
OR every 1000 records
```

Avoid writing one file per event.

---

## 20. Section 02 — Data Architecture

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

## 21. Bronze Layer

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

## 22. Silver Layer

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

## 23. Gold Layer

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

## 24. Gold Dimension Tables

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

## 25. Gold Fact Tables

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

## 26. Gold OBT Table

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

## 27. Gold Feature Tables

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

## 28. PySpark Transform Design

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

Example Spark submit:

```bash
spark-submit --master local[*] /opt/airflow/src/transforms/silver_to_gold.py
```

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

## 29. Local PostgreSQL Metadata

Local PostgreSQL stores operational metadata.

Tables:

```text
project_metadata.pipeline_run_log
project_metadata.data_quality_result
project_metadata.dataset_freshness
project_metadata.schema_version_registry
project_metadata.failed_records
project_metadata.backfill_request
```

DBeaver is used for inspection and evidence.

---

## 30. Data Quality Checks

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

---

## 31. SLA Targets

Suggested mini-coursework SLA targets:

```text
Bronze offline ingestion freshness: manual or daily batch
Bronze streaming ingestion freshness: <= 10 minutes
Silver refresh: <= 30 minutes
Gold refresh: <= 60 minutes
Feature table refresh: <= 60 minutes
Pipeline success rate target: >= 95% for demo runs
```

---

## 32. Backfill Strategy

For mini-coursework:

```text
No large automatic backfill by default.
Allow manual backfill for selected date range or last 1 day / last 1 quarter.
Backfill jobs must be idempotent.
Backfill should not create duplicate records.
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

## 33. Airflow DAG Design for Mini-Coursework

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

---

# PART B — FULL COURSEWORK EXTENSION

---

## 34. Section 03 — Data Generator Improvement

Section 03 extends the generator from Section 01.

Goal:

```text
Make the generator more realistic.
Add feature drift/change scenarios.
Create monitoring tables.
Create ML label table.
Create final ML training table.
```

Section 03 should not replace Section 01. It builds on top of it.

---

## 35. Drift Scenarios

Choose at least one drift scenario.

Recommended primary scenario:

```text
Scenario A — Financial deterioration drift
```

### Scenario A — Financial deterioration drift

After a configured drift start date:

```text
Debt-to-asset ratio increases.
Current ratio decreases.
Net income decreases.
Operating cash flow becomes weaker.
Interest coverage decreases.
Probability of distress label increases.
```

Affected features:

```text
f_avg_debt_to_asset_4q
f_current_ratio_latest
f_interest_coverage_latest
f_net_income_growth_4q
f_negative_equity_flag
```

Reason:

This drift is highly aligned with Financial Distress.

---

### Scenario B — Market stress drift

After drift start date:

```text
Stock volatility increases.
30-day return decreases.
Market cap drops.
Volume spikes.
```

Affected features:

```text
f_return_30d
f_volatility_30d
f_volume_change_30d
f_max_drawdown_30d
```

---

### Scenario C — News sentiment drift

After drift start date:

```text
Negative news increases.
Risk keyword count increases.
News bursts become more frequent.
Average sentiment decreases.
```

Affected features:

```text
f_negative_news_count_30d
f_avg_sentiment_30d
f_risk_keyword_count_30d
f_news_burst_flag
```

---

## 36. Drift Generator Config

```yaml
drift_enabled: true
drift_start_date: "2024-01-01"
drift_mode: "gradual"

scenario_financial_deterioration: true
scenario_market_stress: true
scenario_news_sentiment_shift: false

debt_ratio_multiplier_after_drift: 1.25
current_ratio_multiplier_after_drift: 0.80
net_income_multiplier_after_drift: 0.70
operating_cash_flow_multiplier_after_drift: 0.75

volatility_multiplier_after_drift: 1.50
market_return_shift_after_drift: -0.08
negative_news_multiplier_after_drift: 1.75
```

---

## 37. Section 03 Gold Monitoring Tables

Add these Gold tables:

```text
agg_feature_health_daily
feature_drift_alerts
ml_company_distress_label
ml_company_distress_training
```

---

### 37.1 agg_feature_health_daily

Purpose:

```text
Track daily distribution and drift metrics for important features.
```

Columns:

```text
monitoring_date
feature_name
mean_value
stddev_value
min_value
max_value
null_rate
psi_vs_baseline
alert_flag
created_ts
```

---

### 37.2 feature_drift_alerts

Purpose:

```text
Store drift alerts when feature drift exceeds threshold.
```

Columns:

```text
alert_id
alert_date
feature_name
psi_value
threshold_value
severity
action
created_ts
```

Example action:

```text
Investigate increase in debt ratio and liquidity deterioration.
```

---

### 37.3 ml_company_distress_label

Purpose:

```text
Label-only table for ML training.
```

Grain:

```text
ticker + event_timestamp
```

Columns:

```text
ticker
event_timestamp
created_ts
distress_label
label_reason
label_version
```

---

### 37.4 ml_company_distress_training

Purpose:

```text
Training table created by joining labels with point-in-time features.
```

Grain:

```text
ticker + event_timestamp
```

Columns:

```text
ticker
event_timestamp
created_ts
distress_label

f_revenue_growth_4q
f_net_income_growth_4q
f_avg_roa_4q
f_avg_debt_to_asset_4q
f_current_ratio_latest
f_interest_coverage_latest
f_negative_equity_flag

f_return_30d
f_volatility_30d
f_volume_change_30d
f_max_drawdown_30d
f_market_cap_latest

f_negative_news_count_30d
f_avg_sentiment_30d
f_risk_keyword_count_30d
f_news_burst_flag
```

Important rule:

```text
Use point-in-time join.
Do not use future feature values.
```

---

## 38. Section 03 Deliverables

Section 03 should deliver:

```text
Improved generator code
Drift configuration
Drift validation report
Gold feature health table
Feature drift alert table
ML label table
ML training table
Brief explanation of why drift matters for downstream ML
```

Evidence:

```text
Drift report CSV
DuckDB query showing drift metrics
DBeaver metadata logs
Gold table screenshots
Feature distribution before/after drift
```

---

# PART C — AI TRACK: ML DESIGN

---

## 39. Recommended AI Track

Choose:

```text
04.1 ML Design
```

Main ML task:

```text
Predict whether a company will become financially distressed in the next reporting period.
```

This is the most natural extension of the data pipeline.

---

## 40. ML Prediction Setup

Entity:

```text
ticker
```

Prediction time:

```text
event_timestamp
```

Label:

```text
will_be_distressed_next_period
```

Or simpler:

```text
distress_label
```

Training data:

```text
gold_finance.ml_company_distress_training
```

Feature input:

```text
feat_company_financial_4q
feat_company_market_30d
feat_company_news_30d
feat_company_unified
```

---

## 41. ML Modeling Plan

Recommended baseline models:

```text
Logistic Regression
Random Forest
XGBoost or LightGBM optional
```

Start simple.

Do not use deep learning unless necessary.

Recommended split:

```text
Time-based split
Train: earlier years
Validation: middle period
Test: latest period
```

Avoid random split because financial data is time-dependent.

Example:

```text
Train: 2018–2022
Validation: 2023
Test: 2024–2025
```

---

## 42. ML Metrics

Recommended metrics:

```text
Precision
Recall
F1-score
ROC-AUC
PR-AUC
Confusion matrix
```

For financial distress:

```text
Recall for distress class is important.
False negative is more serious than false positive.
```

---

## 43. ML Pipeline Design

Add ML DAGs:

```text
dags/
├── 08_build_training_dataset.py
├── 09_train_distress_model.py
├── 10_batch_score_companies.py
└── 11_monitor_model_and_drift.py
```

### 43.1 build_training_dataset

Tasks:

```text
Read ml_company_distress_label
Read feature tables
Perform point-in-time join
Validate training schema
Write ml_company_distress_training
```

### 43.2 train_distress_model

Tasks:

```text
Read training table
Split by time
Train baseline model
Evaluate model
Save model artifact
Save metrics
Register model version metadata
```

### 43.3 batch_score_companies

Tasks:

```text
Read latest feature table
Load latest approved model
Generate distress probability
Write score table to Gold/S3
```

### 43.4 monitor_model_and_drift

Tasks:

```text
Read model metrics
Read drift metrics
Check thresholds
Trigger retrain recommendation
Write monitoring result to PostgreSQL
```

---

## 44. ML Artifact Storage

Use MinIO or local artifact storage.

Recommended path:

```text
s3a://financial-distress-lake/ml/artifacts/model_version=YYYYMMDD_HHMM/
```

Store:

```text
model.pkl
metrics.json
feature_list.json
training_config.yaml
model_card.md
```

No need for full MLflow unless time allows.

---

## 45. ML Metadata Tables in PostgreSQL

Add local PostgreSQL tables:

```text
project_metadata.ml_training_run
project_metadata.ml_model_registry
project_metadata.ml_batch_score_run
project_metadata.ml_monitoring_result
```

### ml_training_run

Columns:

```text
training_run_id
model_version
started_at
ended_at
status
train_rows
validation_rows
test_rows
metrics_json
error_message
```

### ml_model_registry

Columns:

```text
model_version
model_type
artifact_path
status
created_at
created_by
promotion_reason
```

Statuses:

```text
candidate
approved
rejected
production
archived
```

### ml_batch_score_run

Columns:

```text
score_run_id
model_version
score_date
input_rows
output_rows
status
created_at
```

### ml_monitoring_result

Columns:

```text
monitoring_id
model_version
monitoring_date
metric_name
metric_value
threshold_value
status
action
created_at
```

---

## 46. ML Score Output Table

Gold table:

```text
gold_finance.ml_company_distress_score
```

Grain:

```text
ticker + score_timestamp + model_version
```

Columns:

```text
ticker
score_timestamp
distress_probability
risk_band
model_version
created_ts
```

Risk bands:

```text
low
medium
high
critical
```

---

## 47. Model Promotion and Rollback

Promotion rule:

```text
Promote candidate model only if it beats baseline metrics and passes validation checks.
```

Example:

```text
F1 >= baseline F1
Recall for distress class >= threshold
No major data quality failures
No schema mismatch
```

Rollback rule:

```text
Keep previous production model artifact.
If new model fails monitoring checks, switch back to previous version.
```

---

## 48. Retraining Strategy

Use both scheduled and triggered retraining.

Scheduled retraining:

```text
Monthly or quarterly
```

Triggered retraining:

```text
Feature drift PSI > threshold
F1/Recall drops below threshold
Data distribution changes significantly
New financial reporting period arrives
```

Output:

```text
Retrain recommendation
New candidate model
Evaluation comparison
Promotion/rejection decision
```

---

## 49. ML Monitoring

Monitor:

```text
Feature drift
Prediction score drift
Label drift
Data quality failures
Input row count changes
Model metric degradation
```

Store monitoring results in local PostgreSQL and optionally Gold monitoring tables.

---

## 50. ML Design Deliverables

Section 04.1 should deliver:

```text
High-level ML design
Low-level ML components/classes
Training data contract
Feature/label contract
Train/validation/test split policy
Baseline model implementation
Evaluation metrics
Batch scoring implementation
Model artifact storage
Model versioning design
Retraining policy
Rollback policy
Monitoring design
CI/CD intent
```

Evidence:

```text
Training log
Evaluation metrics JSON
Model artifact file
Batch scoring output
DuckDB query on score table
DBeaver screenshot of ml_training_run
DBeaver screenshot of ml_model_registry
```

---

# PART D — OPTIONAL LLM TRACK

---

## 51. Optional LLM Use Case

If the team chooses or wants to discuss LLM track, the LLM use case can be:

```text
Financial Risk Analyst Assistant
```

Example questions:

```text
Why is ticker AAA considered high risk?
Which features contributed to this distress score?
Compare two companies by financial health.
Summarize risk signals for a company.
Which companies have deteriorating liquidity?
```

---

## 52. LLM Architecture

Optional components:

```text
FastAPI chat endpoint
Retrieval over Gold tables and generated reports
Simple prompt template
Tool call to prediction score API/table
Application logs
Safety checks
```

Trusted sources:

```text
gold_finance.obt_company_quarter_risk
gold_finance.feat_company_unified
gold_finance.ml_company_distress_score
Financial ratio explanation docs
```

This is optional and should not distract from ML track unless required.

---

# PART E — COMMON IMPLEMENTATION DETAILS

---

## 53. Airflow DAGs for Full Coursework

Full DAG set:

```text
01_collect_company_master_data.py
02_collect_financial_statement_api.py
03_collect_market_price_api.py
04_stream_market_events_to_kafka.py
05_transform_bronze_to_silver.py
06_pyspark_silver_to_gold.py
07_run_data_quality_checks.py
08_minio_duckdb_register_tables.py
08_generate_drift_scenarios.py
09_build_training_dataset.py
10_train_distress_model.py
11_batch_score_companies.py
12_monitor_drift_and_model.py
```

Mini-coursework only needs DAGs 01–07.

Full coursework can add DAGs 08–12.

---

## 54. Repository Structure

Recommended full repository:

```text
financial-distress-data-ai-system/
├── README.md
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── configs/
│   ├── generator_config.yaml
│   ├── drift_config.yaml
│   ├── minio_config.yaml
│   ├── spark_config.yaml
│   ├── dq_rules.yaml
│   └── ml_config.yaml
├── dags/
│   ├── 01_collect_company_master_data.py
│   ├── 02_collect_financial_statement_api.py
│   ├── 03_collect_market_price_api.py
│   ├── 04_stream_market_events_to_kafka.py
│   ├── 05_transform_bronze_to_silver.py
│   ├── 06_pyspark_silver_to_gold.py
│   ├── 07_run_data_quality_checks.py
│   ├── 08_minio_duckdb_register_tables.py
│   ├── 08_generate_drift_scenarios.py
│   ├── 09_build_training_dataset.py
│   ├── 10_train_distress_model.py
│   ├── 11_batch_score_companies.py
│   └── 12_monitor_drift_and_model.py
├── src/
│   ├── generator/
│   ├── streaming/
│   ├── transforms/
│   ├── quality/
│   ├── catalog/
│   ├── metadata/
│   ├── drift/
│   └── ml/
├── sql/
│   ├── init_project_metadata.sql
│   ├── init_ml_metadata.sql
│   ├── duckdb_create_views.sql
│   └── duckdb_validation_queries.sql
├── docs/
│   ├── 01_data_generator.md
│   ├── 02_schema_design.md
│   ├── 03_data_generator_improvement.md
│   ├── 04.1_ml_design.md
│   └── evidence/
├── tests/
│   ├── test_generator.py
│   ├── test_schema_contracts.py
│   ├── test_silver_to_gold.py
│   ├── test_dq_checks.py
│   ├── test_drift.py
│   └── test_ml_pipeline.py
└── outputs/
    ├── bronze/
    ├── silver/
    ├── gold/
    ├── drift_reports/
    ├── dq_reports/
    ├── ml_artifacts/
    ├── ml_scores/
    └── athena_results/
```

---

## 55. Evidence Checklist

## Mini-Coursework Evidence

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
DQ report CSV/JSON
README run instructions
Final 01_data_generator.md
Final 02_schema_design.md
```

## Full Coursework Evidence

```text
Drift validation report
Feature drift monitoring table
Feature drift alert table
ML label table
ML training table
Training pipeline logs
Evaluation metrics
Model artifact path
Batch score output
DuckDB query on ML score table
DBeaver screenshot of ml_training_run
DBeaver screenshot of ml_model_registry
Final 03_data_generator_improvement.md
Final 04.1_ml_design.md
```

---

## 56. Team Split for Full Coursework

For 5 members:

### Member 1 — Data Generator and Drift

```text
Offline generator
Financial data simulation
Distress label logic
Drift scenario generation
Drift report
```

### Member 2 — Streaming and Kafka

```text
Kafka KRaft setup
Price event producer
News event producer
Alert event producer
Kafka consumer
Micro-batch Bronze output
```

### Member 3 — Local Infra and Airflow

```text
docker-compose
Airflow setup
PostgreSQL setup
DBeaver connection guide
DAG orchestration
Run metadata logging
```

### Member 4 — PySpark and Data Modeling

```text
Bronze-to-Silver transform
Silver-to-Gold PySpark transform
Dimensions
Facts
OBT
Feature tables
Training table
```

### Member 5 — AWS, DQ, ML, Evidence

```text
MinIO layout
DuckDB views
DuckDB validation
Data quality checks
ML training/scoring
Metrics
Screenshots and evidence
```

---

## 57. Implementation Order

## Mini-Coursework Order

```text
1. Create repository structure.
2. Write docker-compose.yml with Airflow, Kafka KRaft, and PostgreSQL.
3. Create local PostgreSQL project_metadata schema.
4. Connect DBeaver to local PostgreSQL.
5. Write collector config YAML and source mapping.
6. Implement API batch collectors.
7. Implement Kafka producers for price/news events.
8. Implement Kafka consumer with micro-batching.
9. Write local Bronze output.
10. Upload/sync Bronze to S3.
11. Implement Bronze-to-Silver cleaning.
12. Write local Silver output.
13. Upload/sync Silver to S3.
14. Add local PySpark Silver-to-Gold transform.
15. Write local Gold Parquet outputs.
16. Upload/sync Gold to S3.
17. Register DuckDB views.
18. Run DuckDB validation queries.
19. Add DQ checks.
20. Write DQ results to local PostgreSQL.
21. Capture DBeaver screenshots.
22. Capture Airflow, MinIO, DuckDB, and DBeaver screenshots.
23. Add README run instructions.
24. Finalize 01_data_generator.md.
25. Finalize 02_schema_design.md.
```

## Full Coursework Order

```text
26. Add drift_config.yaml.
27. Implement drift scenarios.
28. Build drift validation report.
29. Build agg_feature_health_daily.
30. Build feature_drift_alerts.
31. Build ml_company_distress_label.
32. Build ml_company_distress_training.
33. Implement training pipeline.
34. Train baseline model.
35. Save model artifact and metrics.
36. Register model metadata locally.
37. Implement batch scoring.
38. Write ml_company_distress_score.
39. Add model/drift monitoring.
40. Capture ML and drift evidence.
41. Finalize 03_data_generator_improvement.md.
42. Finalize 04.1_ml_design.md.
```

---

## 58. Report Paragraph for Full Coursework

Use this paragraph in the final coursework report:

```text
This coursework designs and implements a local-first Data + AI Engineering system for Financial Distress analytics. The system collects offline/API-batch financial datasets and streaming market/news events from online Vietnamese market data sources, then processes them through a Medallion Architecture with Bronze, Silver, and Gold layers.

Local Docker services such as Airflow, Kafka, PostgreSQL, MinIO, and PySpark are used for orchestration, streaming, metadata management, object storage, data quality tracking, and Silver-to-Gold transformations. PostgreSQL runs locally and is inspected through DBeaver for pipeline metadata, data quality results, freshness metrics, checkpoints, drift metrics, and ML run metadata.

MinIO is utilized as the local S3-compatible object storage layer to store Bronze, Silver, Gold, model artifacts, and scoring outputs. DuckDB acts as the local query engine, allowing high-performance, Athena-style SQL validation and analytical queries directly over MinIO datasets inside DBeaver.

The mini-coursework phase implements the data foundation through Section 01 and Section 02. The full coursework extends the same architecture through Section 03 and Section 04.1 by adding drift scenarios, feature monitoring, ML label generation, training table construction, model training, batch scoring, model monitoring, and retraining strategy.
```

---

## 59. Key Design Principles

```text
Simple but production-oriented
Local-first for development
100% Free & offline-capable (No AWS credit card/billing required)
No AWS RDS or S3 Cloud dependencies
Local PostgreSQL + MinIO + DuckDB + DBeaver for full pipeline evidence
PySpark for scalable-style Silver-to-Gold and ML dataset transformations
Kafka kept minimal with KRaft single-node
Micro-batch streaming output to avoid small files
Clear data contracts
Clear Bronze/Silver/Gold separation
Idempotent pipelines
Observable pipeline runs
Explicit data quality checks
Point-in-time correctness for ML features
Future-ready for ML/LLM
```

---

## 60. Final Agent Instructions

Any agent continuing this project should follow these instructions:

```text
1. Treat this as the main full coursework idea document.
2. Keep mini-coursework as Phase 1: Section 01 and Section 02.
3. Expand full coursework as Phase 2: Section 03 and Section 04.1 ML.
4. Do not create a separate inconsistent architecture for mini and final phases.
5. Do not add AWS RDS or S3 Cloud back.
6. Use local PostgreSQL for metadata, DQ, drift, and ML run logs.
7. Mention DBeaver as the inspection tool for local PostgreSQL and DuckDB.
8. Use Kafka single-node KRaft, not multi-node Kafka.
9. Use PySpark local mode with S3A connector for Silver-to-Gold and training table construction.
10. Write Parquet outputs directly to local MinIO buckets.
11. Configure PySpark to target the local http://minio:9000 endpoint.
12. Use DuckDB to query MinIO Parquet files with serverless SQL.
13. Make Section 03 build naturally on Section 01 and 02.
14. Make Section 04.1 ML use Gold feature tables and labels created earlier.
15. Leave LLM/Kubernetes/SageMaker/EMR/MSK as optional future extensions.
16. Produce runnable evidence and screenshots for every completed phase.
```
