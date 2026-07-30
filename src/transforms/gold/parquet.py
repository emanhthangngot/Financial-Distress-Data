"""
Parquet read/write helpers for the Gold zone.

Centralizes the S3A write options (compression, partitioning, overwrite-mode) used by every Gold
builder so the zone layout stays uniform.
"""

from __future__ import annotations

from typing import Any


def write_partitioned_parquet(dataframe: Any, path: str, partition_columns: list[str]) -> None:
    (dataframe.write.mode("overwrite").partitionBy(*partition_columns).parquet(path))
