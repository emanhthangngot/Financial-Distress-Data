from __future__ import annotations

from typing import Any


def write_partitioned_parquet(dataframe: Any, path: str, partition_columns: list[str]) -> None:
    (dataframe.write.mode("overwrite").partitionBy(*partition_columns).parquet(path))
