"""
Catalog of data quality checks for the financial-distress pipeline.

Each check is a small function that inspects a DataFrame and returns a ``DqResult`` with status
(PASS / WARN / FAIL) and a reason. Checks are registered by the runner, never called directly from
jobs.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class DQResult:
    dataset_name: str
    check_name: str
    status: str
    severity: str
    metric_value: float | None = None
    threshold_value: float | None = None
    error_message: str | None = None


def check_not_null(rows: Iterable[dict[str, Any]], dataset_name: str, field: str) -> DQResult:
    failures = sum(1 for row in rows if row.get(field) is None)
    return DQResult(
        dataset_name,
        f"{field}_not_null",
        "pass" if failures == 0 else "fail",
        "critical",
        float(failures),
        0.0,
        None if failures == 0 else f"{failures} rows have null {field}",
    )


def check_unique(rows: Iterable[dict[str, Any]], dataset_name: str, fields: list[str]) -> DQResult:
    seen = set()
    duplicates = 0
    for row in rows:
        key = tuple(row.get(field) for field in fields)
        if key in seen:
            duplicates += 1
        seen.add(key)
    return DQResult(
        dataset_name,
        "_".join(fields) + "_unique",
        "pass" if duplicates == 0 else "fail",
        "critical",
        float(duplicates),
        0.0,
        None if duplicates == 0 else f"{duplicates} duplicate keys",
    )


def check_referential_integrity(
    fact_rows: Iterable[dict[str, Any]],
    dimension_keys: set[Any],
    dataset_name: str,
    field: str,
) -> DQResult:
    failures = sum(
        1 for row in fact_rows if row.get(field) is None or row.get(field) not in dimension_keys
    )
    return DQResult(
        dataset_name,
        f"{field}_exists",
        "pass" if failures == 0 else "fail",
        "critical",
        float(failures),
        0.0,
        None if failures == 0 else f"{failures} rows fail {field} referential integrity",
    )


def check_retention(
    bronze_count: int, silver_count: int, dataset_name: str, threshold: float = 0.8
) -> DQResult:
    ratio = 0.0 if bronze_count == 0 else silver_count / bronze_count
    return DQResult(
        dataset_name,
        "silver_retention_at_least_80_percent",
        "pass" if ratio >= threshold else "warning",
        "warning",
        ratio,
        threshold,
        None if ratio >= threshold else "Silver retained fewer records than expected",
    )


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def check_freshness(
    rows: Iterable[dict[str, Any]],
    dataset_name: str,
    reference_timestamp: str | datetime,
    sla_minutes: float,
    timestamp_field: str = "event_timestamp",
) -> DQResult:
    reference = _parse_timestamp(reference_timestamp)
    if reference is None:
        raise ValueError("reference_timestamp must be an ISO timestamp or datetime")

    timestamps = [
        timestamp
        for row in rows
        if (timestamp := _parse_timestamp(row.get(timestamp_field))) is not None
    ]
    if not timestamps:
        return DQResult(
            dataset_name,
            f"{timestamp_field}_freshness",
            "warning",
            "warning",
            None,
            float(sla_minutes),
            f"No parseable {timestamp_field} values found",
        )

    latest = max(timestamps)
    lag_minutes = (reference - latest).total_seconds() / 60
    if lag_minutes < 0:
        return DQResult(
            dataset_name,
            f"{timestamp_field}_freshness",
            "fail",
            "critical",
            float(lag_minutes),
            0.0,
            "Latest event timestamp is in the future",
        )
    return DQResult(
        dataset_name,
        f"{timestamp_field}_freshness",
        "pass" if lag_minutes <= sla_minutes else "warning",
        "warning",
        float(lag_minutes),
        float(sla_minutes),
        None if lag_minutes <= sla_minutes else "Latest event timestamp exceeds freshness SLA",
    )
