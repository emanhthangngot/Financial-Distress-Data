from pathlib import Path

import pytest

from src.catalog.duckdb_runner import create_views_sql
from src.io.paths import dataset_object_key
from src.jobs.stage1_evidence_job import (
    DEFAULT_BUCKET,
    build_evidence_artifacts,
    build_evidence_payload,
    evidence_prefix,
    write_evidence_files,
)
from src.metadata.metadata_writer import MetadataWriter
from src.quality.dq_runner import CriticalDQFailure, DQRunner


def test_dataset_object_key_uses_medallion_prefixes():
    assert (
        dataset_object_key("financial-distress-lake", "gold", "fact_market_price")
        == "financial-distress-lake/gold/fact_market_price/data.parquet"
    )


def test_stage1_evidence_payload_keeps_existing_deterministic_counts():
    payload = build_evidence_payload()

    assert DEFAULT_BUCKET == "financial-distress-lake"
    assert payload.row_counts["bronze_companies"] == 2
    assert payload.row_counts["silver_companies"] == 2
    assert payload.row_counts["gold_fact_financial_statement"] == 16
    assert payload.row_counts["gold_fact_market_price"] == 12
    assert payload.row_counts["gold_obt_company_quarter_risk"] == 16
    assert payload.row_counts["gold_feat_company_unified"] == 16
    assert all(path.startswith("financial-distress-lake/") for path in payload.object_keys)


def test_write_evidence_files_exports_runtime_manifest_inputs(tmp_path: Path):
    payload = build_evidence_payload()

    write_evidence_files(payload, tmp_path)

    assert (tmp_path / "stage1_row_counts.json").exists()
    assert (tmp_path / "stage1_minio_objects.txt").exists()
    assert (tmp_path / "stage1_stream_batches.json").exists()


def test_duckdb_create_views_sql_can_use_container_minio_endpoint(tmp_path: Path, monkeypatch):
    sql_path = tmp_path / "views.sql"
    sql_path.write_text("SET s3_endpoint='localhost:9000';", encoding="utf-8")
    monkeypatch.setenv("MINIO_ENDPOINT", "http://minio:9000")

    assert create_views_sql(sql_path) == "SET s3_endpoint='minio:9000';"


def test_evidence_prefix_is_run_scoped_and_sanitized():
    assert (
        evidence_prefix("manual__2026-06-06T01:00:00+00:00")
        == "evidence/stage1/run_id=manual__2026-06-06T01_00_00_00_00"
    )


def test_build_evidence_artifacts_includes_duckdb_validation_when_available():
    payload = build_evidence_payload()
    artifacts = build_evidence_artifacts(
        payload,
        duckdb_validation=[{"query": "select 1", "columns": ["one"], "rows": [(1,)]}],
    )

    assert "stage1_row_counts.json" in artifacts
    assert "stage1_minio_objects.txt" in artifacts
    assert "stage1_stream_batches.json" in artifacts
    assert "stage1_duckdb_validation.json" in artifacts
    assert '"gold_fact_financial_statement": 16' in artifacts["stage1_row_counts.json"]


def test_dq_runner_logs_warning_and_continues():
    writer = MetadataWriter()
    runner = DQRunner(writer)

    results = runner.run(
        run_id="run-1",
        checks=[
            {
                "type": "freshness",
                "dataset_name": "market_prices_daily",
                "rows": [{"event_timestamp": "2026-01-01T00:00:00+00:00"}],
                "reference_timestamp": "2026-01-01T02:30:00+00:00",
                "sla_minutes": 60,
            }
        ],
    )

    assert results[0].status == "warning"
    assert writer.data_quality_result[0]["status"] == "warning"


def test_dq_runner_logs_critical_failure_and_halts():
    writer = MetadataWriter()
    runner = DQRunner(writer)

    with pytest.raises(CriticalDQFailure):
        runner.run(
            run_id="run-1",
            checks=[
                {
                    "type": "not_null",
                    "dataset_name": "companies",
                    "rows": [{"ticker": None}],
                    "field": "ticker",
                }
            ],
        )

    assert writer.data_quality_result[0]["status"] == "fail"
    assert writer.data_quality_result[0]["severity"] == "critical"
