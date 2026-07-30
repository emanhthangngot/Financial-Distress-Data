# Financial Distress Data Platform

Local-first mini-coursework platform for generating difficult financial data,
processing it with Spark and Flink, orchestrating three Airflow pipelines, and
publishing governance metadata to DataHub.

![Deployment architecture](images/architecture/deployment-architecture.png)

## Contents

1. [Domain](#domain)
2. [Architecture](#architecture)
3. [Repository](#repository)
4. [Quick Start](#quick-start)
5. [Pipelines](#pipelines)
6. [Validation](#validation)
7. [Detailed Evidence](#detailed-evidence)

## Domain

The platform builds company, financial statement, market, news, distress-label,
and point-in-time feature datasets. It deliberately generates skew, high
cardinality, schema evolution, duplicates, bursts, late events, and out-of-order
events so processing strategies can be measured against controlled baselines.

## Architecture

Deployable units are Airflow, Kafka, Spark, Flink, MinIO, PostgreSQL, DataHub,
and DuckDB/DBeaver. Airflow owns retries and atomic publication gates; Spark
owns bounded lakehouse processing; Flink owns event-time streaming; DataHub
stores ownership, lineage, assertions, and contracts.

See [the numbered deployment flows](docs/system-architecture.md).

## Repository

```text
dags/       Airflow DP1, DP2, and DP3 DAG definitions
src/        generator, transforms, streaming, governance, evidence, and IO code
flink/      executable PyFlink jobs
configs/    generator, processing, schema, governance, and rubric contracts
sql/        PostgreSQL metadata, DuckDB views, and schema evidence DDL
infra/      pinned Airflow and Flink images
scripts/    runtime, benchmark, evidence, and audit entry points
tests/      focused unit, contract, integration, and evidence tests
docs/       reviewer-facing design, results, and runbooks
plans/      implementation phases and completion reports
```

## Quick Start

Requirements: Docker with Compose, Python 3.11 or 3.12, and `uv` or a virtual
environment.

```bash
uv sync --all-extras
POSTGRES_HOST_PORT=55432 docker compose up -d
docker compose ps
```

Core service endpoints:

| Service | Endpoint |
|---|---|
| Airflow | `http://localhost:8080` |
| MinIO API / console | `http://localhost:9000` / `http://localhost:9001` |
| PostgreSQL | `localhost:55432` |
| Kafka host listener | `localhost:9094` |
| Flink profile | `http://localhost:8081` |
| DataHub evidence window | `http://localhost:9002` |

DataHub's quickstart and coursework Kafka both default to host port `9092`.
Follow the separate governance evidence window in
[DataHub governance](docs/data-governance.md).

## Pipelines

| DAG | Purpose | Publication gate |
|---|---|---|
| `ingest_source_to_bronze` | batch source and Kafka to Bronze | schema and count validation |
| `build_silver_gold` | Spark Bronze to Silver/Gold | staged DQ then atomic promotion |
| `build_offline_features` | PIT-safe offline feature tables | timestamp and leakage audit |

The three DAGs can run independently and share a deterministic logical-interval
run ID. See [pipeline orchestration](docs/data-pipeline-orchestration.md).

## Validation

```bash
uv run pytest -q tests
uv run ruff check src dags scripts tests
uv run black --check src dags scripts tests
POSTGRES_HOST_PORT=55432 docker compose config --quiet
git diff --check
```

Build the reviewer schema database:

```bash
uv run --with duckdb python scripts/build_schema_evidence.py \
  --output warehouse.db \
  --report docs/evidence/schema/phase8-schema-audit.json
```

Build a new immutable package, or audit the accepted package:

```bash
uv run python scripts/run_mini_coursework_submission.py \
  --profile evidence \
  --run-id <new-run-id>
uv run python scripts/audit_mini_coursework_rubric.py \
  --evidence-dir docs/evidence/final/coursework-final-20260731T0030 \
  --require-score 100
```

## Detailed Evidence

- [Data generator](docs/data-generator.md)
- [Spark and storage optimization](docs/spark-and-storage-optimization.md)
- [Flink stream processing](docs/flink-stream-processing.md)
- [Airflow orchestration](docs/data-pipeline-orchestration.md)
- [DataHub governance](docs/data-governance.md)
- [Schema design](docs/schema-design.md)
- [Docker optimization](docs/docker-optimization.md)
- [Novel idea: evidence manifest](docs/novel-idea-evidence-manifest.md)
- [Novel idea: PIT leakage guard](docs/novel-idea-pit-leakage-guard.md)
- [Evidence index](docs/evidence-index.md)

The repository does not claim production readiness. Final rubric points are
accepted only when the Phase 9 manifest and mock audit verify every linked
artifact from one run.
