from pathlib import Path

import pytest

from src.catalog.duckdb_runner import create_views_sql
from src.io.paths import dataset_object_key
from src.jobs.stage1_dq_job import build_intentional_dq_failure_checks
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
    assert payload.row_counts["gold_fact_market_alert"] == 1
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


def test_duckdb_create_views_sql_injects_minio_credentials_from_env(tmp_path: Path, monkeypatch):
    sql_path = tmp_path / "views.sql"
    sql_path.write_text(
        "SET s3_endpoint='localhost:9000';\n"
        "-- env chain (process env, .env, ~/.aws/credentials).",
        encoding="utf-8",
    )
    monkeypatch.setenv("MINIO_ROOT_USER", "minio-user")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "minio-secret")

    sql = create_views_sql(sql_path)

    assert "SET s3_access_key_id='minio-user';" in sql
    assert "SET s3_secret_access_key='minio-secret';" in sql


def test_duckdb_create_views_sql_injects_minio_credentials_from_dotenv(tmp_path: Path, monkeypatch):
    sql_path = tmp_path / "views.sql"
    sql_path.write_text(
        "SET s3_endpoint='localhost:9000';\n"
        "-- env chain (process env, .env, ~/.aws/credentials).",
        encoding="utf-8",
    )
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "MINIO_ROOT_USER=dotenv-user\nMINIO_ROOT_PASSWORD=dotenv-secret\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MINIO_ROOT_USER", raising=False)
    monkeypatch.delenv("MINIO_ROOT_PASSWORD", raising=False)

    sql = create_views_sql(sql_path)

    assert "SET s3_access_key_id='dotenv-user';" in sql
    assert "SET s3_secret_access_key='dotenv-secret';" in sql


def test_duckdb_create_views_sql_registers_all_claimed_gold_tables():
    sql = create_views_sql()

    for view_name in [
        "gold_dim_date",
        "gold_fact_market_alert",
        "gold_fact_news_sentiment",
        "gold_feat_company_financial_4q",
        "gold_feat_company_market_30d",
        "gold_feat_company_news_30d",
    ]:
        assert f"CREATE OR REPLACE VIEW {view_name}" in sql


def test_duckdb_validation_sql_checks_point_in_time_feature_leakage():
    sql = Path("sql/duckdb_validation_queries.sql").read_text(encoding="utf-8")

    assert "future_feature_leakage_rows" in sql
    assert "feature_event_timestamp" in sql


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


def test_stage1_intentional_dq_failure_probe_persists_before_halting():
    writer = MetadataWriter()
    runner = DQRunner(writer)

    with pytest.raises(CriticalDQFailure, match="ticker_not_null"):
        runner.run("dq-failure-probe", build_intentional_dq_failure_checks())

    assert writer.data_quality_result == [
        {
            **writer.data_quality_result[0],
            "run_id": "dq-failure-probe",
            "dataset_name": "dq_failure_probe_companies",
            "check_name": "ticker_not_null",
            "status": "fail",
            "severity": "critical",
            "metric_value": 1.0,
            "threshold_value": 0.0,
            "error_message": "1 rows have null ticker",
        }
    ]
