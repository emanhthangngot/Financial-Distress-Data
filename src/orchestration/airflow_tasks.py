"""Real task adapters used by the three rubric Airflow DAGs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.io.minio_publish import promote_staged_prefixes
from src.io.minio_writer import write_minio_dataset
from src.io.paths import DEFAULT_BUCKET
from src.jobs.kafka_to_bronze_job import (
    build_lakehouse_stream_events,
    consume_lakehouse_stream_events_to_bronze,
    produce_lakehouse_stream_events,
)
from src.jobs.lakehouse_evidence_job import (
    _ensure_bucket,
    _minio_client,
    build_evidence_payload,
    current_evidence_run_id,
)
from src.jobs.lakehouse_spark_lakehouse_job import run_lakehouse_spark_lakehouse
from src.orchestration.pipeline_contracts import (
    stable_pipeline_run_id,
    validate_feature_audit,
    validate_feature_snapshot,
    validate_required_counts,
)


def _bucket() -> str:
    import os

    return os.getenv("FINANCIAL_DISTRESS_BUCKET", DEFAULT_BUCKET)


def resolve_run(dag_id: str, **context: Any) -> str:
    """Resolve a stable run ID from the Airflow logical interval."""
    logical_date = context.get("logical_date") or datetime.now(UTC)
    return stable_pipeline_run_id(dag_id, logical_date)


def ingest_batch_to_bronze() -> dict[str, int]:
    """Materialize deterministic source datasets into Bronze MinIO objects."""
    bucket = _bucket()
    payload = build_evidence_payload(bucket)
    client = _minio_client()
    _ensure_bucket(client, bucket)
    datasets = {
        "bronze_companies": payload.datasets["bronze_companies"],
        "bronze_financial_statements": payload.datasets["bronze_financial_statements"],
        "bronze_market_prices": payload.datasets["bronze_market_prices"],
    }
    for name, rows in datasets.items():
        write_minio_dataset(
            client,
            bucket,
            f"{bucket}/bronze/{name.removeprefix('bronze_')}/data.parquet",
            rows,
        )
    return {name: len(rows) for name, rows in datasets.items()}


def ingest_stream_to_bronze() -> dict[str, int | str]:
    """Publish correlated Kafka events and consume them into Bronze storage."""
    run_id = current_evidence_run_id()
    produced = produce_lakehouse_stream_events(run_id)
    batches = consume_lakehouse_stream_events_to_bronze(
        run_id,
        _bucket(),
        len(build_lakehouse_stream_events(run_id)),
    )
    return {"run_id": run_id, "records_produced": produced, "batches_written": len(batches)}


def validate_bronze(**context: Any) -> dict[str, int]:
    """Block DP1 publication when batch or stream ingestion is empty."""
    task_instance = context["ti"]
    counts = dict(task_instance.xcom_pull(task_ids="ingest_batch_to_bronze") or {})
    stream = task_instance.xcom_pull(task_ids="ingest_stream_to_bronze") or {}
    counts["bronze_stream_records"] = int(stream.get("records_produced", 0))
    return validate_required_counts(
        counts,
        (
            "bronze_companies",
            "bronze_financial_statements",
            "bronze_market_prices",
            "bronze_stream_records",
        ),
    )


def spark_build_silver_gold() -> dict[str, int]:
    """Run the verified Spark Bronze-to-Silver/Gold implementation."""
    return run_lakehouse_spark_lakehouse(_bucket())


def validate_silver_gold(**context: Any) -> dict[str, int]:
    """Block DP2 publication when a core Silver or Gold dataset is empty."""
    counts = context["ti"].xcom_pull(task_ids="spark_build_silver_gold") or {}
    return validate_required_counts(
        counts,
        (
            "silver_companies",
            "silver_financial_statements",
            "silver_market_prices",
            "gold_dim_company",
            "gold_fact_financial_statement",
            "gold_fact_market_price",
        ),
    )


def compute_offline_features(**context: Any) -> dict[str, Any]:
    """Compute and stage four offline feature datasets for gated promotion."""
    bucket = _bucket()
    payload = build_evidence_payload(bucket)
    client = _minio_client()
    _ensure_bucket(client, bucket)
    run_id = context["ti"].xcom_pull(task_ids="resolve_run")
    names = (
        "gold_feat_company_financial_4q",
        "gold_feat_company_market_30d",
        "gold_feat_company_news_30d",
        "gold_feat_company_unified",
    )
    for name in names:
        write_minio_dataset(
            client,
            bucket,
            (f"{bucket}/_staging/{run_id}/gold/{name.removeprefix('gold_')}/data.parquet"),
            payload.datasets[name],
        )
    return {
        "run_id": run_id,
        "counts": {name: len(payload.datasets[name]) for name in names},
        "pit_audit": validate_feature_snapshot(payload.datasets["gold_feat_company_unified"]),
    }


def validate_point_in_time_features(**context: Any) -> dict[str, int]:
    """Block DP3 publication on empty tables, missing timestamps, or leakage."""
    result = context["ti"].xcom_pull(task_ids="compute_offline_features") or {}
    validate_required_counts(
        result.get("counts", {}),
        (
            "gold_feat_company_financial_4q",
            "gold_feat_company_market_30d",
            "gold_feat_company_news_30d",
            "gold_feat_company_unified",
        ),
    )
    return validate_feature_audit(result.get("pit_audit", {}))


def publish_manifest(pipeline_id: str, **context: Any) -> dict[str, Any]:
    """Publish the run-correlation summary only after the validation gate passes."""
    task_instance = context["ti"]
    run_id = task_instance.xcom_pull(task_ids="resolve_run")
    if pipeline_id == "build_offline_features":
        promote_staged_prefixes(
            _minio_client(),
            _bucket(),
            run_id,
            [
                "gold/feat_company_financial_4q/",
                "gold/feat_company_market_30d/",
                "gold/feat_company_news_30d/",
                "gold/feat_company_unified/",
            ],
        )
    return {
        "pipeline_id": pipeline_id,
        "run_id": run_id,
        "validated": True,
    }
