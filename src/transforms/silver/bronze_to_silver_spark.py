"""Compatibility import for the canonical PySpark Bronze-to-Silver transform."""

from src.transforms.silver.spark import bronze_to_silver_spark

__all__ = ["bronze_to_silver_spark"]
