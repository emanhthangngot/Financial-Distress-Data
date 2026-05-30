from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class DbConnection(Protocol):
    def cursor(self) -> Any: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


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
        run_id: str | None = None,
    ) -> None:
        self.data_quality_result.append(
            {
                "check_id": str(uuid4()),
                "run_id": run_id,
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
        self,
        dataset_name: str,
        failure_reason: str,
        raw_payload: dict[str, Any],
        run_id: str | None = None,
    ) -> None:
        self.failed_records.append(
            {
                "record_id": str(uuid4()),
                "dataset_name": dataset_name,
                "run_id": run_id,
                "failure_reason": failure_reason,
                "raw_payload": raw_payload,
                "created_at": utc_now_iso(),
            }
        )


def psycopg_connection_factory(dsn: str) -> Callable[[], DbConnection]:
    def connect() -> DbConnection:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL metadata persistence requires psycopg. "
                "Install the runtime extra or requirements before running local evidence jobs."
            ) from exc

        return psycopg.connect(dsn)

    return connect


@dataclass
class PostgresMetadataWriter:
    connection_factory: Callable[[], DbConnection]

    def _execute(self, sql: str, params: tuple[Any, ...]) -> None:
        connection = self.connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
            connection.commit()
        except Exception:
            connection.rollback()
            raise

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
        now = utc_now_iso()
        self._execute(
            """
            INSERT INTO project_metadata.pipeline_run_log (
                run_id, dag_id, task_id, dataset_name, status, started_at, ended_at,
                input_rows, output_rows, error_message
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                run_id,
                dag_id,
                task_id,
                dataset_name,
                status,
                now,
                now,
                input_rows,
                output_rows,
                error_message,
            ),
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
        run_id: str | None = None,
    ) -> None:
        self._execute(
            """
            INSERT INTO project_metadata.data_quality_result (
                check_id, run_id, dataset_name, check_name, status, severity,
                metric_value, threshold_value, checked_at, error_message
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(uuid4()),
                run_id,
                dataset_name,
                check_name,
                status,
                severity,
                metric_value,
                threshold_value,
                utc_now_iso(),
                error_message,
            ),
        )

    def log_failed_record(
        self,
        dataset_name: str,
        failure_reason: str,
        raw_payload: dict[str, Any],
        run_id: str | None = None,
    ) -> None:
        self._execute(
            """
            INSERT INTO project_metadata.failed_records (
                record_id, dataset_name, run_id, failure_reason, raw_payload, created_at
            )
            VALUES (%s, %s, %s, %s, %s::jsonb, %s)
            """,
            (
                str(uuid4()),
                dataset_name,
                run_id,
                failure_reason,
                json.dumps(raw_payload, sort_keys=True),
                utc_now_iso(),
            ),
        )
