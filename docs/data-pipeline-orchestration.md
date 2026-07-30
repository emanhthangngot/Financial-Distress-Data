# Data Pipeline Orchestration

Phase 6 exposes three independently reviewable Airflow DAGs. Each pipeline uses
a stable run ID derived from the logical interval, retries transient failures,
and places a critical validation task before publication.

## DP1: Source To Bronze

`ingest_source_to_bronze` runs:

```text
resolve_run
  -> ingest_batch_to_bronze
  -> ingest_stream_to_bronze
  -> validate_bronze
  -> publish_manifest
```

Batch inputs are written to Bronze MinIO objects. Streaming inputs are produced
to Kafka and consumed into Bronze micro-batches. Empty batch datasets or zero
stream records block publication.

## DP2: Silver And Gold

`build_silver_gold` runs:

```text
resolve_run
  -> spark_build_silver_gold
  -> validate_silver_gold
  -> publish_manifest
```

The build task invokes the verified Spark lakehouse implementation. The
validation gate requires all core Silver datasets, dimensions, and facts to be
non-empty before the run is published.

## DP3: Offline Features

`build_offline_features` runs:

```text
resolve_run
  -> compute_offline_features
  -> validate_point_in_time_features
  -> publish_manifest
```

Four feature datasets are written under `_staging/<run_id>/`. Airflow passes
only compact counts and a PIT audit through XCom. The validation task rejects
empty outputs, missing creation timestamps, and features newer than their
reference event. Publication atomically promotes all four staged prefixes and
restores the previous snapshot if promotion fails.

## Runtime Configuration

Airflow receives service endpoints through environment-backed Variables and a
PostgreSQL metadata Connection:

- `AIRFLOW_CONN_PROJECT_METADATA`
- `AIRFLOW_VAR_FINANCIAL_DISTRESS_BUCKET`
- `AIRFLOW_VAR_KAFKA_BOOTSTRAP_SERVERS`

No secret values are checked into a dotenv file. Compose defaults are local
development credentials and can be overridden through the shell environment.

## Reproduce

```bash
POSTGRES_HOST_PORT=55432 docker compose up -d \
  postgres minio minio-init kafka kafka-init

POSTGRES_HOST_PORT=55432 docker compose run --rm --no-deps \
  airflow-scheduler airflow dags list-import-errors

POSTGRES_HOST_PORT=55432 docker compose run --rm --no-deps \
  airflow-scheduler airflow dags test ingest_source_to_bronze \
  2026-07-30T12:02:00+00:00

POSTGRES_HOST_PORT=55432 docker compose run --rm --no-deps \
  airflow-scheduler airflow dags test build_silver_gold \
  2026-07-30T12:02:00+00:00

POSTGRES_HOST_PORT=55432 docker compose run --rm --no-deps \
  airflow-scheduler airflow dags test build_offline_features \
  2026-07-30T12:02:00+00:00
```

Export reviewer evidence from Airflow metadata:

```bash
python scripts/export_phase6_airflow_evidence.py \
  --dsn postgresql://airflow:airflow@localhost:55432/financial_distress \
  --output docs/evidence/airflow/phase6-runtime.json
```
