"""
Stage 1 real end-to-end pipeline.

The DAG that drives the Stage 1 real end-to-end run used for rubric evidence
collection. It schedules collectors, Bronze/Silver/Gold transforms, DQ, and
DuckDB view registration as a single Airflow graph.
"""

from __future__ import annotations

import os
from pathlib import Path

from dags.utils.dag_utils import DEFAULT_ARGS, airflow_imports
from src.catalog.duckdb_runner import run_duckdb_validation
from src.io.minio_writer import write_minio_dataset
from src.io.paths import DEFAULT_BUCKET
from src.jobs.kafka_to_bronze_job import (
    build_lakehouse_stream_events,
    consume_lakehouse_stream_events_to_bronze,
    produce_lakehouse_stream_events,
)
from src.jobs.lakehouse_dq_job import build_actual_dq_checks
from src.jobs.lakehouse_evidence_job import (
    build_evidence_payload,
    current_evidence_run_id,
    write_minio_evidence_artifacts,
    write_postgres_metadata,
)
from src.jobs.lakehouse_spark_lakehouse_job import run_lakehouse_spark_lakehouse
from src.quality.dq_runner import DQRunner

DAG, PythonOperator = airflow_imports()


def _bucket() -> str:
    return os.getenv("FINANCIAL_DISTRESS_BUCKET", DEFAULT_BUCKET)


def _evidence_dir() -> Path:
    return Path(os.getenv("LAKEHOUSE_EVIDENCE_DIR", "/tmp/lakehouse-evidence"))


def task_chain() -> list[str]:
    return [
        "materialize_bronze_batch_objects",
        "produce_fixture_stream_events_to_kafka",
        "consume_kafka_events_to_bronze",
        "run_spark_bronze_to_silver_gold",
        "run_silver_gold_dq_gate",
        "write_project_metadata_rows",
        "run_duckdb_validation_and_publish_evidence",
    ]


def materialize_bronze_batch_objects() -> dict[str, int]:
    from src.jobs.lakehouse_evidence_job import _ensure_bucket, _minio_client

    bucket = _bucket()
    payload = build_evidence_payload(bucket)
    client = _minio_client()
    _ensure_bucket(client, bucket)
    bronze_datasets = {
        "bronze/companies/data.parquet": payload.datasets["bronze_companies"],
        "bronze/financial_statements/data.parquet": payload.datasets["bronze_financial_statements"],
        "bronze/market_prices_daily/data.parquet": payload.datasets["bronze_market_prices"],
    }
    for object_key, rows in bronze_datasets.items():
        write_minio_dataset(client, bucket, f"{bucket}/{object_key}", rows)
    return {name: len(rows) for name, rows in bronze_datasets.items()}


def produce_fixture_stream_events_to_kafka() -> dict[str, int | str]:
    run_id = current_evidence_run_id()
    count = produce_lakehouse_stream_events(run_id)
    return {"evidence_run_id": run_id, "records_produced": count}


def consume_kafka_events_to_bronze() -> list[dict]:
    run_id = current_evidence_run_id()
    expected_records = len(build_lakehouse_stream_events(run_id))
    return consume_lakehouse_stream_events_to_bronze(run_id, _bucket(), expected_records)


def run_spark_bronze_to_silver_gold() -> dict[str, int]:
    return run_lakehouse_spark_lakehouse(_bucket(), evidence_run_id=current_evidence_run_id())


def run_silver_gold_dq_gate() -> list[dict]:
    from src.metadata.metadata_writer import PostgresMetadataWriter, psycopg_connection_factory

    writer = PostgresMetadataWriter(
        psycopg_connection_factory(os.getenv("PROJECT_METADATA_DSN", ""))
    )
    runner = DQRunner(writer)
    run_id = current_evidence_run_id()
    results = runner.run(run_id, build_actual_dq_checks(_bucket()))
    return [result.__dict__ for result in results]


def write_project_metadata_rows() -> str:
    return write_postgres_metadata(
        build_evidence_payload(_bucket()),
        dag_id="lakehouse_real_e2e_pipeline",
        task_id="write_project_metadata_rows",
        dataset_name="lakehouse_real_e2e",
    )


def run_duckdb_validation_and_publish_evidence() -> str:
    payload = build_evidence_payload(_bucket())
    validation = run_duckdb_validation(_evidence_dir())
    return write_minio_evidence_artifacts(
        payload,
        _bucket(),
        run_id=current_evidence_run_id(),
        duckdb_validation=validation,
    )


if DAG is not None:
    with DAG(
        dag_id="lakehouse_real_e2e_pipeline",
        default_args=DEFAULT_ARGS,
        schedule=None,
        catchup=False,
        tags=["financial-distress", "stage-1", "real-e2e"],
    ) as dag:
        names = task_chain()
        tasks = {
            name: PythonOperator(task_id=name, python_callable=globals()[name]) for name in names
        }
        for left, right in zip(names[:-1], names[1:], strict=True):
            tasks[left] >> tasks[right]
