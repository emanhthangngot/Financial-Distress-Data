"""
Pure-Python Bronze-to-Silver primitives.

Column normalization, schema alignment, and ``deduplicate_latest`` over ``created_ts`` for each
business key. Used by the PySpark implementation and by unit tests that want a no-Spark path.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def normalize_columns(row: dict[str, Any]) -> dict[str, Any]:
    return {str(key).strip().lower(): value for key, value in row.items()}


def align_to_schema(
    row: dict[str, Any], required: list[str], nullable: list[str]
) -> dict[str, Any]:
    normalized = normalize_columns(row)
    missing_required = [field for field in required if normalized.get(field) is None]
    if missing_required:
        raise ValueError(f"missing required fields: {', '.join(missing_required)}")
    return {field: normalized.get(field) for field in [*required, *nullable]}


def deduplicate_latest(rows: Iterable[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    latest: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        business_key = tuple(row.get(key) for key in keys)
        current = latest.get(business_key)
        if current is None or str(row.get("created_ts", "")) >= str(current.get("created_ts", "")):
            latest[business_key] = row
    return list(latest.values())


def bronze_to_silver(
    rows: Iterable[dict[str, Any]],
    required: list[str],
    nullable: list[str],
    dedup_keys: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    valid: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for row in rows:
        try:
            valid.append(align_to_schema(row, required, nullable))
        except ValueError as exc:
            failed.append({"failure_reason": str(exc), "raw_payload": row})
    return deduplicate_latest(valid, dedup_keys), failed
