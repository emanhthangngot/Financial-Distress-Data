import importlib
from pathlib import Path

from src.catalog.duckdb_runner import run_duckdb_validation
from src.jobs.kafka_to_bronze_job import build_stage1_stream_events
from src.jobs.stage1_spark_lakehouse_job import spark_runtime_config
from src.streaming.kafka_producer import serialize_event


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

    assert len(events) >= 2
    assert {event["evidence_run_id"] for event in events} == {"run-123"}
    assert {event["topic"] for event in events} == {"financial.price_events"}


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
