"""
Runner that executes the DQ check catalog and persists results.

Loads the catalog, applies the hard/soft-fail policy, and writes each result to
``project_metadata.data_quality_result``. Hard failures halt downstream tasks; soft failures route
records to ``project_metadata.failed_records``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from src.quality.dq_checks import (
    DQResult,
    check_freshness,
    check_not_null,
    check_referential_integrity,
    check_retention,
    check_unique,
)


class CriticalDQFailure(RuntimeError):
    """Raised after a critical DQ result is persisted."""


@dataclass
class DQRunner:
    metadata_writer: Any

    def run(self, run_id: str | None, checks: Iterable[dict[str, Any]]) -> list[DQResult]:
        results: list[DQResult] = []
        critical_failures: list[DQResult] = []
        for check in checks:
            result = self._execute_check(check)
            results.append(result)
            self.metadata_writer.log_dq_result(
                dataset_name=result.dataset_name,
                check_name=result.check_name,
                status=result.status,
                severity=result.severity,
                metric_value=result.metric_value,
                threshold_value=result.threshold_value,
                error_message=result.error_message,
                run_id=run_id,
            )
            if result.status == "fail" and result.severity == "critical":
                critical_failures.append(result)

        if critical_failures:
            names = ", ".join(result.check_name for result in critical_failures)
            raise CriticalDQFailure(f"critical DQ checks failed: {names}")
        return results

    def _execute_check(self, check: dict[str, Any]) -> DQResult:
        check_type = check["type"]
        if check_type == "not_null":
            return check_not_null(check["rows"], check["dataset_name"], check["field"])
        if check_type == "unique":
            return check_unique(check["rows"], check["dataset_name"], check["fields"])
        if check_type == "referential_integrity":
            return check_referential_integrity(
                check["fact_rows"],
                check["dimension_keys"],
                check["dataset_name"],
                check["field"],
            )
        if check_type == "retention":
            return check_retention(
                check["bronze_count"],
                check["silver_count"],
                check["dataset_name"],
                check.get("threshold", 0.8),
            )
        if check_type == "freshness":
            return check_freshness(
                check["rows"],
                check["dataset_name"],
                check["reference_timestamp"],
                check["sla_minutes"],
                check.get("timestamp_field", "event_timestamp"),
            )
        raise ValueError(f"unknown DQ check type: {check_type}")
