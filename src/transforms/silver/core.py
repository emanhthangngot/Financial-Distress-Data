"""Pure-Python Bronze-to-Silver normalization and deduplication primitives.

Supports latest-wins deduplication for snapshot tables and a separate path that retains every
knowledge-time vintage while identifying the latest vintage for each business key.
"""

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
        created_ts = _created_timestamp(row)
        business_key = tuple(row.get(key) for key in keys)
        current = latest.get(business_key)
        if current is None or created_ts >= _created_timestamp(current):
            latest[business_key] = row
    return list(latest.values())


def deduplicate_preserve_vintage(
    rows: Iterable[dict[str, Any]],
    keys: list[str],
    *,
    known_from_field: str = "known_from_ts",
) -> list[dict[str, Any]]:
    """Retain one ingest of every vintage and mark one latest vintage per business key."""

    by_vintage: dict[tuple[Any, ...], dict[str, Any]] = {}
    vintage_times: dict[tuple[Any, ...], datetime] = {}
    for source_row in rows:
        row = dict(source_row)
        known_value = row.get(known_from_field)
        if known_value in (None, ""):
            known_value = next(
                (
                    row.get(field)
                    for field in ("report_release_date", "event_timestamp", "created_ts")
                    if row.get(field) not in (None, "")
                ),
                None,
            )
            if known_value is None:
                raise ValueError(
                    f"{known_from_field} or a source timestamp is required to preserve vintages"
                )
            row[known_from_field] = known_value
        known_from = _parse_timestamp(known_value, field=known_from_field)
        created_ts = _created_timestamp(row)
        business_key = tuple(row.get(key) for key in keys)
        vintage_key = (*business_key, known_from)
        current = by_vintage.get(vintage_key)
        if current is None or created_ts >= _created_timestamp(current):
            by_vintage[vintage_key] = row
            vintage_times[vintage_key] = known_from

    latest_by_business_key: dict[tuple[Any, ...], datetime] = {}
    for vintage_key, known_from in vintage_times.items():
        business_key = vintage_key[:-1]
        latest = latest_by_business_key.get(business_key)
        if latest is None or known_from > latest:
            latest_by_business_key[business_key] = known_from

    output = []
    for vintage_key, row in by_vintage.items():
        business_key = vintage_key[:-1]
        output.append(
            {
                **row,
                "is_latest_vintage": (
                    vintage_times[vintage_key] == latest_by_business_key[business_key]
                ),
            }
        )
    return output


def _parse_timestamp(value: Any, *, field: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip().replace("Z", "+00:00")
        if not text:
            raise ValueError(f"{field} is required")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"{field} must be an ISO timestamp, got {value!r}") from exc
    parsed = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _created_timestamp(row: dict[str, Any]) -> datetime:
    return _parse_timestamp(row.get("created_ts"), field="created_ts")


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
    preserve_vintages: bool = False,
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
    if preserve_vintages:
        return deduplicate_preserve_vintage(valid, dedup_keys), failed
    return deduplicate_latest(valid, dedup_keys), failed
