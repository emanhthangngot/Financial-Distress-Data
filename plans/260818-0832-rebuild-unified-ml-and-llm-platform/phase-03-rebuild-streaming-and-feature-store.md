---
title: "Phase 3: Rebuild Streaming And The Feature Store"
status: todo
priority: P1
effort: "1 week"
dependencies: [2]
---

# Phase 3: Rebuild Streaming And The Feature Store

## Overview

Rebuild the streaming path exactly as the reference draws it — Debezium CDC from
the source Postgres into Kafka, Flink for real-time feature engineering, Feast
materializing into Redis (online) and Postgres (offline) — plus the two streaming
push jobs and the incremental materialization pipeline the rubric names
explicitly. Register everything in DataHub for lineage and governance.

## Requirements

Functional:
- [ ] Debezium captures changes from the source Postgres into Kafka topics
- [ ] A Kafka schema registry holds the CDC subjects; the Flink job deserializes against the registered schema, so a source DDL change fails the contract instead of the job
- [ ] Flink computes windowed real-time features from those topics
- [ ] Feast feature views defined for both batch (Spark/Iceberg) and streaming features
- [ ] Job 1: push streaming features to the **offline** store, deployable and independently runnable
- [ ] Job 2: push streaming features to the **online** store, deployable and independently runnable
- [ ] An Airflow pipeline incrementally materializes the newest offline data into the online store
- [ ] Every feature table has an explicit TTL with a written justification
- [ ] DataHub shows lineage across source → bronze → silver → gold → feature view
- [ ] Data governance checks run over the pipeline as in the mini-coursework

Non-functional:
- [ ] Materialization is incremental — it must not rewrite the full online store per run
- [ ] Online feature reads return in under 50 ms p99 from Redis

## Architecture

Reference 1's `ns: recsys-dataflow` maps one-to-one:

```
source Postgres ──Debezium CDC──▶ Kafka ──▶ Flink (windowed features)
                                              │
Spark batch features ────────────────────────▶ Feast offline store (Postgres)
                                              │
                                    Feast materialize (incremental)
                                              ▼
                                    Feast online store (Redis)
```

TTL rationale is a graded deliverable, not a config detail. Each feature view's TTL
is set from the update cadence of its source: quarterly financial-statement
features get a TTL spanning a reporting quarter plus a filing-lag margin; daily
market-price features get a short TTL; streaming behavioural features get a TTL on
the order of the window they aggregate. The justification is written per table.

Debezium runs as a Kafka Connect connector. This adds one deployable unit against
the previous direct-to-Kafka generator path, which is the point — CDC appears in
both reference diagrams and makes the source-of-truth story honest.

## Related Code Files

- Create: `src/cdc/debezium_connector.py`, `src/streaming/flink_feature_job.py`, `src/jobs/push_stream_features_offline.py`, `src/jobs/push_stream_features_online.py`, `dags/feature_materialize.py`, `infra/debezium/`, `feature_repo/feature_views/streaming.py`, `docs/feature-store.md`
- Modify: `feature_repo/**` (feature views, entities, TTLs), `src/streaming/**`, `infra/flink/`, `infra/kafka/kafka_init_topics.sh`, `src/governance/**`, `src/catalog/**` (DataHub emitters), `docker-compose.yml`
- Delete: `dags/phase2/phase2_stream_feature_offline.py`, `dags/phase2/phase2_stream_feature_online.py`, `dags/phase2/phase2_feature_materialize.py` (the `phase2/` wrapper directory disappears with the phase split)

## Implementation Steps

1. Remove `dags/phase2/` entirely; flatten its wrappers into first-class DAGs under `dags/`, since the phase distinction no longer exists.
2. Deploy Kafka Connect + Debezium against the source Postgres; register connectors for the source tables and verify change events land in Kafka.
3. Rewrite the Flink job to consume Debezium envelopes (not raw generator events) and emit windowed features: rolling aggregates over the market-price and statement streams.
4. Define Feast entities and feature views for batch features (Iceberg-backed offline) and streaming features, each with an explicit TTL and a written justification in `docs/feature-store.md`.
5. Implement job 1 (stream → offline store): consume the Flink output topic, write to the Feast offline store with idempotent upsert semantics.
6. Implement job 2 (stream → online store): consume the same topic, push to Redis via the Feast push API, with at-least-once handling that is idempotent on the key.
7. Build the Airflow materialization DAG: read a watermark, materialize only the delta window offline→online, advance the watermark atomically. Prove incrementality by asserting the row count touched is bounded by the window, not the table.
8. Emit DataHub lineage from every stage **through the Kafka emitter**, never the REST emitter — DataHub scales to zero outside its window, and a REST emit against a down GMS loses the lineage silently rather than failing loudly. Verify the graph renders source→bronze→silver→gold→feature-view without breaks once GMS is up.
9. Run the existing data-quality and governance checks over the new pipeline; route critical failures to halt and warning failures to `failed_records` as the contract requires.
10. Benchmark online read latency from Redis under a synthetic key load; record p50/p95/p99.

## Success Criteria

- [ ] A row updated in source Postgres appears as a Kafka change event within 5 s
- [ ] Flink produces windowed features observable on its output topic
- [ ] Both push jobs run as independent deployable units and are visible as separate Airflow tasks/services
- [ ] The materialization DAG's second run touches only the delta window, proven by a logged row count and watermark advance
- [ ] Every feature view has a TTL and a justification paragraph naming its source cadence
- [ ] DataHub lineage graph is unbroken from source to feature view
- [ ] Redis online reads meet p99 < 50 ms in the recorded benchmark
- [ ] `python scripts/run_quality_gates.py` passes

## Risk Assessment

- **Debezium adds operational surface (Connect cluster, offsets, schema history).** Mitigation: run it single-connector, single-task; snapshot mode `initial` once, then streaming. If Connect proves unstable in the cluster window, the generator's direct-to-Kafka path remains as a documented fallback — CDC is architecture fidelity, not a rubric row.
- **Feast + Iceberg offline store integration is thinner than Feast + Parquet.** Mitigation: validate the offline retrieval path against Iceberg early in the phase; if the connector is inadequate, register the offline store against the Iceberg tables' underlying Parquet location and keep snapshot pinning at the job level.
- **Incrementality is easy to claim and easy to fake.** Mitigation: the success criterion is a logged bounded row count, not a passing DAG. Assert it in a test.
