---
title: "Data Pipeline Orchestration"
date: 2026-08-14
status: active
---

# Data Pipeline Orchestration: three DP Airflow DAGs, each with an Ingest and Validate stage

This doc proves "Data Pipeline Orchestration": three independently
reviewable Airflow DAGs (DP1 source→Bronze, DP2 Bronze→Silver/Gold, DP3
offline features), each with a resolve→ingest→validate→publish shape, real
runs captured on the Airflow UI. It does not prove production-scale
scheduling load — these are functional-correctness DAG runs, not a
throughput benchmark.

**Active deployment facts:** Airflow (Docker Compose), connections/variables
sourced from environment (`AIRFLOW_CONN_PROJECT_METADATA`,
`AIRFLOW_VAR_FINANCIAL_DISTRESS_BUCKET`,
`AIRFLOW_VAR_KAFKA_BOOTSTRAP_SERVERS`) — no secret checked into a dotenv
file.

## Part I — DP1: source to Bronze

### 1. Ingest and validate stages

```text
resolve_run -> ingest_batch_to_bronze -> ingest_stream_to_bronze
            -> validate_bronze -> publish_manifest
```

Batch inputs write to Bronze MinIO objects; streaming inputs produce to
Kafka and consume into Bronze micro-batches. Empty batch datasets or zero
stream records block publication.

#### Image proof

![Airflow DAG graph: DP1 bronze ingest](../../pngs/airflow_dp1_bronze_ingest_dag.png)

*Image note:* live Airflow DAG graph for `ingest_source_to_bronze` shows the
resolve→ingest→validate→publish task chain in execution order. It proves
the DAG structure matches the documented contract. It does not show a
successful run by itself — see the successful-run capture below.

## Part II — DP2 and DP3

### 2. DP2: Silver and Gold

```text
resolve_run -> spark_build_silver_gold -> validate_silver_gold -> publish_manifest
```

The build task invokes the verified Spark lakehouse implementation
(`processing_jobs.md`); the validation gate requires all core Silver
datasets, dimensions, and facts to be non-empty before publication.

### 3. DP3: offline features

```text
resolve_run -> compute_offline_features -> validate_point_in_time_features
            -> publish_manifest
```

Four feature datasets are written under `_staging/<run_id>/`; Airflow passes
only compact counts and a PIT audit through XCom. The validation task
rejects empty outputs, missing creation timestamps, and features newer than
their reference event. Publication atomically promotes all four staged
prefixes and restores the previous snapshot if promotion fails.

#### Image proof

![Airflow DAG graph: DP2 silver/gold build](../../pngs/airflow_dp2_silver_gold_dag.png)
![Airflow DAG graph: DP3 offline features build](../../pngs/airflow_dp3_offline_features_dag.png)
![Airflow: successful DP2/DP3 task-tree run](../../pngs/airflow_dp2_dp3_successful_run.png)

*Image note:* live Airflow DAG graphs for `build_silver_gold` and
`build_offline_features`, plus a successful task-tree run capture. They
prove both DAG structures match their documented contract and that a real
run completed successfully. They do not show the actual row counts written —
those are recorded in `docs/evidence/airflow/phase6-runtime.json`.

## Reproduction

```bash
POSTGRES_HOST_PORT=55432 docker compose run --rm --no-deps airflow-scheduler \
  airflow dags test ingest_source_to_bronze 2026-07-30T12:02:00+00:00
POSTGRES_HOST_PORT=55432 docker compose run --rm --no-deps airflow-scheduler \
  airflow dags test build_silver_gold 2026-07-30T12:02:00+00:00
POSTGRES_HOST_PORT=55432 docker compose run --rm --no-deps airflow-scheduler \
  airflow dags test build_offline_features 2026-07-30T12:02:00+00:00

python scripts/export_phase6_airflow_evidence.py \
  --dsn postgresql://airflow:airflow@localhost:55432/financial_distress \
  --output docs/evidence/airflow/phase6-runtime.json
```

## Limitations

These are functional-correctness runs on generator-scale fixture data
(tens of thousands of rows), not a production-scheduling load test — Airflow
DAG concurrency, SLA misses, and retry-storm behavior at scale are out of
scope for this evidence set.

## References

- Apache Airflow DAGs: https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html
</content>
