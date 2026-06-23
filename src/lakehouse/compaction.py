"""Compaction + Z-order helpers for the Gold Parquet zone.

This module is the spine for W19 (lakehouse compaction + DW indexing). It
operates on plain Parquet files in a local-FS or S3A path. Full Spark runtime
is intentionally not required — DuckDB + pyarrow cover the unit-test surface
and the DAG hook uses the same primitives.
"""
