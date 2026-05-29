# Mini-Coursework Spec - Financial Distress Data Engineering System

## 0. Document Purpose

This is the Phase 1 mini-coursework source of truth for the current repository state.

It is intentionally written as an as-built specification, not an aspirational roadmap. If this document says a feature is implemented, there must be code, SQL, tests, DAG scaffolding, or configuration in this repository that supports that statement.

Phase 1 scope remains limited to:

```text
01_data_generator.md
02_schema_design.md
```

Phase 2 items such as ML training, model serving, drift monitoring, LLM assistants, managed cloud services, and Kubernetes are out of scope unless explicitly requested.

## 1. Current Repository Status

The repository currently implements a local-first Stage 1 data engineering foundation with:

- Documentation contracts in `docs/01_data_generator.md` and `docs/02_schema_design.md`.
- Local Docker service definitions in `docker-compose.yml`.
- Airflow DAG scaffolding in `dags/`.
- Fixture-backed collectors in `src/collectors/`.
- Schema contracts and in-memory metadata helpers in `src/metadata/`.
- Bronze-to-Silver normalization and deduplication helpers in `src/transforms/bronze_to_silver.py`.
- Gold table construction helpers in `src/transforms/silver_to_gold.py`.
- Rule-based distress labels in `src/transforms/compute_distress_labels.py`.
- Kafka event and micro-batch contracts in `src/streaming/`.
- Data quality checks in `src/quality/dq_checks.py`.
- DuckDB SQL helpers and view SQL in `src/catalog/` and `sql/`.
- PostgreSQL metadata DDL in `sql/init_project_metadata.sql`.
- PyTest coverage in `tests/`.
- Architecture image in `images/architecture/architecture-stage-1.png`.

The repository does not yet contain a fully executed end-to-end runtime evidence package. The remaining evidence work is to run the Docker services, execute DAGs or scripts against the local services, produce MinIO objects, query them through DuckDB, and store DBeaver screenshots or query exports under `docs/evidence/`.

## 2. Active Phase and Boundaries

```text
PHASE: Phase 1 mini-coursework
SCOPE: Data collection contracts, local lakehouse schema, pipeline scaffolding, DQ, metadata, and evidence targets
```

Allowed Phase 1 stack:

- Apache Airflow in local Docker.
- Kafka single-node KRaft in local Docker.
- PySpark local-mode design and transform-compatible helpers.
- PostgreSQL local Docker with schema `project_metadata`.
- MinIO local S3-compatible storage with bucket `financial-distress-lake`.
- DuckDB `httpfs` SQL for local Parquet inspection.
- DBeaver for SQL evidence screenshots and inspection.
- Python modules, fixtures, YAML configs, SQL files, and PyTest tests.

Not allowed in Phase 1:

- AWS S3, Glue, Athena, RDS, EMR, MSK, Redshift, SageMaker.
- Kubernetes.
- Cloud-only collectors or cloud-only packages.
- ML model training, drift jobs, model registry, online inference, LLM assistant code.

## 3. One-Sentence Summary

This project builds a local-first Stage 1 lakehouse foundation for Vietnamese financial distress analytics, using fixture-backed source adapters and local contracts to demonstrate batch collection, streaming event contracts, Bronze/Silver/Gold transformations, metadata, DQ, and DuckDB/DBeaver evidence paths.

## 4. Project Objective

The objective is to create a coursework-sized data engineering system that prepares clean, queryable financial and market data for listed companies.

Stage 1 prepares the data foundation for later use cases such as:

- Financial distress prediction.
- Company risk scoring.
- Early warning monitoring.
- Investor screening.

Stage 1 does not train a model. It builds and verifies the data contracts that a later ML or analytics layer would consume.

## 5. As-Built Architecture

Architecture image:

```text
images/architecture/architecture-stage-1.png
```

Current logical flow:

```text
Fixture source adapter
  -> collectors
  -> metadata helper logs
  -> Bronze-to-Silver helper contracts
  -> Gold table helper contracts
  -> DQ helper contracts
  -> SQL contracts for PostgreSQL and DuckDB
```

Target runtime flow for evidence:

```text
Online APIs or polling feeds
  -> source adapters
  -> Airflow tasks
  -> Kafka event contracts and Bronze raw paths
  -> MinIO Bronze/Silver/Gold Parquet paths
  -> PostgreSQL metadata rows
  -> DuckDB views over MinIO
  -> DBeaver inspection evidence
```

Important implementation note:

The current code uses `VnstockFixtureAdapter` as a deterministic adapter boundary for tests and smoke runs. It does not yet call live `vnstock`, HOSE, HNX, or other online APIs. This keeps tests stable while preserving the adapter shape needed for replacing fixtures with real online sources later.

## 6. Technology Stack

| Layer | Current repository artifact | Status |
|---|---|---|
| Local services | `docker-compose.yml` | Defined for PostgreSQL, MinIO, Kafka, Airflow webserver, Airflow scheduler |
| Collection | `src/collectors/*.py`, `src/collectors/source_adapters/vnstock_adapter.py` | Fixture-backed implementation |
| Streaming | `src/streaming/events.py`, `src/streaming/kafka_to_bronze_consumer.py` | Event and micro-batch contracts implemented |
| Transformation | `src/transforms/*.py` | Pure Python helper logic implemented and tested |
| Metadata | `src/metadata/*.py`, `sql/init_project_metadata.sql` | In-memory helper plus PostgreSQL DDL |
| Data quality | `src/quality/dq_checks.py`, `configs/dq_rules.yaml` | Core checks implemented and tested |
| Catalog | `src/catalog/duckdb_catalog.py`, `sql/duckdb_create_views.sql` | DuckDB SQL generation and SQL contracts |
| Tests | `tests/` | Unit tests for contracts and transformation logic |
| CI | `.github/workflows/ci.yml` | Quality gate workflow present for `main` and `dev` |

## 7. Repository Layout

```text
dags/
  01_collect_company_master_data.py
  02_collect_financial_statement_api.py
  03_collect_market_price_api.py
  04_stream_market_events_to_kafka.py
  05_transform_bronze_to_silver.py
  06_pyspark_silver_to_gold.py
  07_run_data_quality_checks.py
  08_minio_duckdb_register_tables.py
  _stage1_dag_utils.py

src/
  collectors/
  streaming/
  transforms/
  quality/
  catalog/
  metadata/

configs/
  collector_config.yaml
  dq_rules.yaml
  source_mapping.yaml
  spark_config.yaml

sql/
  init_project_metadata.sql
  duckdb_create_views.sql
  duckdb_validation_queries.sql

tests/
  test_bronze_to_silver.py
  test_distress_labels.py
  test_dq_checks.py
  test_keys.py
  test_silver_to_gold.py
  test_streaming.py
```

There is no `src/generator/` directory in the current implementation. Synthetic or fixture data lives behind `VnstockFixtureAdapter`, not in a separate generator module.

## 8. Data Source Design

### 8.1 Current implementation

Current collectors use `VnstockFixtureAdapter`:

- `collect_companies()` returns deterministic company master rows.
- `collect_financial_statements()` returns deterministic quarterly statement rows.
- `collect_market_prices()` returns deterministic daily market price rows.

The adapter returns fields that match the Phase 1 schema contracts and supports tests without network access.

### 8.2 Target online adapter boundary

Future live collectors should preserve the current adapter boundary and replace fixture methods with source-specific implementations:

- `fetch_companies()`
- `fetch_financial_statements(ticker, start_year, end_year)`
- `fetch_market_prices(ticker, start_year, end_year)`

Source-specific parsing should remain isolated under `src/collectors/source_adapters/`.

Credentials, cookies, tokens, endpoints, and rate limits must come from environment variables or config files, not hardcoded values.

## 9. Timestamp Conventions

Stage 1 uses four timestamp concepts. These definitions are required for consistent deduplication, freshness checks, and point-in-time joins:

- `event_timestamp`: when the source business event happened, such as a price tick, alert, or news article timestamp.
- `created_ts`: when the source system or local normalized record was created. Bronze-to-Silver deduplication keeps the latest `created_ts` for the same business key.
- `ingest_ts`: when the record entered the local Bronze layer. Bronze evidence should include this timestamp when runtime writes are generated.
- `report_release_date`: when a financial statement became visible to analysts. Feature joins for financial-statement labels must not use market or news features after this date.

Acceptance criteria:

```text
Bronze-to-Silver helper -> receives duplicate business keys -> chooses the row with the latest created_ts.
Feature/OBT builder -> joins features to a financial statement -> uses report_release_date or event_timestamp as the reference time and excludes future features.
Runtime Bronze writer -> writes evidence rows -> includes ingest_ts to separate ingestion time from source event time.
```

## 10. Dataset Contracts

### 10.1 Companies

Current contract location:

```text
src/metadata/schema_registry.py
```

Required fields:

```text
ticker
company_name
exchange
created_ts
```

Nullable fields:

```text
industry
sector
listing_date
delisted_flag
company_size
```

Grain:

```text
One row per company snapshot.
```

### 10.2 Financial Statements

Required fields:

```text
ticker
report_period
fiscal_year
fiscal_quarter
total_assets
total_liabilities
equity
created_ts
```

Nullable fields:

```text
current_assets
current_liabilities
revenue
ebit
interest_expense
net_income
operating_cash_flow
retained_earnings
report_release_date
event_timestamp
```

Grain:

```text
One row per ticker per report period.
```

### 10.3 Market Prices Daily

Required fields:

```text
ticker
trading_date
close_price
volume
created_ts
```

Nullable fields:

```text
open_price
high_price
low_price
market_cap
shares_outstanding
event_timestamp
```

Grain:

```text
One row per ticker per trading date.
```

### 10.4 Distress Labels

Current implementation:

```text
src/transforms/compute_distress_labels.py
```

Grain:

```text
One row per ticker per report period.
```

Fields:

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

`rule_version` is currently `v1`.

Stage 1 uses the non-manufacturing Altman Z double-prime style score:

```text
working_capital = current_assets - current_liabilities

Z'' =
  6.56 * (working_capital / total_assets)
+ 3.26 * (retained_earnings / total_assets)
+ 6.72 * (ebit / total_assets)
+ 1.05 * (equity / total_liabilities)
```

Warning rules:

- `high_debt_to_asset`: `total_liabilities / total_assets > 0.8`
- `low_current_ratio`: `current_assets / current_liabilities < 1.0`
- `two_quarter_net_loss`: current and previous quarter `net_income < 0`
- `negative_equity`: `equity < 0`
- `weak_interest_coverage`: `ebit / interest_expense < 1.0`

Label policy:

- `distress_label = 1` if `z_score < 1.1` or at least two warning rules are true.
- `distress_label = 0` if `z_score > 2.6` and fewer than two warning rules are true.
- If `1.1 <= z_score <= 2.6` and fewer than two warning rules are true, set `distress_label = 0` and include `gray_zone_monitor` in `distress_reason`.
- If `z_score` is null, still apply warning rules. If at least two warning rules are true, set `distress_label = 1` and include `z_score_null`; otherwise set `distress_label = NULL` and include `insufficient_data`.
- Null or zero denominators make the affected ratio null instead of raising an exception.

Acceptance criteria:

```text
Distress label helper -> receives complete safe-zone ratios -> computes Z'' and returns distress_label 0 with z_score_safe_zone.
Distress label helper -> receives gray-zone Z'' and fewer than two warnings -> returns distress_label 0 with gray_zone_monitor.
Distress label helper -> receives null Z'' and fewer than two warnings -> returns distress_label NULL with insufficient_data.
Distress label helper -> receives at least two warning rules -> returns distress_label 1 even when Z'' is null.
```

### 10.5 Stream Events

Current implementation supports:

- `financial.price_events`
- `financial.alert_events`

Designed but not yet implemented in code:

- `financial.news_events`

Required record fields from `StreamEvent.as_record()`:

```text
topic
event_id
event_type
ticker
event_timestamp
created_ts
```

`StreamEvent.price_update()` produces deterministic event IDs by hashing the payload. `StreamEvent.alert()` uses UUIDs.

`financial.news_events` remains a Phase 1 design contract because `docs/01_data_generator.md` and `docs/02_schema_design.md` define news sentiment data for ML-readiness. It is not represented by a current `StreamEvent` factory or collector implementation, so it must be reported as a remaining gap until implemented.

## 11. Volume Strategy

The Stage 1 coursework design includes a volume target, but the current repository only ships small deterministic fixtures for tests and smoke runs.

Approximate design volume:

| Dataset | Calculation | Target records |
|---|---:|---:|
| `financial_statements` | 300 tickers * 32 quarters | ~9,600 |
| `market_prices_daily` | 300 tickers * ~2,000 trading days | ~600,000 |
| `price_events` | historical replay or polling stream | primary driver for `>=20M` target |

Acceptance criteria:

```text
Coursework reviewer -> reads volume section -> sees that >=20M is a design target driven by streaming replay, not current fixture output.
CI runner -> runs tests -> uses small deterministic fixtures rather than generating high-volume data.
Evidence builder -> generates runtime data -> records actual row counts separately from target design volume.
```

## 12. Bronze-to-Silver Contract

Current implementation:

```text
src/transforms/bronze_to_silver.py
```

Implemented behavior:

- Normalize column names by stripping whitespace and lowercasing keys.
- Validate required fields.
- Allow nullable fields to be missing.
- Route invalid records to a failed-record list with `failure_reason` and `raw_payload`.
- Deduplicate valid rows by business keys.
- Keep the row with the latest `created_ts`.

Test coverage:

- `tests/test_bronze_to_silver.py`

Acceptance criteria:

```text
Bronze-to-Silver helper -> receives missing nullable fields -> returns valid Silver row with nullable fields set to null.
Bronze-to-Silver helper -> receives duplicate business keys -> keeps only the row with the latest created_ts.
Bronze-to-Silver helper -> receives missing required fields -> returns failed record with failure_reason and raw_payload.
```

## 13. Gold Transformation Contract

Current implementation:

```text
src/transforms/silver_to_gold.py
src/transforms/compute_distress_labels.py
src/transforms/keys.py
```

Implemented helper outputs:

- `dim_company`
- `dim_date`
- `fact_financial_statement`
- `fact_market_price`
- `distress_labels`
- `obt_company_quarter_risk`
- point-in-time feature joins through `pit_join_features()`

Implemented behavior:

- Stable case-insensitive `company_key`.
- `date_key` in `yyyymmdd` integer format.
- SCD2-like `dim_company` rebuild behavior for tracked company fields.
- Financial statement fact rows enriched with `company_key` and `date_key`.
- Market price fact rows enriched with `daily_return` and `volatility_signal`.
- Rule-based distress labels using Altman Z double-prime style components plus warning rules.
- Risk OBT ratios such as current ratio, debt-to-asset, debt-to-equity, ROA, ROE, and EBIT interest coverage.
- Point-in-time joins that do not use future feature timestamps.

### 13.1 SCD2 Key Policy

`company_key` is deterministic and case-insensitive:

```text
company_key = sha256(upper(ticker)).hexdigest()[:16]
```

`dim_company` stores SCD2-like versions with:

```text
valid_from_ts
valid_to_ts
is_current
```

Facts currently store `company_key` and `date_key` only. They do not store `company_version_key`. Historical joins resolve the correct dimension version through the temporal range policy already documented in `docs/02_schema_design.md`:

```text
dim_company.company_key = fact.company_key
AND dim_company.valid_from_ts <= fact_reference_ts
AND (fact_reference_ts < dim_company.valid_to_ts OR dim_company.valid_to_ts IS NULL)
```

`fact_reference_ts` is:

- `report_release_date` for financial statement facts.
- `trading_date` for market price facts.
- `event_timestamp` for news sentiment facts.

This is an explicit Stage 1 design choice, not an accidental omission. A future `company_version_key` can be added only through a schema/code change that also updates fact builders and tests.

### 13.2 Feature Table Contracts

Implemented helper behavior:

- `pit_join_features()` joins reference rows to the latest feature row for the same ticker where `feature.event_timestamp <= reference.event_timestamp`.

Designed Gold feature tables, not yet fully implemented as separate builders:

- `feat_company_financial_4q`
- `feat_company_market_30d`
- `feat_company_news_30d`
- `feat_company_unified`

PIT policy:

```text
entity key: ticker or company_key
reference timestamp: label/event/report timestamp on the reference row
feature eligibility: feature.event_timestamp <= reference.event_timestamp
market/news aggregation window: 30 days ending at report_release_date for obt_company_quarter_risk
financial aggregation window: last 4 quarters available at or before the reference timestamp
```

`feat_company_news_30d` and news-driven OBT fields are design contracts only until `financial.news_events` and `fact_news_sentiment` are implemented.

Test coverage:

- `tests/test_keys.py`
- `tests/test_silver_to_gold.py`
- `tests/test_distress_labels.py`

Acceptance criteria:

```text
Gold key helper -> receives ticker in mixed case -> returns stable case-insensitive company_key.
Gold date helper -> receives ISO timestamp -> returns yyyymmdd date_key.
Gold dim_company builder -> receives changed tracked fields -> emits historical and current rows with stable company_key.
Gold financial fact builder -> receives statement rows -> adds company_key and date_key.
Distress label helper -> receives safe financial ratios -> returns distress_label 0 with safe-zone reason.
Distress label helper -> receives multiple warning signals -> returns distress_label 1 with triggered reasons.
PIT join helper -> receives future and past features -> selects only feature rows at or before reference timestamp.
```

## 14. Streaming Contract

Current implementation:

```text
src/streaming/events.py
src/streaming/kafka_to_bronze_consumer.py
```

Implemented behavior:

- Build normalized price update records.
- Build normalized market alert records.
- Preserve `financial.news_events` as a design topic that still needs implementation.
- Buffer events in `MicroBatchConsumer`.
- Flush by record count or elapsed time.
- Group flushed batches by topic.
- Produce Bronze target paths partitioned by `event_date` and `event_hour`.

Current Bronze path pattern:

```text
s3a://financial-distress-lake/bronze/kafka/{topic}/event_date={YYYY-MM-DD}/event_hour={HH}/
```

Designed Bronze evidence path from `docs/01_data_generator.md` includes `batch_id`:

```text
s3a://financial-distress-lake/bronze/kafka/{topic}/event_date=YYYY-MM-DD/event_hour=HH/batch_id=.../
```

The current `MicroBatchConsumer` returns the topic/date/hour prefix and exposes `batch_id` in the batch payload, but does not yet include `batch_id` in `bronze_path`.

Test coverage:

- `tests/test_streaming.py`

Acceptance criteria:

```text
Stream event factory -> creates price update -> returns normalized record with deterministic event_id.
Micro-batch consumer -> reaches flush_record_count -> flushes one batch grouped by topic.
Micro-batch consumer -> flushes events -> returns Bronze path partitioned by event_date and event_hour.
```

## 15. Data Quality Contract

Current implementation:

```text
src/quality/dq_checks.py
configs/dq_rules.yaml
```

Implemented checks:

- `check_not_null()`
- `check_unique()`
- `check_referential_integrity()`
- `check_retention()`

Implemented severity behavior:

- Null, uniqueness, and referential-integrity failures return `status="fail"` and `severity="critical"`.
- Retention below threshold returns `status="warning"` and `severity="warning"`.

Test coverage:

- `tests/test_dq_checks.py`

Acceptance criteria:

```text
DQ not-null check -> receives null critical field -> returns fail with critical severity.
DQ referential check -> receives unknown dimension key -> returns fail with critical severity.
DQ retention check -> receives low retained row ratio -> returns warning with warning severity.
```

Runtime note:

The Python DQ helpers return result objects. Writing those results to PostgreSQL metadata is represented by `MetadataWriter.log_dq_result()` and by `project_metadata.data_quality_result` DDL, but an executed database-backed DQ job is still part of remaining runtime evidence work.

## 16. Metadata Contract

Current implementation:

```text
src/metadata/metadata_writer.py
src/metadata/schema_registry.py
sql/init_project_metadata.sql
```

In-memory helper lists:

- `pipeline_run_log`
- `data_quality_result`
- `failed_records`
- `source_request_log`
- `collector_checkpoint`

PostgreSQL schema:

```text
project_metadata
```

PostgreSQL tables defined in SQL:

- `pipeline_run_log`
- `data_quality_result`
- `dataset_freshness`
- `schema_version_registry`
- `failed_records`
- `backfill_request`
- `source_request_log`
- `collector_checkpoint`

Acceptance criteria:

```text
Metadata SQL -> runs against local PostgreSQL -> creates project_metadata schema and Phase 1 metadata tables.
Metadata writer -> logs collector run -> appends run record with run_id, dag_id, task_id, dataset_name, status, and row counts.
Metadata writer -> logs failed record -> appends record_id, dataset_name, failure_reason, raw_payload, and created_at.
Schema registry -> receives known dataset name -> returns current required and nullable field contract.
```

Runtime note:

`MetadataWriter` is currently an in-memory test/smoke helper, not a PostgreSQL client. The SQL DDL defines the database contract for local runtime evidence.

## 17. DuckDB and DBeaver Contract

Current implementation:

```text
src/catalog/duckdb_catalog.py
sql/duckdb_create_views.sql
sql/duckdb_validation_queries.sql
```

Implemented behavior:

- Generate DuckDB `httpfs` setup SQL.
- Generate `CREATE OR REPLACE VIEW` SQL over Parquet paths.
- Provide SQL view contracts for Gold datasets.
- Provide validation query contracts.

Current Gold view names:

- `gold_fact_financial_statement`
- `gold_fact_market_price`
- `gold_obt_company_quarter_risk`
- `gold_feat_company_unified`

Designed Gold views not yet present in `sql/duckdb_create_views.sql`:

- `gold_fact_news_sentiment`
- `gold_feat_company_financial_4q`
- `gold_feat_company_market_30d`
- `gold_feat_company_news_30d`

Acceptance criteria:

```text
DuckDB catalog helper -> receives endpoint and credentials -> returns httpfs setup SQL for local MinIO.
DuckDB catalog helper -> receives view name and Parquet path -> returns CREATE OR REPLACE VIEW SQL.
DBeaver user -> connects to DuckDB/PostgreSQL -> can inspect Gold views and project_metadata tables after runtime evidence is generated.
```

## 18. Airflow DAG Contract

Current DAG files:

- `01_collect_company_master_data.py`
- `02_collect_financial_statement_api.py`
- `03_collect_market_price_api.py`
- `04_stream_market_events_to_kafka.py`
- `05_transform_bronze_to_silver.py`
- `06_pyspark_silver_to_gold.py`
- `07_run_data_quality_checks.py`
- `08_minio_duckdb_register_tables.py`

Current behavior:

- DAGs are import-safe when Airflow is not installed.
- DAGs use `PythonOperator` if Airflow imports are available.
- DAG tasks call fixture-backed collectors or smoke helper functions.
- DAGs are scaffolding for evidence, not yet full production DAGs with external API calls, Spark submit, MinIO writes, or PostgreSQL client transactions.

Acceptance criteria:

```text
Python test runner -> imports DAG files without Airflow installed -> import does not fail due to guarded Airflow imports.
Airflow runtime -> loads DAG files with Airflow installed -> creates Stage 1 DAGs with manual schedules and stage tags.
Stage 1 DAG task -> calls smoke helper -> returns deterministic rows or SQL strings for evidence scaffolding.
```

## 19. Local Docker Contract

Current implementation:

```text
docker-compose.yml
.env.example
```

Defined services:

- `postgres`
- `minio`
- `kafka`
- `airflow-webserver`
- `airflow-scheduler`

Useful commands:

```bash
cp .env.example .env
docker compose config
docker compose up -d postgres minio kafka
docker compose up -d airflow-webserver airflow-scheduler
```

Runtime note:

The Docker stack definition exists, but this document does not claim that the full stack has already been executed end to end. That proof belongs in `docs/evidence/` after runtime evidence is captured.

## 20. Verification Commands

Current local quality commands:

```bash
pytest tests
ruff check src dags tests
black --check src dags tests
docker compose config
```

The GitHub Actions workflow mirrors these gates for `main` and `dev` branch pushes and pull requests.

Expected test coverage:

```text
tests/test_bronze_to_silver.py
tests/test_distress_labels.py
tests/test_dq_checks.py
tests/test_keys.py
tests/test_silver_to_gold.py
tests/test_streaming.py
```

Acceptance criteria:

```text
Developer -> runs pytest tests -> all current unit tests pass.
Developer -> runs ruff check src dags tests -> lint gate passes.
Developer -> runs black --check src dags tests -> formatting gate passes.
Developer -> runs docker compose config -> compose file is valid.
GitHub Actions -> runs on dev pull request -> executes Ruff, Black, PyTest, and Docker Compose config gates.
```

## 21. Evidence Targets

The final coursework evidence should be generated under:

```text
docs/evidence/
```

Expected evidence artifacts:

- Test command output.
- `docker compose config` output.
- PostgreSQL table screenshots or query exports for `project_metadata`.
- MinIO bucket screenshots showing Bronze/Silver/Gold paths after data is written.
- DuckDB SQL query outputs against Gold views.
- DBeaver screenshots for PostgreSQL metadata and DuckDB views.
- Airflow DAG screenshots if the local Airflow services are run.

Evidence not yet present should be documented as a remaining task, not described as already completed.

## 22. Current Gaps

These are known gaps between the current repository and a fully executed local lakehouse demo:

- Live online API adapters are not implemented. Current collectors use deterministic fixtures.
- `financial.news_events`, `fact_news_sentiment`, and `feat_company_news_30d` are design contracts only; no current collector/event factory/builders generate them.
- Separate builders for `feat_company_financial_4q`, `feat_company_market_30d`, and `feat_company_unified` are not implemented beyond the generic `pit_join_features()` helper and DuckDB view contract for unified features.
- Kafka broker integration is not exercised by tests. Current streaming tests cover event and micro-batch contracts.
- PySpark jobs are not implemented as real Spark submit jobs. Current Gold transforms are pure Python helper functions designed to mirror the target contracts.
- MinIO Parquet writes are not executed by the current unit tests.
- PostgreSQL metadata writes are not executed by the current unit tests. SQL DDL and in-memory metadata helpers exist.
- Airflow DAGs are smoke scaffolds. They do not yet run full end-to-end jobs against live Docker services.
- `docs/evidence/` runtime artifacts still need to be generated.

These gaps are acceptable for the current Stage 1 codebase as long as they are reported honestly and not represented as completed runtime evidence.

## 23. Implementation Order for Remaining Evidence Work

Recommended next steps:

1. Run quality gates locally.
2. Start PostgreSQL, MinIO, and Kafka with Docker Compose.
3. Confirm PostgreSQL initializes `project_metadata` from `sql/init_project_metadata.sql`.
4. Add or run a small script/DAG task that writes fixture collector outputs to local Bronze paths.
5. Convert fixture Bronze rows through Silver and Gold helper contracts.
6. Write sample outputs to MinIO-compatible paths or a local evidence substitute if Spark/MinIO runtime is not available.
7. Run DuckDB view SQL or validation SQL against generated Parquet evidence.
8. Capture DBeaver screenshots or query exports.
9. Store evidence under `docs/evidence/`.
10. Update this document only with evidence that actually exists.

## 24. Acceptance Criteria Summary

```text
Future engineer -> reads mini_coursework.md -> understands the exact current Stage 1 implementation state.
Future engineer -> follows repository layout -> finds every referenced module, DAG, SQL file, config file, and test file.
Future engineer -> runs listed verification commands -> can validate the current code contracts.
Coursework reviewer -> inspects documentation -> can distinguish implemented code from remaining runtime evidence work.
Coding agent -> starts new Phase 1 task -> preserves local-first boundaries and does not introduce cloud-only services.
```

## 25. Phase 2 Boundary

Phase 2 must remain separate from the current Phase 1 pipeline foundation.

If Phase 2 is explicitly requested later:

- ML code belongs under `src/ml/`.
- Drift code belongs under `src/drift/`.
- ML metadata belongs under `ml_metadata`.
- Phase 2 must not silently change Phase 1 collectors, schema contracts, DQ rules, or Gold output semantics.

Until then, this repository should continue to treat Stage 1 as a local-first data engineering coursework platform.
