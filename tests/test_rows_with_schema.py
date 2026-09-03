"""Tests for src.jobs.lakehouse_spark_lakehouse_job._rows_with_schema.

Covers P-C from docs/_plans/codebase_recon_followups.md: deterministic type inference.
"""

from datetime import date, datetime

from pyspark.sql.types import (
    BooleanType,
    DoubleType,
    LongType,
    StringType,
    StructType,
)

from src.jobs.lakehouse_spark_lakehouse_job import _rows_with_schema


def test_homogeneous_strings_infer_string_type():
    rows = [{"name": "alice"}, {"name": "bob"}, {"name": "carol"}]
    _, schema = _rows_with_schema(rows)
    assert isinstance(schema, StructType)
    assert isinstance(schema.fields[0].dataType, StringType)


def test_homogeneous_ints_infer_long_type():
    rows = [{"x": 1}, {"x": 2}, {"x": 3}]
    _, schema = _rows_with_schema(rows)
    assert isinstance(schema.fields[0].dataType, LongType)


def test_homogeneous_floats_infer_double_type():
    rows = [{"x": 1.5}, {"x": 2.5}, {"x": 3.5}]
    _, schema = _rows_with_schema(rows)
    assert isinstance(schema.fields[0].dataType, DoubleType)


def test_homogeneous_bools_infer_boolean_type():
    rows = [{"flag": True}, {"flag": False}, {"flag": True}]
    _, schema = _rows_with_schema(rows)
    assert isinstance(schema.fields[0].dataType, BooleanType)


def test_all_null_column_infers_string_type():
    rows = [{"x": None}, {"x": None}]
    _, schema = _rows_with_schema(rows)
    assert isinstance(schema.fields[0].dataType, StringType)


def test_heterogeneous_mix_infers_string_type():
    rows = [{"x": 1}, {"x": "two"}, {"x": 3.0}, {"x": True}]
    _, schema = _rows_with_schema(rows)
    assert isinstance(schema.fields[0].dataType, StringType)


def test_datetime_values_in_string_field_pass_through():
    rows = [
        {"ts": datetime(2026, 1, 1, 9, 0, 0)},
        {"ts": date(2026, 1, 2)},
    ]
    normalized, schema = _rows_with_schema(rows)
    assert isinstance(schema.fields[0].dataType, StringType)
    assert normalized[0]["ts"] == "2026-01-01T09:00:00"
    assert normalized[1]["ts"] == "2026-01-02"
