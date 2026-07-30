from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from src.metadata.schema_registry import SchemaContract, SchemaValidationError


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
        if current is None or _created_timestamp(row) >= _created_timestamp(current):
            latest[business_key] = row
    return list(latest.values())


def _created_timestamp(row: dict[str, Any]) -> datetime:
    value = row.get("created_ts")
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return datetime.min.replace(tzinfo=UTC)
    parsed = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def bronze_to_silver(
    rows: Iterable[dict[str, Any]],
    required: list[str],
    nullable: list[str],
    dedup_keys: list[str],
    *,
    field_types: dict[str, str] | None = None,
    enum_values: dict[str, list[Any]] | None = None,
    blank_as_null: bool = True,
    run_id: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    contract = SchemaContract(
        dataset_name="inline",
        schema_version="runtime",
        required=required,
        nullable=nullable,
        field_types=field_types,
        enum_values=enum_values,
        blank_as_null=blank_as_null,
    )
    valid: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for row in rows:
        try:
            aligned = (
                contract.validate_row(row)
                if field_types is not None
                else align_to_schema(row, required, nullable)
            )
            valid.append(aligned)
        except (SchemaValidationError, ValueError) as exc:
            failed.append({"failure_reason": str(exc), "raw_payload": row, "run_id": run_id})
    return deduplicate_latest(valid, dedup_keys), failed
