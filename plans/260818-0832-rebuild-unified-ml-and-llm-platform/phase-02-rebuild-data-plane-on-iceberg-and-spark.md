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
- [ ] Generator config declares an explicit synthetic timeline: `timeline.start`, `timeline.end`, `timeline.period` and `label_horizon`, expressed in periods rather than wall-clock dates
- [ ] A `label` table joinable to every feature table, carrying `company_id`, `label` **and `label_event_ts`** — the timestamp at which the distress outcome became observable
- [ ] A frozen evaluation set `gold.distress_holdout_v1`, pinned by an Iceberg tag, with a train/embargo/holdout split derived from the generator's `label_horizon`
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

### The synthetic timeline and `label_horizon`

The generator currently has no notion of time beyond row order, which makes three
things in this plan inexpressible: the holdout split (phase 2), the drift
detector's reference window (phase 5) and the point-in-time leakage guard (phase
8). All three need to know **when** a feature was observable and **when** its label
became known. So the timeline becomes a first-class config object rather than an
implicit consequence of generation order:

```yaml
timeline:
  start: 2020-01-01        # synthetic epoch — not the wall clock
  end:   2026-01-01
  period: month            # the unit every other window is counted in
label_horizon: 12          # periods between as_of_date and label_event_ts
```

`label_horizon` is the load-bearing one. A distress label is not observable at the
moment its features are: the outcome is defined as *distress occurring within
`label_horizon` periods after `as_of_date`*, so `label_event_ts = as_of_date +
label_horizon`. Every other boundary in the plan is derived from it — the embargo
width, the holdout's mature-label cutoff, and the leakage guard's overlap test —
which is why it lives in the generator config and is read from there, never
restated. A hard-coded 12 in one module and a config value of 6 in another produces
an embargo that looks present and does nothing.

Rows whose `label_event_ts` falls past `timeline.end` have **immature labels**: the
outcome has not happened yet within the generated world. They must be emitted with
`label IS NULL`, not with `label = 0`. Defaulting them to negative is the single
most damaging shortcut available here — it inflates every evaluation metric,
concentrates the distortion in the most recent data, and produces no error anywhere.

### The frozen evaluation set

Model promotion in phase 5 compares a candidate against the champion. That
comparison is only meaningful if both are scored on the **same** data, so the
evaluation set is cut once here and frozen, rather than being re-derived from a
rolling window at promotion time. A rolling window fails silently: the pipeline
still runs, still emits an AUC, and still promotes — but the number compares two
models sitting different exams, so the gate stops protecting anything without ever
raising an error.

The split follows the generator's own time axis, not the wall clock, since the
dataset is synthetic and its timeline is a config parameter:

```
   TRAIN                    EMBARGO              HOLDOUT v1        immature
├────────────────────────┤├─────────────────┤├──────────────────┤├──────────▶
                          ◀─ label_horizon ─▶  ◀─ ≥ 4 label periods ─▶
```

- **Embargo** spans exactly one `label_horizon` and is discarded. Without it, a
  training row's label window overlaps a holdout row's, so the model has already
  seen the holdout period's outcome — the same leak the phase-8 point-in-time
  guard is built to catch, arriving through the split rather than through a
  feature.
- **Holdout** spans at least four label periods so it covers a full reporting
  cycle rather than one seasonal slice, and includes only rows whose
  `label_event_ts` has already passed at cut time — immature labels read as
  negatives and inflate the score.
- The window is **placed to include a generator drift episode**, so a candidate
  that overfits the calm regime is visible at the gate rather than in production.

Freezing is an Iceberg tag, not a copy. `CREATE TAG holdout-v1 ... RETAIN 3650
DAYS` pins the snapshot; Iceberg's own ref semantics then protect it from
`expire_snapshots`, which is why the tag must exist **before** any maintenance DAG
is scheduled. The split boundaries live in one module, `src/lakehouse/holdout.py`,
which both the phase-5 training pull and the phase-7 promotion gate import — two
copies of a date constant is how the embargo silently disappears.

## Related Code Files

- Modify: `src/generator/**` (volume, drift injection, config schema, timeline + `label_horizon`), `src/transforms/**` (Iceberg writes), `dags/build_silver_gold.py`, `dags/06_pyspark_silver_to_gold.py`, `dags/ingest_source_to_bronze.py`
- Create: `src/lakehouse/iceberg_catalog.py`, `src/lakehouse/compaction.py`, `src/lakehouse/holdout.py`, `scripts/create_holdout_snapshot.py`, `dags/iceberg_maintenance.py`, `configs/generator-scale.yaml`, `configs/generator-drift.yaml`, `src/jobs/spark_baseline.py`, `src/jobs/spark_optimized.py`, `scripts/run_spark_skew_benchmark.py`, `scripts/run_lakehouse_compaction_benchmark.py`, `infra/trino/`, `infra/superset/`
- Modify: `docker-compose.yml` (Iceberg REST catalog, Trino, Superset services)

## Implementation Steps

1. Extend the generator config schema with `volume`, `skew.top_share`, `drift`, `duplicate_rate`, `late_rate`, `schema_evolution`, `seed`, and the timeline block: `timeline.start`, `timeline.end`, `timeline.period`, `label_horizon`. Cover the schema with validation tests before generating anything, including two rules that are cheap here and expensive later: `label_horizon >= 1`, and `timeline` must span at least `label_horizon + embargo + holdout_window + 1` periods, otherwise no valid split exists and generation should fail rather than silently produce a dataset the phase-5 gate cannot use.
2. Implement drift injection: a scheduled shift in feature distributions between generation windows, so the phase-5 drift detector has real drift to find and the label table has a real relationship to shift against. Declare the shift points as explicit periods on the timeline (`drift.episodes: [{start, end, magnitude}]`) rather than as a rate, so step 13 can place the holdout window over a known episode instead of guessing where drift landed.
3. Emit the label table (`company_id`, `as_of_date`, `label`, `label_event_ts`) as its own Iceberg table, derived from the distress definition already in `src/transforms/`, with `label_event_ts = as_of_date + label_horizon` read from the config. Emit `label = NULL` wherever `label_event_ts > timeline.end`. `label_event_ts` is what makes both the holdout split and the phase-8 leakage guard expressible; a label with no event time cannot be checked for leakage or held out by time.
4. Stand up the Iceberg REST catalog in Compose (Postgres-backed) and point Spark, Trino and DuckDB at it.
5. Port bronze/silver/gold writes to Iceberg, preserving the existing data contract: bronze append-only, silver/gold idempotent partition overwrite, dedupe by business key + latest `created_ts`.
6. Write `spark_baseline.py` with deliberately no optimization: no partition pruning, default shuffle partitions, no skew handling, no broadcast hints.
7. Write `spark_optimized.py` applying, each as a separately measurable step: partition pruning, shuffle-partition tuning, broadcast join for the small dimension, salting + AQE for the skewed key, and file-size targets.
8. Run both at 10M rows minimum, capture Spark UI stage timelines and event logs, and record per-optimization deltas in a benchmark JSON.
9. Implement `rewrite_data_files` compaction with a sort order; measure file count, average file size and Trino query latency before and after.
10. Deploy Trino (1 coordinator + 1 worker) and Superset; build one dashboard over the gold OBT table so the analytic plane in the reference diagram is real.
11. Wire both Spark jobs into the Airflow DAGs so the "Spark job integrated into data pipelines" row is satisfied by orchestration, not a manual run.
12. Define the split in `src/lakehouse/holdout.py`, **reading `label_horizon` and `timeline` from the generator config** rather than restating them: `EMBARGO = label_horizon`, `HOLDOUT_END = timeline.end - label_horizon` (the last mature label), `HOLDOUT_START = HOLDOUT_END - holdout_window`, `TRAIN_END = HOLDOUT_START - EMBARGO - 1`, plus `TRAIN_FILTER` and `HOLDOUT_TAG`. Deriving instead of hard-coding is what keeps a later generator-config change from leaving a stale embargo behind — the failure mode being that the boundaries still look deliberate while no longer separating anything.
13. Choose `holdout_window` so the window covers at least one full `drift.episodes` entry and at least four periods, then run `scripts/create_holdout_snapshot.py` once: create `gold.distress_holdout_v1` over the holdout window with mature labels only, assert the quality thresholds below, then `CREATE TAG holdout-v1 ... RETAIN 3650 DAYS` and write the resulting snapshot ID back into `holdout.py`.
14. Verify the tag resolves (`SELECT * FROM gold.distress_holdout_v1.refs WHERE name = 'holdout-v1'` returns one row of type `TAG`) and add a daily CI test asserting both the tag's existence and the frozen row count. **Only then** schedule `dags/iceberg_maintenance.py` (`expire_snapshots` with `retain_last => 10`, `rewrite_data_files`, `rewrite_manifests`) — ordering the tag after the maintenance DAG risks the snapshot being expired before it is pinned.
15. Apply the embargo to the training path: the gold training pull reads `TRAIN_FILTER` from `holdout.py`, never its own date literal.

## Success Criteria

- [ ] Generator produces ≥10M rows from `configs/generator-scale.yaml`; row counts and byte size recorded in a characteristics artifact
- [ ] Config validation rejects a `timeline` too short to admit a valid train/embargo/holdout split, and rejects `label_horizon < 1`
- [ ] Every label row satisfies `label_event_ts = as_of_date + label_horizon`, and every row with `label_event_ts > timeline.end` carries `label IS NULL` — asserted by a test, not by inspection
- [ ] `holdout.py` derives all boundaries from the generator config; changing `label_horizon` in the config and re-running the boundary test shifts the embargo accordingly
- [ ] Two Spark UI screenshots show a skewed stage (one task ≥10x the median task duration) and the same stage after the fix
- [ ] Benchmark JSON records wall-clock and shuffle-bytes per optimization step, baseline vs optimized
- [ ] Compaction reduces file count by ≥10x with a recorded query-latency delta
- [ ] Trino returns correct results against the same Iceberg tables Spark wrote
- [ ] A Superset dashboard renders over Trino
- [ ] Airflow DAG runs the Spark job end-to-end and lands gold tables
- [ ] `gold.distress_holdout_v1` exists with tag `holdout-v1`, zero null labels, no row whose `label_event_ts` post-dates the cut, and enough positives that a 0.01 AUC difference is not sampling noise (≥ 50 positives, ≥ 200 preferred)
- [ ] Train and holdout windows are provably disjoint by at least one `label_horizon`, asserted by a test over the boundaries in `holdout.py`
- [ ] The maintenance DAG runs `expire_snapshots` and the `holdout-v1` tag still resolves afterwards
- [ ] `python scripts/run_quality_gates.py` passes

## Risk Assessment

- **10-50M rows will not fit local disk or the node pool.** Mitigation: size the dataset at the low end (10M) first, measure actual bytes, and only scale up if the node pool and MinIO PVC have headroom. Generation is seeded, so scaling up is a re-run, not a rewrite.
- **Iceberg migration breaks platform data contracts.** Mitigation: the contract tests already exist; run them against Iceberg-backed tables before deleting any Parquet path. The contract is the spec — if a test fails, the Iceberg write is wrong, not the test.
- **Spark on a 4-vCPU node is too slow to iterate.** Mitigation: develop against a 100K-row sample locally; run full-volume benchmarks only for evidence capture, in a dedicated cluster window.
- **`label_horizon` gets restated somewhere instead of read from the config.** The embargo then silently stops matching the label window, and nothing fails — the split still exists, still looks intentional, and no longer prevents the overlap it was built to prevent. Mitigation: `holdout.py` is the only module that computes boundaries, it reads the config, and the phase-8 guard asserts the overlap independently. Two mechanisms because the failure is invisible to one.
- **The holdout window lands in a flat stretch of the generator timeline.** A candidate then scores well without ever being tested against drift, and the gate passes models that fail in the drift scenario phase 5 depends on. Mitigation: choose the window against the generated drift schedule in `configs/generator-drift.yaml`, and record the overlap in the holdout table's properties. This is cheap here and impossible to retrofit once the tag is cut.
- **Too few positives makes the gate noise.** Mitigation: assert the positive count at creation time and widen the window before tagging. After tagging, a fix means `holdout-v2` and re-scoring the champion — much more expensive than checking now.
- **Superset carries no rubric row.** It is the first cut if the schedule slips. Do not let it block Trino, which the analytic diagram depends on.
