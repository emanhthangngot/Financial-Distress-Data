"""
platform local evidence pipeline.

The on-demand DAG that exercises the full platform path on the developer laptop:
collectors, Bronze-to-Silver, Silver-to-Gold, DQ, and DuckDB catalog
registration. Drives the rubric row 4 evidence collection.
"""

from __future__ import annotations

import os
from pathlib import Path

from dags.utils.dag_utils import DEFAULT_ARGS, airflow_imports
from src.catalog.duckdb_runner import run_duckdb_validation
from src.jobs.lakehouse_evidence_job import (
    DEFAULT_BUCKET,
    DEFAULT_EVIDENCE_DIR,
    build_evidence_payload,
    current_evidence_run_id,
    write_minio_evidence_artifacts,
    write_minio_outputs,
    write_postgres_metadata,
)

DAG, PythonOperator = airflow_imports()


def _bucket() -> str:
    return os.getenv("FINANCIAL_DISTRESS_BUCKET", DEFAULT_BUCKET)


def _evidence_dir() -> Path:
    return Path(os.getenv("LAKEHOUSE_EVIDENCE_DIR", str(DEFAULT_EVIDENCE_DIR)))


def build_lakehouse_payload() -> dict[str, int]:
    payload = build_evidence_payload(_bucket())
    return payload.row_counts


def write_lakehouse_minio_outputs() -> dict[str, int]:
    payload = build_evidence_payload(_bucket())
    write_minio_outputs(payload, _bucket())
    return payload.row_counts


def write_lakehouse_postgres_metadata() -> str:
    payload = build_evidence_payload(_bucket())
    return write_postgres_metadata(payload)


def run_lakehouse_duckdb_validation() -> str:
    payload = build_evidence_payload(_bucket())
    duckdb_validation = run_duckdb_validation(_evidence_dir())
    return write_minio_evidence_artifacts(
        payload,
        _bucket(),
        run_id=current_evidence_run_id(),
        duckdb_validation=duckdb_validation,
    )


def materialize_lakehouse_local_evidence() -> dict[str, int]:
    payload = build_evidence_payload(_bucket())
    write_minio_outputs(payload, _bucket())
    write_postgres_metadata(payload)
    duckdb_validation = run_duckdb_validation(_evidence_dir())
    write_minio_evidence_artifacts(payload, _bucket(), duckdb_validation=duckdb_validation)
    return payload.row_counts


if DAG is not None:
    with DAG(
        dag_id="lakehouse_local_evidence_pipeline",
        default_args=DEFAULT_ARGS,
        schedule=None,
        catchup=False,
        tags=["financial-distress", "stage-1", "evidence"],
    ) as dag:
        build_payload = PythonOperator(
            task_id="build_fixture_lakehouse_payload",
            python_callable=build_lakehouse_payload,
        )
        write_minio = PythonOperator(
            task_id="write_minio_bronze_silver_gold_objects",
            python_callable=write_lakehouse_minio_outputs,
        )
        write_metadata = PythonOperator(
            task_id="write_project_metadata_rows",
            python_callable=write_lakehouse_postgres_metadata,
        )
        validate_duckdb = PythonOperator(
            task_id="run_duckdb_validation_and_publish_evidence_artifacts",
            python_callable=run_lakehouse_duckdb_validation,
        )

        build_payload >> write_minio >> write_metadata >> validate_duckdb
