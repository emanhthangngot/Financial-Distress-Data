"""
Bronze-to-Silver transform entry point.

Re-exports the pure-Python and PySpark implementations of the Bronze-to-Silver pipeline from
``src.transforms.silver``. Callers should depend on this module rather than the inner subpackage.
"""

from __future__ import annotations

from src.transforms.silver.core import (
    align_to_schema,
    bronze_to_silver,
    deduplicate_latest,
    normalize_columns,
)
from src.transforms.silver.spark import bronze_to_silver_spark

__all__ = [
    "align_to_schema",
    "bronze_to_silver",
    "bronze_to_silver_spark",
    "deduplicate_latest",
    "normalize_columns",
]
