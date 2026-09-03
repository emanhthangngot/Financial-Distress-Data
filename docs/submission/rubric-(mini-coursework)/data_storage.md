---
title: "Data Storage"
date: 2026-08-14
status: active
---

# Data Storage: lakehouse compaction and DuckDB indexing, both measured

This doc proves "Data Storage": a real small-file compaction pass on the
MinIO lakehouse (100 files → 1, zero row loss) and a DuckDB ART index that
measurably speeds up a point-lookup query. It does not claim these numbers
generalize to production-scale partition counts — both are local,
bounded-input measurements.

**Active deployment facts:** MinIO S3A lakehouse
(`s3a://financial-distress-lake/`), DuckDB `warehouse.db`.

## Part I — Lakehouse compaction

### 1. 100 small files compacted to 1, row count preserved

```json
{
  "n_input_files": 100, "n_output_files": 1,
  "input_total_bytes": 176873, "output_total_bytes": 119075,
  "target_file_mb": 128,
  "row_count_preserved": true, "rows_in": 20000, "rows_out": 20000
}
```

Full evidence:
[`docs/evidence/lakehouse_compaction_benchmark.json`](../../evidence/lakehouse_compaction_benchmark.json).
The optimized Spark storage layout (see `processing_jobs.md`) additionally
partitions by `fiscal_year` and compacts each year, contributing the 34.6%
stored-bytes reduction measured there.

## Part II — DuckDB indexing

### 2. ART index: 1.41x speedup on a point-lookup query

```json
{
  "query": "SELECT debt_to_equity, current_ratio, roa FROM obt_company_quarter_risk WHERE ticker = 'TKR0123' ORDER BY report_period LIMIT 1",
  "indexed_columns": ["ticker", "report_period"],
  "row_count": 200000,
  "before_ms": 4.627, "after_ms": 3.277,
  "speedup_factor": 1.412, "index_method": "duckdb_art"
}
```

Full evidence:
[`docs/evidence/duckdb_index_benchmark.json`](../../evidence/duckdb_index_benchmark.json).
The equivalent selective composite index
(`ops.source_request_log(run_id, request_status,
requested_at DESC)`) is proven separately by
`sql/postgres-index-benchmark.sql`: a 250,000-row workload shows `EXPLAIN
(ANALYZE, BUFFERS)` changing from `Seq Scan` to `Index Scan`, execution time
falling from 23.717 ms to 0.061 ms.

## Limitations

Both benchmarks run against local, bounded datasets (20,000 rows compacted;
200,000-row DuckDB table) — they demonstrate the optimization technique
correctly, not a production-scale performance guarantee at billions of rows.

## References

- DuckDB ART indexes: https://duckdb.org/docs/sql/indexes.html
