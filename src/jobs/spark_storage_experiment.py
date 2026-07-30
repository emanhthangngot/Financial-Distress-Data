"""Measured small-file and partition-pruning experiment for Spark/MinIO."""

from __future__ import annotations

import time
from typing import Any

from src.jobs.spark_benchmark_common import BenchmarkConfig


def _parquet_files(spark: Any, path: str) -> list[dict[str, Any]]:
    jvm = spark.sparkContext._jvm
    hadoop = spark.sparkContext._jsc.hadoopConfiguration()
    root = jvm.org.apache.hadoop.fs.Path(path)
    filesystem = root.getFileSystem(hadoop)
    iterator = filesystem.listFiles(root, True)
    files = []
    while iterator.hasNext():
        status = iterator.next()
        if status.getPath().getName().endswith(".parquet"):
            files.append(
                {
                    "path": status.getPath().toString(),
                    "bytes": int(status.getLen()),
                }
            )
    return files


def run_storage_experiment(
    spark: Any,
    statements: Any,
    config: BenchmarkConfig,
    variant: str,
) -> dict[str, Any]:
    """Write equivalent rows with baseline or compacted partition layout."""
    from pyspark.sql import functions as F

    settings = getattr(config, variant)
    path = f"{config.output_root}/storage/{variant}"
    started = time.perf_counter()
    writer = statements
    if variant == "baseline":
        writer = writer.repartition(settings.output_files)
        writer.write.mode("overwrite").parquet(path)
    else:
        partition_columns = list(config.storage.partition_columns)
        writer = writer.repartition(*[F.col(column) for column in partition_columns])
        writer.write.mode("overwrite").partitionBy(*partition_columns).parquet(path)
    write_seconds = time.perf_counter() - started

    files = _parquet_files(spark, path)
    query_started = time.perf_counter()
    filtered_count = (
        spark.read.parquet(path)
        .filter(F.col("fiscal_year") == config.storage.query_filter_year)
        .count()
    )
    query_seconds = time.perf_counter() - query_started
    total_bytes = sum(item["bytes"] for item in files)
    return {
        "path": path,
        "row_count": statements.count(),
        "filtered_year": config.storage.query_filter_year,
        "filtered_row_count": filtered_count,
        "file_count": len(files),
        "total_bytes": total_bytes,
        "average_file_bytes": round(total_bytes / len(files), 2) if files else 0.0,
        "write_seconds": round(write_seconds, 6),
        "filtered_read_seconds": round(query_seconds, 6),
        "files": files,
    }
