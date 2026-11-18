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


def check_latest_vintage_unique(
    rows: Iterable[dict[str, Any]],
    dataset_name: str,
    business_key_fields: list[str],
    vintage_flag_field: str = "is_latest_vintage",
) -> DQResult:
    """AC-P2-4: exactly one row per business key has ``vintage_flag_field`` true.

    A restatement fixture that keeps every vintage but forgets the ``WHERE
    is_latest_vintage`` filter downstream fans out silently (plan Risk
    section); this check is the runtime half of the partial-unique-index
    invariant declared in the ERD.
    """
    latest_counts: dict[tuple[Any, ...], int] = {}
    for row in rows:
        if not row.get(vintage_flag_field):
            continue
        key = tuple(row.get(field) for field in business_key_fields)
        latest_counts[key] = latest_counts.get(key, 0) + 1
    violations = sum(1 for count in latest_counts.values() if count != 1)
    return DQResult(
        dataset_name,
        "_".join(business_key_fields) + "_latest_vintage_unique",
        "pass" if violations == 0 else "fail",
        "critical",
        float(violations),
        0.0,
        None if violations == 0 else f"{violations} business keys have != 1 latest vintage",
    )


def check_null_rate_ceiling(
    rows: Iterable[dict[str, Any]],
    dataset_name: str,
    field: str,
    ceiling: float = 0.05,
) -> DQResult:
    """F16: a nullable FK column's NULL rate must stay under ``ceiling``.

    "Zero orphans" on a column that is entirely NULL passes trivially —
    Postgres does not enforce a foreign key on NULL (MATCH SIMPLE). This
    check makes an all-NULL or mostly-NULL column a real, visible failure
    instead of a silently vacuous pass.
    """
    materialized = list(rows)
    total = len(materialized)
    nulls = sum(1 for row in materialized if row.get(field) is None)
    rate = 0.0 if total == 0 else nulls / total
    return DQResult(
        dataset_name,
        f"{field}_null_rate_ceiling",
        "pass" if rate <= ceiling else "fail",
        "critical",
        rate,
        ceiling,
        None if rate <= ceiling else f"{field} null rate {rate:.2%} exceeds ceiling {ceiling:.2%}",
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
