from __future__ import annotations

import importlib
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.orchestration.pipeline_contracts import (
    PipelineValidationError,
    stable_pipeline_run_id,
    validate_feature_snapshot,
    validate_required_counts,
)


@pytest.mark.parametrize(
    ("module_name", "expected_chain"),
    [
        (
            "dags.ingest_source_to_bronze",
            [
                "resolve_run",
                "ingest_batch_to_bronze",
                "ingest_stream_to_bronze",
                "validate_bronze",
                "publish_manifest",
            ],
        ),
        (
            "dags.build_silver_gold",
            [
                "resolve_run",
                "spark_build_silver_gold",
                "validate_silver_gold",
                "publish_manifest",
            ],
        ),
        (
            "dags.build_offline_features",
            [
                "resolve_run",
                "compute_offline_features",
                "validate_point_in_time_features",
                "publish_manifest",
            ],
        ),
    ],
)
def test_rubric_pipeline_modules_expose_explicit_ingest_validate_stages(
    module_name: str, expected_chain: list[str]
):
    module = importlib.import_module(module_name)

    assert module.task_chain() == expected_chain
    assert module.DAG is None


def test_run_id_is_stable_for_dag_and_logical_interval():
    logical_date = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)

    first = stable_pipeline_run_id("build_silver_gold", logical_date)
    second = stable_pipeline_run_id("build_offline_features", logical_date)

    assert first == second
    assert first.startswith("coursework-20260730T120000-")


def test_required_count_gate_blocks_empty_publication():
    with pytest.raises(PipelineValidationError, match="gold_fact_market_price"):
        validate_required_counts(
            {"silver_companies": 10, "gold_fact_market_price": 0},
            ("silver_companies", "gold_fact_market_price"),
        )


def test_feature_gate_rejects_future_data_and_missing_creation_timestamp():
    with pytest.raises(PipelineValidationError, match="future feature"):
        validate_feature_snapshot(
            [
                {
                    "ticker": "AAA",
                    "event_timestamp": "2026-01-02T00:00:00+00:00",
                    "created_ts": "2026-01-02T00:00:01+00:00",
                    "feature_event_timestamp": "2026-01-03T00:00:00+00:00",
                }
            ]
        )

    with pytest.raises(PipelineValidationError, match="created_ts"):
        validate_feature_snapshot(
            [{"ticker": "AAA", "event_timestamp": "2026-01-02T00:00:00+00:00"}]
        )


def test_dp3_stages_outputs_and_returns_only_compact_audit(monkeypatch):
    from src.orchestration import airflow_tasks

    feature = {
        "ticker": "AAA",
        "event_timestamp": "2026-01-02T00:00:00+00:00",
        "created_ts": "2026-01-02T00:00:01+00:00",
        "feature_event_timestamp": "2026-01-01T00:00:00+00:00",
    }
    names = (
        "gold_feat_company_financial_4q",
        "gold_feat_company_market_30d",
        "gold_feat_company_news_30d",
        "gold_feat_company_unified",
    )
    writes = []
    monkeypatch.setattr(airflow_tasks, "_bucket", lambda: "lake")
    monkeypatch.setattr(airflow_tasks, "_minio_client", lambda: object())
    monkeypatch.setattr(airflow_tasks, "_ensure_bucket", lambda *_: None)
    monkeypatch.setattr(
        airflow_tasks,
        "build_evidence_payload",
        lambda _: SimpleNamespace(datasets={name: [feature] for name in names}),
    )
    monkeypatch.setattr(
        airflow_tasks,
        "write_minio_dataset",
        lambda _client, _bucket, key, _rows: writes.append(key),
    )
    task_instance = SimpleNamespace(
        xcom_pull=lambda task_ids: "coursework-20260730T120200-bf92b2cdf0"
    )

    result = airflow_tasks.compute_offline_features(ti=task_instance)

    assert "unified_rows" not in result
    assert result["pit_audit"] == {"feature_rows": 1, "future_rows": 0}
    assert all("/_staging/coursework-20260730T120200-bf92b2cdf0/" in key for key in writes)
