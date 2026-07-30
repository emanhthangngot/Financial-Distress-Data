# Phase 4 Completion Report

## Status

Completed on 2026-07-23. R14-R18, R25, and R26 are implemented and verified.
R19 remains pending until DP2 is built and executed in Phase 6.

## Delivered

- Versioned benchmark contract and deterministic correctness digests.
- Separate baseline and optimized Spark implementations for skew, high
  cardinality, schema evolution, and duplicate handling.
- Repeated benchmark runner, equivalence auditor, storage compaction experiment,
  and live Spark UI HTML/screenshot evidence.
- PostgreSQL before/after `EXPLAIN ANALYZE` experiment and production index.
- Focused contract tests and reviewer documentation.

## Runtime Evidence

- Source: 10,204 companies and 80,000 financial statements.
- Identical output: 5 rows, digest
  `404f6e52d8b959a4164974a6836d0c73837012e53fd014b2f85fcabc727b7b64`.
- Spark median: 1.251296 s baseline versus 0.802365 s optimized (1.5595x).
- Storage: 24 files versus 2; filtered read 0.438756 s versus 0.181349 s.
- PostgreSQL: sequential scan 23.717 ms versus index scan 0.061 ms.

## Evidence Index

- `docs/evidence/spark/baseline.json`
- `docs/evidence/spark/optimized.json`
- `docs/evidence/spark/comparison.json`
- `docs/evidence/spark/postgres-index-benchmark.txt`
- `docs/evidence/screenshots/spark-ui-baseline.png`
- `docs/evidence/screenshots/spark-ui-optimized.png`
- `docs/spark-and-storage-optimization.md`

## Remaining Dependency

The optimized Spark callable is ready for orchestration, but claiming R19 before
the rubric DP2 DAG exists would be unsupported. Phase 6 owns its Airflow task,
run correlation, logs, and UI proof.

## Verification

- Focused Stage 4 tests: 9 passed.
- Full repository suite: 147 passed.
- Ruff, Python compileall, Docker Compose config, and `git diff --check`: passed.
- Benchmark equivalence audit: passed against the checked-in runtime artifacts.
- Manual code review found and closed a report-correlation gap by requiring
  matching run IDs, input populations, and storage populations.
