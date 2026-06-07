import importlib
import json
import sys
from pathlib import Path

import pytest

from src.catalog.duckdb_runner import run_duckdb_validation
from src.jobs.kafka_to_bronze_job import build_stage1_stream_events
from src.jobs.stage1_spark_lakehouse_job import spark_runtime_config
from src.streaming.kafka_producer import serialize_event


def _write_complete_stage1_audit_artifacts(evidence_dir: Path) -> None:
    (evidence_dir / "stage1_real_airflow_dag_test.txt").write_text(
        "DagRun Finished: state=success",
        encoding="utf-8",
    )
    (evidence_dir / "stage1_real_kafka_offsets.json").write_text(
        json.dumps(
            {
                "financial.price_events": ["financial.price_events:0:1"],
                "financial.news_events": ["financial.news_events:0:1"],
                "financial.alert_events": ["financial.alert_events:0:1"],
            }
        ),
        encoding="utf-8",
    )
    (evidence_dir / "stage1_real_postgres_summary.json").write_text(
        json.dumps(
            {
                "data_quality_result": "gold_fact_market_alert pass",
                "dataset_freshness": "silver_market_prices pass",
                "backfill_request": "completed",
                "source_request_log": "vnstock_fixture success",
                "collector_checkpoint": "stage1_fixture_collectors last_successful_run_id",
            }
        ),
        encoding="utf-8",
    )
    (evidence_dir / "stage1_dq_failure_probe.json").write_text(
        json.dumps(
            {
                "error_message": "critical DQ checks failed: ticker_not_null",
                "expected_outcome": "critical_failure_persisted_before_halt",
                "halted": True,
            }
        ),
        encoding="utf-8",
    )
    (evidence_dir / "stage1_real_duckdb_validation.json").write_text(
        json.dumps(
            [
                {"columns": ["total_financial_statement_rows"], "rows": [[16]]},
                {"columns": ["total_dim_company_rows"], "rows": [[2]]},
                {"columns": ["ticker", "report_period", "cnt"], "rows": []},
                {"columns": ["distress_label", "row_count"], "rows": [[0, 12], [1, 4]]},
                {"columns": ["total_news_sentiment_rows"], "rows": [[2]]},
                {"columns": ["total_market_alert_rows"], "rows": [[1]]},
                {"columns": ["total_financial_feature_rows"], "rows": [[16]]},
                {"columns": ["total_market_feature_rows"], "rows": [[12]]},
                {"columns": ["total_news_feature_rows"], "rows": [[2]]},
                {"columns": ["future_feature_leakage_rows"], "rows": [[0]]},
            ]
        ),
        encoding="utf-8",
    )
    (evidence_dir / "stage1_real_minio_objects.json").write_text(
        json.dumps(
            [
                {"object_name": "bronze/companies/data.parquet"},
                {"object_name": "bronze/financial_statements/data.parquet"},
                {"object_name": "bronze/market_prices_daily/data.parquet"},
                {"object_name": "bronze/kafka/financial.price_events/part.parquet"},
                {"object_name": "bronze/kafka/financial.news_events/part.parquet"},
                {"object_name": "bronze/kafka/financial.alert_events/part.parquet"},
                {"object_name": "silver/companies/part.parquet"},
                {"object_name": "silver/financial_statements/part.parquet"},
                {"object_name": "silver/market_prices_daily/part.parquet"},
                {"object_name": "gold/fact_financial_statement/part.parquet"},
                {"object_name": "gold/fact_market_price/part.parquet"},
                {"object_name": "gold/dim_company/part.parquet"},
                {"object_name": "gold/fact_news_sentiment/part.parquet"},
                {"object_name": "gold/fact_market_alert/part.parquet"},
                {"object_name": "gold/obt_company_quarter_risk/part.parquet"},
                {"object_name": "gold/feat_company_unified/part.parquet"},
                {"object_name": "evidence/stage1/run_id=run/stage1_row_counts.json"},
            ]
        ),
        encoding="utf-8",
    )


def test_duckdb_validation_creates_missing_evidence_directory(tmp_path: Path):
    views_sql = tmp_path / "views.sql"
    validation_sql = tmp_path / "validation.sql"
    evidence_dir = tmp_path / "missing-evidence"
    views_sql.write_text("CREATE OR REPLACE VIEW one AS SELECT 1 AS value;", encoding="utf-8")
    validation_sql.write_text("SELECT * FROM one;", encoding="utf-8")

    outputs = run_duckdb_validation(evidence_dir, views_sql, validation_sql)

    assert outputs[0]["rows"] == [(1,)]
    assert (evidence_dir / "stage1_duckdb_validation.json").exists()


def test_stage1_stream_events_include_run_id_for_broker_filtering():
    events = build_stage1_stream_events("run-123")

    assert len(events) >= 6
    assert {event["evidence_run_id"] for event in events} == {"run-123"}
    assert {event["topic"] for event in events} == {
        "financial.price_events",
        "financial.news_events",
        "financial.alert_events",
    }


def test_kafka_event_serializer_encodes_json_bytes():
    payload = {"topic": "financial.price_events", "ticker": "AAA", "evidence_run_id": "run-123"}

    encoded = serialize_event(payload)

    assert isinstance(encoded, bytes)
    assert b'"evidence_run_id": "run-123"' in encoded


def test_spark_runtime_config_includes_s3a_packages_and_local_minio_endpoint():
    config = spark_runtime_config("http://minio:9000")

    assert "org.apache.hadoop:hadoop-aws" in config["spark.jars.packages"]
    assert config["spark.hadoop.fs.s3a.endpoint"] == "http://minio:9000"
    assert config["spark.hadoop.fs.s3a.path.style.access"] == "true"


def test_real_e2e_dag_exposes_full_runtime_task_chain():
    module = importlib.import_module("dags.stage1_real_e2e_pipeline")

    task_names = module.task_chain()

    assert task_names == [
        "materialize_bronze_batch_objects",
        "produce_fixture_stream_events_to_kafka",
        "consume_kafka_events_to_bronze",
        "run_spark_bronze_to_silver_gold",
        "run_silver_gold_dq_gate",
        "write_project_metadata_rows",
        "run_duckdb_validation_and_publish_evidence",
    ]


def test_real_e2e_dq_task_uses_actual_lakehouse_outputs():
    module = importlib.import_module("dags.stage1_real_e2e_pipeline")

    source_names = module.run_silver_gold_dq_gate.__code__.co_names

    assert "build_actual_dq_checks" in source_names
    assert "build_evidence_payload" not in source_names


def test_stage1_dq_failure_probe_script_uses_intentional_failure_checks():
    module = importlib.import_module("scripts.run_stage1_dq_failure_probe")

    source_names = module.main.__code__.co_names

    assert "build_intentional_dq_failure_checks" in source_names
    assert "CriticalDQFailure" in source_names
    assert "metadata_dsn" in source_names


def test_real_e2e_postgres_summary_exports_operational_metadata_tables():
    module = importlib.import_module("scripts.run_stage1_real_e2e")

    source = module.postgres_summary.__code__.co_consts
    joined = "\n".join(str(item) for item in source)

    assert "project_metadata.dataset_freshness" in joined
    assert "project_metadata.failed_records" in joined
    assert "project_metadata.backfill_request" in joined


def test_stage1_evidence_audit_summary_passes_for_complete_artifacts(tmp_path: Path):
    module = importlib.import_module("scripts.audit_stage1_evidence")
    _write_complete_stage1_audit_artifacts(tmp_path)

    summary = module.audit_evidence(tmp_path)

    assert summary["status"] == "pass"
    assert summary["failed_checks"] == []
    assert summary["checks"]["duckdb_total_dim_company_rows_ok"] is True
    assert summary["duckdb_metrics"]["total_dim_company_rows"] == 2


def test_stage1_evidence_audit_check_mode_fails_when_summary_is_missing(
    tmp_path: Path,
    monkeypatch,
):
    module = importlib.import_module("scripts.audit_stage1_evidence")
    _write_complete_stage1_audit_artifacts(tmp_path)
    monkeypatch.setattr(sys, "argv", ["audit_stage1_evidence.py", str(tmp_path), "--check"])

    with pytest.raises(SystemExit):
        module.main()


def test_stage1_evidence_audit_check_mode_fails_when_summary_is_stale(
    tmp_path: Path,
    monkeypatch,
):
    module = importlib.import_module("scripts.audit_stage1_evidence")
    _write_complete_stage1_audit_artifacts(tmp_path)
    (tmp_path / "stage1_runtime_audit_summary.json").write_text(
        json.dumps({"status": "pass"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["audit_stage1_evidence.py", str(tmp_path), "--check"])

    with pytest.raises(SystemExit):
        module.main()


def test_stage1_evidence_audit_reports_failed_check_names(tmp_path: Path):
    module = importlib.import_module("scripts.audit_stage1_evidence")
    _write_complete_stage1_audit_artifacts(tmp_path)
    minio_objects_path = tmp_path / "stage1_real_minio_objects.json"
    minio_objects = json.loads(minio_objects_path.read_text(encoding="utf-8"))
    minio_objects_path.write_text(
        json.dumps(
            [
                item
                for item in minio_objects
                if not item["object_name"].startswith("gold/fact_market_alert/")
            ]
        ),
        encoding="utf-8",
    )

    summary = module.audit_evidence(tmp_path)

    assert summary["status"] == "fail"
    assert "minio_has_gold_alert_fact" in summary["failed_checks"]
    assert "minio_has_required_medallion_prefixes" in summary["failed_checks"]


def test_stage1_evidence_audit_reports_missing_json_artifact_without_traceback(tmp_path: Path):
    module = importlib.import_module("scripts.audit_stage1_evidence")
    _write_complete_stage1_audit_artifacts(tmp_path)
    (tmp_path / "stage1_real_kafka_offsets.json").unlink()

    summary = module.audit_evidence(tmp_path)

    assert summary["status"] == "fail"
    assert "artifact_stage1_real_kafka_offsets.json_readable" in summary["failed_checks"]
    assert "all_kafka_topics_present" in summary["failed_checks"]


def test_stage1_evidence_audit_reports_malformed_json_artifact_without_traceback(tmp_path: Path):
    module = importlib.import_module("scripts.audit_stage1_evidence")
    _write_complete_stage1_audit_artifacts(tmp_path)
    (tmp_path / "stage1_real_duckdb_validation.json").write_text("{broken json", encoding="utf-8")

    summary = module.audit_evidence(tmp_path)

    assert summary["status"] == "fail"
    assert "artifact_stage1_real_duckdb_validation.json_readable" in summary["failed_checks"]
    assert "duckdb_total_financial_statement_rows_ok" in summary["failed_checks"]
