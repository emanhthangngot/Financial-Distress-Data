# Financial Distress Data Engineering System

Local-first Stage 1 mini-coursework for a Financial Distress analytics data platform.

## Scope

Stage 1 implements:

- `docs/01_data_generator.md`
- `docs/02_schema_design.md`
- offline/API batch collectors
- Kafka-first streaming event contracts
- Bronze/Silver/Gold transform helpers
- PostgreSQL metadata contracts
- DuckDB over MinIO serving SQL
- PyTest and GitHub Actions quality gates

Out of scope for Stage 1: drift simulation, ML training, LLM, Kubernetes, AWS S3, Glue, Athena, RDS, EMR, MSK, Redshift, and SageMaker.

## Local Stack

- Airflow local Docker
- Kafka single-node KRaft
- PySpark local mode design
- PostgreSQL schema `project_metadata`
- MinIO bucket `financial-distress-lake`
- DuckDB `httpfs` views for local SQL evidence

## Run Checks

```bash
python -m pip install -r requirements.txt
pytest tests
ruff check src dags tests
black --check src dags tests
docker compose config
```

## Start Local Services

```bash
cp .env.example .env
docker compose up -d postgres minio kafka
```

Airflow services are included in `docker-compose.yml` for DAG evidence, but the Python tests are intentionally lightweight and do not require the Docker stack.

## Evidence Targets

- PostgreSQL metadata: `project_metadata.pipeline_run_log`, `data_quality_result`, `schema_version_registry`, `failed_records`
- MinIO paths: `s3a://financial-distress-lake/bronze`, `silver`, `gold`
- DuckDB SQL: `sql/duckdb_create_views.sql`, `sql/duckdb_validation_queries.sql`
- DBeaver screenshots and query outputs under `docs/evidence/`
