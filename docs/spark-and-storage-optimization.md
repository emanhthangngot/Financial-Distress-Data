# Spark And Storage Optimization

Stage 4 compares two implementations against the same generated source run,
`generator-evidence-v1`. The benchmark uses one warm-up followed by five
measured executions and verifies input and output digests before comparing
performance.

## Reproduce

```bash
python scripts/run_spark_benchmark.py \
  --variant baseline \
  --runs 5 \
  --warmups 1 \
  --source-manifest docs/evidence/generator/source-manifest.json \
  --output /tmp/spark-baseline.json \
  --include-storage

python scripts/run_spark_benchmark.py \
  --variant optimized \
  --runs 5 \
  --warmups 1 \
  --source-manifest docs/evidence/generator/source-manifest.json \
  --output /tmp/spark-optimized.json \
  --include-storage

python scripts/audit_spark_benchmark.py \
  --baseline /tmp/spark-baseline.json \
  --optimized /tmp/spark-optimized.json
```

The local Docker runtime provides the S3A dependencies and MinIO endpoint used
by the checked-in evidence. Benchmark settings, source path, partition counts,
and salt count are versioned in `configs/spark-benchmark.yaml`.

## Correctness Contract

Both paths read 10,204 company records and 80,000 financial statements. They
produce five sector aggregates with output digest
`404f6e52d8b959a4164974a6836d0c73837012e53fd014b2f85fcabc727b7b64`.
The audit fails if the run ID, input digest, output digest, row count, or storage
row counts differ.

The baseline deliberately retains manual schema alignment, window-based latest
row selection, disabled automatic broadcast, and 24 shuffle/output partitions.
The optimized path uses `unionByName(..., allowMissingColumns=True)`, `max_by`
latest-row aggregation, explicit broadcast of the small company dimension,
per-company preaggregation, deterministic sector salting, AQE, and eight
shuffle partitions. The first salting-only candidate yielded only about 0.5%
improvement and was rejected; preaggregation was added after inspecting its
extra exchanges.

## Measured Results

| Signal | Baseline | Optimized | Result |
|---|---:|---:|---:|
| Median compute time | 1.251296 s | 0.802365 s | 1.5595x faster |
| Window operators | 6 | 0 | Removed global window dedup |
| Broadcast operators | 0 | 4 | Small dimension broadcast |
| Output files | 24 | 2 | 22 fewer files |
| Filtered read time | 0.438756 s | 0.181349 s | 2.4194x faster |
| Stored bytes | 5,576,064 | 3,644,981 | 34.6% smaller |

The optimized storage layout partitions by `fiscal_year` and compacts each
year. These values are local evidence, not a general cluster performance
guarantee. Full JSON results and live Spark UI snapshots are under
`docs/evidence/spark/`; screenshots are under `docs/evidence/screenshots/`.

## PostgreSQL Index Experiment

`sql/postgres-index-benchmark.sql` builds a temporary 250,000-row representative
request-log workload and captures JSON `EXPLAIN (ANALYZE, BUFFERS)` before and
after a selective composite index. The recorded plan changes from `Seq Scan` to
`Index Scan`; execution time falls from 23.717 ms to 0.061 ms, and the script
then installs the equivalent index on
`project_metadata.source_request_log(run_id, request_status, requested_at DESC)`.

## Rubric Boundary

Stage 4 implements and verifies R14-R18, R25, and R26 (14 points). R19 requires
the optimized callable to run inside the rubric DP2 Airflow DAG. The callable
is ready, but DP2 is intentionally created and runtime-verified in Stage 6; R19
must remain pending until that evidence exists.
