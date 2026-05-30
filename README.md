# Financial Distress Data Engineering System

![Stage 1 Online Local Lakehouse Architecture](images/architecture/architecture-stage-1.png)

Local-first Stage 1 lakehouse for Vietnamese financial distress analytics. The project collects online market and financial data, ingests batch and streaming paths, transforms data through Bronze, Silver, and Gold layers, and publishes local evidence through PostgreSQL, MinIO, DuckDB, and DBeaver.

## Project Goal

Build a production-oriented but coursework-sized data engineering foundation for financial risk analysis. Stage 1 focuses on the data platform only: collectors, schemas, orchestration, quality checks, local metadata, and analytical serving tables. ML training, drift monitoring, LLM workflows, cloud deployment, and Kubernetes are intentionally reserved for later phases.

## Stage 1 Scope

Implemented scope is aligned with:

- `docs/01_data_generator.md`
- `docs/02_schema_design.md`
- `docs/mini_coursework.md`
- `docs/spec.md`

Stage 1 includes:

- Online API batch collectors for company master data, financial statements, and market prices.
- WebSocket or polling adapters that normalize stream-like market events into Kafka contracts.
- Bronze raw storage for API payloads and streaming events.
- Bronze -> Silver cleaning helpers with schema and key enforcement.
- Silver -> Gold PySpark-oriented transforms for features and labels.
- Data quality checks with hard-fail and warning-level handling.
- PostgreSQL metadata tables under `project_metadata`.
- DuckDB SQL views over local MinIO Parquet for DBeaver inspection.
- PyTest and CI quality gates.

Out of scope for Stage 1:

- ML model training and scoring.
- Drift simulation or drift monitoring.
- LLM assistants and prediction APIs.
- AWS S3, Glue, Athena, RDS, EMR, MSK, Redshift, SageMaker, and Kubernetes.

## Architecture

The system runs as a local Docker-based lakehouse:

1. **Collection namespace** pulls online Vietnamese market data through isolated source adapters such as `vnstock`, HTTP JSON, and HTML table adapters.
2. **Streaming namespace** accepts WebSocket or polling events, publishes normalized events to Kafka, and flushes consumed events into Bronze storage.
3. **Storage namespace** stores raw, cleaned, and curated datasets in MinIO using lakehouse-style Bronze, Silver, and Gold zones.
4. **Orchestration namespace** uses Airflow DAGs to schedule collection, transformation, quality, and catalog registration tasks.
5. **Metadata namespace** writes run logs, DQ results, schema versions, failed records, request logs, and checkpoints to local PostgreSQL.
6. **Analytics namespace** exposes Gold datasets through DuckDB `httpfs` SQL and DBeaver evidence queries.

Core data flow:

```text
Online APIs / WebSocket / Polling
  -> Collectors and source adapters
  -> Kafka and raw Bronze payloads
  -> Bronze raw datasets in MinIO
  -> Silver cleaned datasets
  -> Gold feature and label datasets
  -> DuckDB SQL views and DBeaver evidence
```

## Technology Stack

| Layer | Tooling | Purpose |
|---|---|---|
| Orchestration | Apache Airflow | Local DAG scheduling and pipeline evidence |
| Streaming | Apache Kafka single-node KRaft | Normalized event transport |
| Batch processing | PySpark local mode | Silver and Gold transformations |
| Object storage | MinIO | Local S3-compatible Bronze/Silver/Gold lake |
| Metadata | PostgreSQL | `project_metadata` operational metadata |
| Query engine | DuckDB `httpfs` | Local SQL over MinIO Parquet |
| Inspection | DBeaver | PostgreSQL and DuckDB evidence review |
| Quality | PyTest, Ruff, Black | Test and style gates |

## Repository Layout

```text
dags/                  Airflow DAG definitions for Stage 1 workflows
src/collectors/        Online API collectors and source adapters
src/streaming/         Kafka event contracts and consumer logic
src/transforms/        Bronze -> Silver and Silver -> Gold transforms
src/quality/           Data quality checks and failure policy
src/catalog/           DuckDB catalog and MinIO view registration
src/metadata/          PostgreSQL metadata writers and schema registry
sql/                   PostgreSQL and DuckDB SQL contracts
configs/               Source mapping, Spark, collector, and DQ configs
tests/                 PyTest unit and contract tests
docs/                  Specs, coursework docs, and evidence targets
images/architecture/   Architecture diagrams used by documentation
```

## Quick Start

Create a local environment:

```bash
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"
```

Install local-runtime connectors when you are ready to run evidence jobs against
PostgreSQL, Kafka, PySpark, and MinIO:

```bash
python -m pip install -e ".[runtime]"
```

Create local configuration:

```bash
cp .env.example .env
```

Start the local platform services:

```bash
docker compose up -d postgres minio kafka
```

Optional Airflow services for DAG evidence:

```bash
docker compose up -d airflow-webserver airflow-scheduler
```

Service endpoints:

| Service | URL / Connection |
|---|---|
| Airflow | `http://localhost:8080` |
| MinIO API | `http://localhost:9000` |
| MinIO Console | `http://localhost:9001` |
| PostgreSQL | `localhost:5432`, database `financial_distress` |
| Kafka | `kafka:9092` inside Docker network |

## Verification

Run the local quality gates:

```bash
pytest tests
ruff check src dags tests
black --check src dags tests
docker compose config
```

The Python tests are intentionally lightweight and do not require the full Docker stack. Docker is required when collecting runtime evidence from PostgreSQL, Kafka, MinIO, Airflow, DuckDB, and DBeaver.

Runtime-capable Stage 1 adapters now live beside the deterministic test helpers:

- `src/metadata/metadata_writer.py`: `PostgresMetadataWriter` writes run logs, DQ results, and failed records into `project_metadata`.
- `src/transforms/spark_session.py`: builds a PySpark local session configured for MinIO S3A and dynamic partition overwrite.
- `src/transforms/bronze_to_silver.py` and `src/transforms/silver_to_gold.py`: include Spark DataFrame transform helpers while preserving pure-Python unit-test helpers.
- `src/streaming/kafka_to_bronze_consumer.py`: can consume JSON records from a real Kafka consumer into the existing micro-batch Bronze contract.

## Data Contracts

Primary storage paths use the local MinIO bucket:

```text
s3a://financial-distress-lake/bronze/
s3a://financial-distress-lake/silver/
s3a://financial-distress-lake/gold/
```

Gold datasets are designed for financial risk analytics and include cleaned financial statement facts, market features, and distress labels. Silver and Gold writes must be idempotent and overwrite affected partitions rather than blindly appending duplicate records.

## Metadata and Quality

PostgreSQL stores Stage 1 operational metadata in schema `project_metadata`:

- `pipeline_run_log`
- `data_quality_result`
- `dataset_freshness`
- `schema_version_registry`
- `failed_records`
- `backfill_request`
- `source_request_log`
- `collector_checkpoint`

Critical DQ failures halt downstream tasks. Warning-level failures are logged and routed to failed-record handling when applicable. All quality results must leave metadata evidence in PostgreSQL.

## DuckDB and DBeaver Evidence

DuckDB is used as the local SQL layer over MinIO Parquet files. DBeaver is the inspection client for both PostgreSQL metadata and DuckDB analytical views.

Useful SQL entry points:

- `sql/duckdb_create_views.sql`
- `sql/duckdb_validation_queries.sql`
- `sql/init_project_metadata.sql`

Expected evidence includes row counts, DQ outputs, run logs, failed-record samples, schema version rows, and DuckDB query results over Gold datasets.

## Development Rules

- Treat `AGENTS.md`, `docs/spec.md`, and `docs/mini_coursework.md` as mandatory project law.
- Keep Stage 1 local-first: no AWS, managed cloud services, or Kubernetes code.
- Keep Phase 2 ML and drift work isolated under `src/ml/` and `src/drift/` when explicitly requested.
- Write test seeds before implementing core behavior.
- Express acceptance criteria as `WHO -> ACTION -> RESULT`.
- Preserve idempotent Silver and Gold writes.

## Current Status

The repository contains Stage 1 contracts, module scaffolding, transformation helpers, Airflow DAG definitions, metadata SQL, DuckDB SQL, and test coverage for the local lakehouse foundation. The next evidence-oriented work is to run the Docker services end to end, capture PostgreSQL/DuckDB/DBeaver outputs, and place final screenshots or query exports under `docs/evidence/`.
