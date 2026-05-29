from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
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
    failures = sum(1 for row in fact_rows if row.get(field) not in dimension_keys)
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
