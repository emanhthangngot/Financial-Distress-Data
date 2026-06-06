# Financial Distress Data Engineering System

## Introduction

This project is a local-first data engineering foundation for Financial Distress analytics. It runs a small lakehouse stack with Airflow, Kafka, MinIO, PostgreSQL, DuckDB, and PyTest-based validation.

The current Stage 1 pipeline uses deterministic fixture-backed collectors, then materializes Bronze, Silver, Gold, Data Quality, Metadata, and Evidence outputs locally.

## Overall System Architecture

<div style="text-align: center;">
  <img src="images/architecture/architecture-stage-1.png" style="width: 1188px; height: auto;">
</div>

# Table of Contents

1. [Project Structure](#project-structure)
2. [Local Setup](#local-setup)
3. [Running in Docker](#running-in-docker)
4. [Service URLs](#service-urls)
5. [Run Stage 1 Evidence](#run-stage-1-evidence)
6. [Validation Commands](#validation-commands)
7. [Useful Inspection Queries](#useful-inspection-queries)
8. [Stop Services](#stop-services)

## Project Structure

```txt
├── dags/                  - Airflow DAGs for Stage 1 workflows
├── src/                   - Python source code
│   ├── collectors/        - Fixture-backed source adapters and collectors
│   ├── streaming/         - Kafka event contracts and micro-batch logic
│   ├── transforms/        - Bronze/Silver/Gold transform logic
│   ├── quality/           - Data quality checks and DQ runner
│   ├── metadata/          - PostgreSQL metadata writers and schema registry
│   ├── catalog/           - DuckDB catalog and validation helpers
│   ├── io/                - MinIO and local IO helpers
│   └── jobs/              - Runtime evidence job wrappers
├── configs/               - Collector, Spark, source, and DQ config files
├── sql/                   - PostgreSQL metadata DDL and DuckDB SQL views
├── tests/                 - PyTest unit, contract, and runtime smoke tests
├── docs/                  - Specs and evidence notes
├── images/                - Architecture diagrams
├── init/                  - Kafka topic init script
├── scripts/               - Local E2E, DQ failure, and evidence audit runners
├── docker-compose.yml     - Local platform services
├── pyproject.toml         - Python package and tooling config
└── README.md              - This README file
```

# LOCAL

## Local Setup

Create or activate a Python environment, then install development and runtime dependencies.

```bash
python -m pip install -r requirements.txt
python -m pip install -e ".[dev,runtime]"
```

Create local environment config.

```bash
cp .env.example .env
```

## Running in Docker

Start the complete local data platform.

```bash
docker compose up -d
```

Check service status.

```bash
docker compose ps
.venv/bin/python scripts/check_stage1_services.py
```

Create Kafka topics manually if needed.

```bash
docker compose exec kafka bash /opt/financial-distress-init/kafka_init_topics.sh
```

## Service URLs

| Service | URL / Connection | Notes |
|---|---|---|
| Airflow | `http://localhost:8080` | Username/password: `airflow` / `airflow` |
| MinIO Console | `http://localhost:9001` | Username/password: `minioadmin` / `minioadmin` |
| MinIO API | `http://localhost:9000` | Bucket: `financial-distress-lake` |
| PostgreSQL | `localhost:55432` | DB: `financial_distress`, user/password: `airflow` / `airflow` |
| Kafka host listener | `localhost:9094` | Host-side access |
| Kafka Docker listener | `kafka:9092` | Container-side access |

## Run Stage 1 Evidence

Run the fixture-backed Stage 1 evidence pipeline from the host.

```bash
.venv/bin/python scripts/run_stage1_evidence.py
```

Run the connected local E2E path through Airflow, Kafka, Spark, MinIO,
PostgreSQL, and DuckDB.

```bash
.venv/bin/python scripts/run_stage1_real_e2e.py \
  --execution-date 2026-06-06T10:04:00+00:00 \
  --export-evidence /tmp/stage1-e2e
```

Generate a machine-readable audit summary for the E2E artifacts.

```bash
.venv/bin/python scripts/audit_stage1_evidence.py /tmp/stage1-e2e
```

Validate the checked-in submission evidence without regenerating files.

```bash
.venv/bin/python scripts/audit_stage1_evidence.py docs/evidence --check
```

Build a reviewer-facing readiness report from the checked-in evidence.

```bash
.venv/bin/python scripts/stage1_readiness_report.py
```

Prove critical DQ failures are persisted before the pipeline halts.

```bash
.venv/bin/python scripts/run_stage1_dq_failure_probe.py \
  --run-id stage1-dq-failure-probe \
  --export-evidence /tmp/stage1-dq-failure-probe
```

For a no-service payload check:

```bash
.venv/bin/python scripts/run_stage1_evidence.py --dry-run --evidence-dir /tmp/stage1-evidence
```

Run the primary Airflow evidence DAG once from the CLI.

```bash
docker compose exec airflow-scheduler airflow dags test stage1_local_evidence_pipeline 2026-06-06T02:00:00+00:00
```

Runtime evidence artifacts are written to MinIO:

```txt
financial-distress-lake/evidence/stage1/run_id=.../
```

Expected files:

```txt
stage1_row_counts.json
stage1_minio_objects.txt
stage1_stream_batches.json
stage1_duckdb_validation.json
```

The real E2E runner also exports:

```txt
stage1_real_airflow_dag_test.txt
stage1_real_kafka_offsets.json
stage1_real_minio_objects.json
stage1_real_postgres_summary.json
stage1_real_duckdb_validation.json
stage1_runtime_audit_summary.json
```

## Validation Commands

Run local quality gates.

```bash
.venv/bin/python scripts/run_stage1_quality_gates.py
```

Run quality gates plus Docker service readiness after the stack is up.

```bash
.venv/bin/python scripts/run_stage1_quality_gates.py --include-services
```

Build a readiness report plus live service checks after the stack is up.

```bash
.venv/bin/python scripts/stage1_readiness_report.py --include-services
```

The one-shot gate runs the same checks individually listed below.

```bash
.venv/bin/python -m pytest tests
.venv/bin/ruff check src dags tests scripts
.venv/bin/black --check src dags tests scripts
docker compose config
.venv/bin/python scripts/audit_stage1_evidence.py docs/evidence --check
```

List Kafka topics.

```bash
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --list
```

List Airflow DAGs.

```bash
docker compose exec airflow-scheduler airflow dags list
```

Inspect MinIO objects from inside the container.

```bash
docker compose exec minio sh -c 'ls -R /data/financial-distress-lake | head -120'
```

## Useful Inspection Queries

PostgreSQL metadata checks:

```bash
docker compose exec postgres psql -U airflow -d financial_distress -c \
"select dataset_name, status, count(*) from project_metadata.pipeline_run_log group by dataset_name, status order by dataset_name, status;"
```

```bash
docker compose exec postgres psql -U airflow -d financial_distress -c \
"select dataset_name, check_name, status, severity, count(*) from project_metadata.data_quality_result group by dataset_name, check_name, status, severity order by dataset_name, check_name;"
```

```bash
docker compose exec postgres psql -U airflow -d financial_distress -c \
"select dataset_name, status, freshness_lag_minutes, sla_minutes from project_metadata.dataset_freshness;"
```

```bash
docker compose exec postgres psql -U airflow -d financial_distress -c \
"select dataset_name, start_date, end_date, status, requested_by from project_metadata.backfill_request order by created_at desc limit 20;"
```

DuckDB validation output is generated at:

```txt
docs/evidence/stage1_duckdb_validation.json
```

Airflow DAG test output writes the same validation artifact to MinIO under the Stage 1 evidence prefix.

## Stop Services

Stop containers but keep volumes/data.

```bash
docker compose stop
```

Stop and remove containers/network.

```bash
docker compose down
```
