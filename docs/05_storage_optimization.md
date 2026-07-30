# 05. Storage Optimization

This document describes the storage-side optimizations applied to the
Gold lakehouse layer in Phase 1: small-file compaction, Z-order
clustering, and DuckDB index benchmarks for downstream analytical
queries.

All measurements below are reproducible; see [## Reproduce](#reproduce).

## Compaction

Small Parquet files are the typical by-product of micro-batch streaming
ingest and short-window backfills. They inflate the MinIO object count,
slow Spark planning, and make DuckDB's `httpfs` reads chatty.

The helper `src.lakehouse.compaction.compact_small_files` reads a
directory of small Parquet files, buckets rows round-robin into
``N`` target files, and writes them back as larger Parquet shards.

| Setting           | Default | Notes                                                |
| ----------------- | ------- | ---------------------------------------------------- |
| `target_file_mb`  | 128 MB  | Compaction writes approximately 128 MB output files. |
| `output_dir`      | None    | Defaults to a sibling ``_compacted`` directory.     |

The Airflow task `compact_gold_tables` in `dags/06_pyspark_silver_to_gold.py`
runs after `spark_build_gold_tables` and only triggers compaction when the
average output file size is below the `AVG_FILE_MB` threshold (default
64 MB). This avoids unnecessary rewrites on already-healthy partitions.

Evidence: `docs/evidence/lakehouse_compaction_benchmark.json`.

## Z-Order

Co-locating rows for a small set of high-cardinality columns dramatically
reduces the I/O for range and equality scans on those columns. The helper
`src.lakehouse.compaction.z_order_by` computes a 10-bit-per-column
interleaved Z-order key over the requested columns and sorts the
DataFrame by that key.

The Gold OBT (`obt_company_quarter_risk`) is Z-ordered by
(`ticker`, `report_period`) so that point-lookups and rolling-quarter
windows on a single ticker only need to read a contiguous slice of each
Parquet file.

## DuckDB Index Benchmark

Local DuckDB is the primary ad-hoc query surface (typically driven via
DBeaver). For the OBT table we add DuckDB ART secondary indexes on
(`ticker`, `report_period`) so point-lookups inside a single warehouse
session stay snappy even as the table grows.

| Indexed columns      | Table                       | Row count |
| -------------------- | --------------------------- | --------- |
| `ticker`, `report_period` | `obt_company_quarter_risk` | 200 000   |

A representative point-lookup query is timed before and after index
creation; the resulting `speedup_factor` is required to be `>= 1.0`.

Evidence: `docs/evidence/duckdb_index_benchmark.json`.

## Reproduce

```bash
# 1. Compaction benchmark (writes docs/evidence/lakehouse_compaction_benchmark.json)
.venv/bin/python scripts/demo_lakehouse_compaction.py

# 2. DuckDB index benchmark (writes docs/evidence/duckdb_index_benchmark.json)
.venv/bin/python scripts/demo_duckdb_index.py
```

The pytest suite in `tests/test_storage_optimization_doc.py` asserts the
existence of this document, the required sections, and the evidence
files referenced above.
