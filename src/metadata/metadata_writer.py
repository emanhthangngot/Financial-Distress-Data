"""
PostgreSQL writer for ``ops``.

Centralized helpers to insert run records, DQ results, and failed-record rows. Every job must use
this writer so metadata stays consistent.
"""

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
    dataset_freshness: list[dict[str, Any]] = field(default_factory=list)
    backfill_request: list[dict[str, Any]] = field(default_factory=list)
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

    def log_failed_records(
        self,
        dataset_name: str,
        records: list[dict[str, Any]],
        run_id: str | None = None,
    ) -> None:
        """Persist quarantined Silver records with their source run linkage."""
        for record in records:
            self.log_failed_record(
                dataset_name,
                str(record["failure_reason"]),
                dict(record["raw_payload"]),
                run_id=run_id,
            )

    def update_dataset_freshness(
        self,
        dataset_name: str,
        latest_event_timestamp: str,
        latest_ingest_ts: str | None,
        freshness_lag_minutes: float,
        sla_minutes: float,
        status: str,
    ) -> None:
        self.dataset_freshness.append(
            {
                "dataset_name": dataset_name,
                "latest_event_timestamp": latest_event_timestamp,
                "latest_ingest_ts": latest_ingest_ts,
                "freshness_lag_minutes": freshness_lag_minutes,
                "sla_minutes": sla_minutes,
                "status": status,
                "checked_at": utc_now_iso(),
            }
        )

    def log_backfill_request(
        self,
        dataset_name: str,
        start_date: str,
        end_date: str,
        status: str,
        requested_by: str,
        run_id: str | None = None,
    ) -> str:
        backfill_id = run_id or str(uuid4())
        self.backfill_request.append(
            {
                "backfill_id": backfill_id,
                "dataset_name": dataset_name,
                "start_date": start_date,
                "end_date": end_date,
                "status": status,
                "requested_by": requested_by,
                "created_at": utc_now_iso(),
            }
        )
        return backfill_id

    def log_source_request(
        self,
        run_id: str | None,
        source_system: str,
        source_endpoint: str | None,
        ticker: str | None,
        report_period: str | None,
        request_status: str,
        http_status_code: int | None = None,
        retry_count: int = 0,
        raw_payload_hash: str | None = None,
        error_message: str | None = None,
    ) -> str:
        request_id = str(uuid4())
        self.source_request_log.append(
            {
                "request_id": request_id,
                "run_id": run_id,
                "source_system": source_system,
                "source_endpoint": source_endpoint,
                "ticker": ticker,
                "report_period": report_period,
                "request_status": request_status,
                "http_status_code": http_status_code,
                "retry_count": retry_count,
                "raw_payload_hash": raw_payload_hash,
                "error_message": error_message,
                "requested_at": utc_now_iso(),
            }
        )
        return request_id

    def upsert_collector_checkpoint(
        self,
        collector_name: str,
        source_system: str,
        checkpoint_key: str,
        checkpoint_value: str | None,
    ) -> None:
        self.collector_checkpoint = [
            row
            for row in self.collector_checkpoint
            if not (
                row["collector_name"] == collector_name
                and row["source_system"] == source_system
                and row["checkpoint_key"] == checkpoint_key
            )
        ]
        self.collector_checkpoint.append(
            {
                "collector_name": collector_name,
                "source_system": source_system,
                "checkpoint_key": checkpoint_key,
                "checkpoint_value": checkpoint_value,
                "updated_at": utc_now_iso(),
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
            INSERT INTO ops.pipeline_run_log (
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

    def flush_pipeline_run_logs(self, rows: list[dict[str, Any]]) -> None:
        """Persist a batch of pipeline_run_log rows in a single transaction.

        Builds one multi-VALUES INSERT and commits once. Callers batch the rows
        (e.g. one entry per task in a DAG run) to amortize commit overhead.
        """
        if not rows:
            return

        template = (
            "INSERT INTO ops.pipeline_run_log ("
            "run_id, dag_id, task_id, dataset_name, status, started_at, ended_at, "
            "input_rows, output_rows, error_message) VALUES %s"
        )
        placeholders = "(" + ", ".join(["%s"] * 10) + ")"
        values_sql = ", ".join([placeholders] * len(rows))
        sql = template.replace("VALUES %s", f"VALUES {values_sql}")

        params: list[tuple[Any, ...]] = []
        for row in rows:
            params.append(
                (
                    row["run_id"],
                    row["dag_id"],
                    row["task_id"],
                    row["dataset_name"],
                    row["status"],
                    row["started_at"],
                    row["ended_at"],
                    row["input_rows"],
                    row["output_rows"],
                    row["error_message"],
                )
            )

        connection = self.connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
            connection.commit()
        except Exception:
            connection.rollback()
            raise

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
            INSERT INTO ops.data_quality_result (
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
            INSERT INTO ops.failed_records (
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

    def log_failed_records(
        self,
        dataset_name: str,
        records: list[dict[str, Any]],
        run_id: str | None = None,
    ) -> None:
        """Persist a collection of quarantined records through the PostgreSQL writer."""
        for record in records:
            self.log_failed_record(
                dataset_name,
                str(record["failure_reason"]),
                dict(record["raw_payload"]),
                run_id=run_id,
            )

    def update_dataset_freshness(
        self,
        dataset_name: str,
        latest_event_timestamp: str,
        latest_ingest_ts: str | None,
        freshness_lag_minutes: float,
        sla_minutes: float,
        status: str,
    ) -> None:
        self._execute(
            """
            INSERT INTO ops.dataset_freshness (
                dataset_name, latest_event_timestamp, latest_ingest_ts,
                freshness_lag_minutes, sla_minutes, status, checked_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (dataset_name) DO UPDATE SET
                latest_event_timestamp = EXCLUDED.latest_event_timestamp,
                latest_ingest_ts = EXCLUDED.latest_ingest_ts,
                freshness_lag_minutes = EXCLUDED.freshness_lag_minutes,
                sla_minutes = EXCLUDED.sla_minutes,
                status = EXCLUDED.status,
                checked_at = EXCLUDED.checked_at
            """,
            (
                dataset_name,
                latest_event_timestamp,
                latest_ingest_ts,
                freshness_lag_minutes,
                sla_minutes,
                status,
                utc_now_iso(),
            ),
        )

    def log_backfill_request(
        self,
        dataset_name: str,
        start_date: str,
        end_date: str,
        status: str,
        requested_by: str,
        run_id: str | None = None,
    ) -> str:
        backfill_id = run_id or str(uuid4())
        self._execute(
            """
            INSERT INTO ops.backfill_request (
                backfill_id, dataset_name, start_date, end_date, status, requested_by, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (backfill_id) DO UPDATE SET
                dataset_name = EXCLUDED.dataset_name,
                start_date = EXCLUDED.start_date,
                end_date = EXCLUDED.end_date,
                status = EXCLUDED.status,
                requested_by = EXCLUDED.requested_by
            """,
            (
                backfill_id,
                dataset_name,
                start_date,
                end_date,
                status,
                requested_by,
                utc_now_iso(),
            ),
        )
        return backfill_id

    def log_source_request(
        self,
        run_id: str | None,
        source_system: str,
        source_endpoint: str | None,
        ticker: str | None,
        report_period: str | None,
        request_status: str,
        http_status_code: int | None = None,
        retry_count: int = 0,
        raw_payload_hash: str | None = None,
        error_message: str | None = None,
    ) -> str:
        request_id = str(uuid4())
        self._execute(
            """
            INSERT INTO ops.source_request_log (
                request_id, run_id, source_system, source_endpoint, ticker, report_period,
                request_status, http_status_code, retry_count, raw_payload_hash,
                error_message, requested_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                request_id,
                run_id,
                source_system,
                source_endpoint,
                ticker,
                report_period,
                request_status,
                http_status_code,
                retry_count,
                raw_payload_hash,
                error_message,
                utc_now_iso(),
            ),
        )
        return request_id

    def upsert_collector_checkpoint(
        self,
        collector_name: str,
        source_system: str,
        checkpoint_key: str,
        checkpoint_value: str | None,
    ) -> None:
        self._execute(
            """
            INSERT INTO ops.collector_checkpoint (
                collector_name, source_system, checkpoint_key, checkpoint_value, updated_at
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (collector_name, source_system, checkpoint_key) DO UPDATE SET
                checkpoint_value = EXCLUDED.checkpoint_value,
                updated_at = EXCLUDED.updated_at
            """,
            (
                collector_name,
                source_system,
                checkpoint_key,
                checkpoint_value,
                utc_now_iso(),
            ),
        )
