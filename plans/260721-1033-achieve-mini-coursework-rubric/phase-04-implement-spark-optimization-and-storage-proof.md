---
phase: 4
title: "Implement Spark Optimization And Storage Proof"
status: completed
priority: P1
effort: "1-2 weeks"
dependencies: [2, 3]
---

# Phase 4: Implement Spark Optimization And Storage Proof

## Overview

Create comparable baseline and optimized Spark/storage paths using generated problems.

## Requirements

- Baseline preserved for measurement.
- Optimizations address skew, high cardinality, schema evolution, and duplicates.
- Spark UI and metrics demonstrate improvement.
- Lakehouse and warehouse optimization experiments are measured.

## Related Code Files

- Create: `src/jobs/spark_baseline_job.py`
- Create: `src/jobs/spark_optimized_job.py`
- Create: `scripts/run_spark_benchmark.py`
- Create: `sql/postgres-index-benchmark.sql`
- Create: `docs/spark-and-storage-optimization.md`

## Implementation Steps

1. Define identical inputs, outputs, correctness checks, and benchmark protocol.
2. Measure baseline stages, shuffle, spill, skew, runtime, and file counts.
3. Apply evidence-driven techniques such as repartitioning/salting/broadcast only where measurements justify them.
4. Implement schema evolution and deterministic latest-row dedup.
5. Implement partitioning and small-file compaction; measure file count/size/read time.
6. Add useful PostgreSQL indexes; capture `EXPLAIN ANALYZE` before/after.
7. Integrate optimized job into DP2.

DP2 orchestration is intentionally deferred to Phase 6, where the three rubric
DAGs are created and runtime-verified together. Stage 4 delivers the callable
and benchmark contract but does not claim R19 yet.

## Experiment Matrix

| Problem | Baseline signal | Candidate optimization | Required comparison |
|---|---|---|---|
| Skew | Long-tail task duration, uneven shuffle | Salt/repartition/AQE after measurement | Max/median task time, runtime, shuffle |
| High cardinality | Large shuffle/state/aggregation cost | Partition strategy, preaggregation | Shuffle bytes, peak memory, runtime |
| Schema evolution | Read/union failure or manual branching | Explicit schema merge/alignment | Correctness and runtime overhead |
| Duplicates | Full sort/window cost | Partition-aware latest-row plan | Duplicate count and runtime |
| Small files | High file-open/list cost | Compaction and target size | File count/size/read latency |
| Warehouse lookup | Sequential scan | Selective PostgreSQL index | `EXPLAIN ANALYZE` cost/time |

## Task Breakdown

| ID | Task | Output | Rubric points |
|---|---|---|---:|
| P4-T1 | Freeze benchmark dataset and correctness digest | Benchmark manifest | - |
| P4-T2 | Implement unoptimized baseline | Baseline metrics/UI | 2 |
| P4-T3 | Optimize skew with evidence | Before/after report | 2 |
| P4-T4 | Optimize high-cardinality processing | Before/after report | 2 |
| P4-T5 | Handle schema evolution | Compatibility report | 2 |
| P4-T6 | Handle duplicate/other offline problem | Dedup report | 2 |
| P4-T7 | Integrate optimized Spark job into DP2 | Airflow task proof | 2 |
| P4-T8 | Implement partitioning/compaction experiment | Storage metrics | 2 |
| P4-T9 | Implement PostgreSQL index experiment | Query plans | 2 |

## Validation

```bash
python -m pytest -q tests/test_spark_transforms.py tests/integration/test_spark_lakehouse.py
python scripts/run_spark_benchmark.py --variant baseline --runs 5
python scripts/run_spark_benchmark.py --variant optimized --runs 5
python scripts/audit_spark_benchmark.py --require-equivalent-output
```

## Evidence Outputs

- Spark UI stage screenshots for baseline and each targeted issue.
- JSON/CSV metrics with median of repeated runs.
- Code excerpts linked from the optimization document.
- MinIO file-count/size and query-latency comparison.
- PostgreSQL `EXPLAIN ANALYZE` before/after.

## Success Criteria

- [x] Baseline and optimized outputs are semantically identical.
- [x] Each optimization maps to a measured problem and result.
- [x] Spark UI screenshots show the relevant before/after jobs and stages.
- [x] Compaction/partition and index reports satisfy all storage points.

## Risks And Rollback

Do not claim improvement from tiny fixtures. Record hardware, repetitions, warm-up policy, and median results.

## Unresolved Questions

- R19 remains pending until the optimized callable is executed by the DP2 DAG in Phase 6.
