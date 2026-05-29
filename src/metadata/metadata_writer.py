from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass
class MetadataWriter:
    pipeline_run_log: list[dict[str, Any]] = field(default_factory=list)
    data_quality_result: list[dict[str, Any]] = field(default_factory=list)
    failed_records: list[dict[str, Any]] = field(default_factory=list)
    source_request_log: list[dict[str, Any]] = field(default_factory=list)
    collector_checkpoint: list[dict[str, Any]] = field(default_factory=list)

    def log_run(
        self,
        dag_id: str,
        task_id: str,
        dataset_name: str,
        status: str,
        input_rows: int = 0,
        output_rows: int = 0,
        error_message: str | None = None,
    ) -> str:
        run_id = str(uuid4())
        self.pipeline_run_log.append(
            {
                "run_id": run_id,
                "dag_id": dag_id,
                "task_id": task_id,
                "dataset_name": dataset_name,
                "status": status,
                "started_at": utc_now_iso(),
                "ended_at": utc_now_iso(),
                "input_rows": input_rows,
                "output_rows": output_rows,
                "error_message": error_message,
            }
        )
        return run_id

    def log_dq_result(
        self,
        dataset_name: str,
        check_name: str,
        status: str,
        severity: str,
        metric_value: float | None = None,
        threshold_value: float | None = None,
        error_message: str | None = None,
    ) -> None:
        self.data_quality_result.append(
            {
                "check_id": str(uuid4()),
                "dataset_name": dataset_name,
                "check_name": check_name,
                "status": status,
                "severity": severity,
                "metric_value": metric_value,
                "threshold_value": threshold_value,
                "checked_at": utc_now_iso(),
                "error_message": error_message,
            }
        )

    def log_failed_record(
        self, dataset_name: str, failure_reason: str, raw_payload: dict[str, Any]
    ) -> None:
        self.failed_records.append(
            {
                "record_id": str(uuid4()),
                "dataset_name": dataset_name,
                "failure_reason": failure_reason,
                "raw_payload": raw_payload,
                "created_at": utc_now_iso(),
            }
        )
