---
title: "Phase 2: Rebuild The Data Plane On Iceberg And Spark"
status: todo
priority: P1
effort: "1.5 weeks"
dependencies: [1]
---

# Phase 2: Rebuild The Data Plane On Iceberg And Spark

## Overview

Scale the generator from 16 rows to 10-50M rows, move bronze/silver/gold onto
Apache Iceberg over MinIO, and rebuild the Spark batch layer so the rubric's
skew-handling, Spark-UI and lakehouse-optimization rows rest on measurable
behaviour instead of assertion. Add Trino + Superset as the analytic plane.

## Requirements

Functional:
- [ ] Generator emits 10-50M rows / 5-20 GB with configurable skew, cardinality, schema evolution, duplicate and late-arrival rates
- [ ] A `label` table with exactly two columns (`company_id`, `label`) joinable to every feature table
- [ ] Configurable data drift injection, driven by a generator config file, not code edits
- [ ] Bronze/silver/gold as Iceberg tables on MinIO with a REST catalog
- [ ] Spark jobs: baseline (unoptimized) and optimized variants, both runnable and both captured on the Spark UI
- [ ] Skew handled with an explained technique (salting or AQE skew join), with before/after stage timings
- [ ] Lakehouse optimization: small-file compaction plus partitioning/sort-order, each with a measured before/after
- [ ] Trino queries Iceberg; Superset dashboards read through Trino

Non-functional:
- [ ] Generation is reproducible from a seed; the same config yields the same dataset
- [ ] The full generate + bronze→gold run completes in under 2 hours on the target node pool

## Architecture

Iceberg replaces bare Parquet as the table format. The catalog is an Iceberg REST
catalog backed by Postgres, so Spark writes and Trino/DuckDB read the same tables
without a metastore fork. Iceberg snapshots become the mechanism behind the
"data versioning, incremental" rubric row in phase 5 — each training pull pins a
snapshot ID rather than copying data.

The skew evidence needs a genuine bottleneck. The generator's `top_share`
parameter is raised so one partition key holds a dominant share of rows; at 10M+
rows this produces a Spark stage where one task runs an order of magnitude longer
than its peers, visible on the Spark UI timeline. The optimized job applies key
salting and AQE skew-join handling; the same screenshot pair before and after is
the deliverable.

Small-file evidence comes from the streaming path (phase 3) writing many small
Iceberg data files; `rewrite_data_files` compaction then collapses them. File
counts and query latency before and after are the measurement.

## Related Code Files

- Modify: `src/generator/**` (volume, drift injection, config schema), `src/transforms/**` (Iceberg writes), `dags/build_silver_gold.py`, `dags/06_pyspark_silver_to_gold.py`, `dags/ingest_source_to_bronze.py`
- Create: `src/lakehouse/iceberg_catalog.py`, `src/lakehouse/compaction.py`, `configs/generator-scale.yaml`, `configs/generator-drift.yaml`, `src/jobs/spark_baseline.py`, `src/jobs/spark_optimized.py`, `scripts/run_spark_skew_benchmark.py`, `scripts/run_lakehouse_compaction_benchmark.py`, `infra/trino/`, `infra/superset/`
- Modify: `docker-compose.yml` (Iceberg REST catalog, Trino, Superset services)

## Implementation Steps

1. Extend the generator config schema with `volume`, `skew.top_share`, `drift`, `duplicate_rate`, `late_rate`, `schema_evolution` and a `seed`. Cover the schema with validation tests before generating anything.
2. Implement drift injection: a scheduled shift in feature distributions between generation windows, so the phase-5 drift detector has real drift to find and the label table has a real relationship to shift against.
3. Emit the label table (`company_id`, `label`) as its own Iceberg table, derived from the distress definition already in `src/transforms/`.
4. Stand up the Iceberg REST catalog in Compose (Postgres-backed) and point Spark, Trino and DuckDB at it.
5. Port bronze/silver/gold writes to Iceberg, preserving the existing data contract: bronze append-only, silver/gold idempotent partition overwrite, dedupe by business key + latest `created_ts`.
6. Write `spark_baseline.py` with deliberately no optimization: no partition pruning, default shuffle partitions, no skew handling, no broadcast hints.
7. Write `spark_optimized.py` applying, each as a separately measurable step: partition pruning, shuffle-partition tuning, broadcast join for the small dimension, salting + AQE for the skewed key, and file-size targets.
8. Run both at 10M rows minimum, capture Spark UI stage timelines and event logs, and record per-optimization deltas in a benchmark JSON.
9. Implement `rewrite_data_files` compaction with a sort order; measure file count, average file size and Trino query latency before and after.
10. Deploy Trino (1 coordinator + 1 worker) and Superset; build one dashboard over the gold OBT table so the analytic plane in the reference diagram is real.
11. Wire both Spark jobs into the Airflow DAGs so the "Spark job integrated into data pipelines" row is satisfied by orchestration, not a manual run.

## Success Criteria

- [ ] Generator produces ≥10M rows from `configs/generator-scale.yaml`; row counts and byte size recorded in a characteristics artifact
- [ ] Two Spark UI screenshots show a skewed stage (one task ≥10x the median task duration) and the same stage after the fix
- [ ] Benchmark JSON records wall-clock and shuffle-bytes per optimization step, baseline vs optimized
- [ ] Compaction reduces file count by ≥10x with a recorded query-latency delta
- [ ] Trino returns correct results against the same Iceberg tables Spark wrote
- [ ] A Superset dashboard renders over Trino
- [ ] Airflow DAG runs the Spark job end-to-end and lands gold tables
- [ ] `python scripts/run_quality_gates.py` passes

## Risk Assessment

- **10-50M rows will not fit local disk or the node pool.** Mitigation: size the dataset at the low end (10M) first, measure actual bytes, and only scale up if the node pool and MinIO PVC have headroom. Generation is seeded, so scaling up is a re-run, not a rewrite.
- **Iceberg migration breaks Phase 1 data contracts.** Mitigation: the contract tests already exist; run them against Iceberg-backed tables before deleting any Parquet path. The contract is the spec — if a test fails, the Iceberg write is wrong, not the test.
- **Spark on a 4-vCPU node is too slow to iterate.** Mitigation: develop against a 100K-row sample locally; run full-volume benchmarks only for evidence capture, in a dedicated cluster window.
- **Superset carries no rubric row.** It is the first cut if the schedule slips. Do not let it block Trino, which the analytic diagram depends on.
