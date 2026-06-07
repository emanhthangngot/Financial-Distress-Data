import json

from dags._stage1_dag_utils import metadata_writer_from_env
from src.metadata.metadata_writer import PostgresMetadataWriter
from src.streaming.events import StreamEvent
from src.streaming.kafka_to_bronze_consumer import (
    MicroBatchConsumer,
    consume_json_messages,
)
from src.transforms.spark_session import configure_spark_builder


class FakeCursor:
    def __init__(self):
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class FakeBuilder:
    def __init__(self):
        self.configs = {}

    def appName(self, value):
        self.configs["appName"] = value
        return self

    def master(self, value):
        self.configs["master"] = value
        return self

    def config(self, key, value):
        self.configs[key] = value
        return self


class FakeMessage:
    def __init__(self, value):
        self.value = value


class FakeKafkaConsumer:
    def __init__(self, messages):
        self.messages = list(messages)
        self.closed = False

    def __iter__(self):
        return iter(self.messages)

    def close(self):
        self.closed = True


def test_postgres_metadata_writer_executes_project_metadata_inserts():
    connection = FakeConnection()
    writer = PostgresMetadataWriter(lambda: connection)

    run_id = writer.log_run("dag", "task", "companies", "success", input_rows=1, output_rows=1)
    writer.log_dq_result("companies", "ticker_not_null", "pass", "critical", run_id=run_id)
    writer.log_failed_record("companies", "bad row", {"ticker": None}, run_id=run_id)
    writer.log_backfill_request(
        "financial_statements",
        "2024-01-01",
        "2025-12-31",
        "completed",
        "stage1_e2e",
        run_id=run_id,
    )
    writer.log_source_request(
        run_id=run_id,
        source_system="vnstock_fixture",
        source_endpoint="fixture://companies",
        ticker="AAA",
        report_period=None,
        request_status="success",
        http_status_code=None,
        retry_count=0,
        raw_payload_hash="hash-1",
        error_message=None,
    )
    writer.upsert_collector_checkpoint(
        collector_name="company_list_collector",
        source_system="vnstock_fixture",
        checkpoint_key="last_successful_run_id",
        checkpoint_value=run_id,
    )
    writer.update_dataset_freshness(
        "companies",
        latest_event_timestamp="2026-01-01T00:00:00+00:00",
        latest_ingest_ts="2026-01-01T00:05:00+00:00",
        freshness_lag_minutes=5,
        sla_minutes=60,
        status="pass",
    )

    executed_sql = "\n".join(sql for sql, _params in connection.cursor_instance.executed)
    assert "project_metadata.pipeline_run_log" in executed_sql
    assert "project_metadata.data_quality_result" in executed_sql
    assert "project_metadata.failed_records" in executed_sql
    assert "project_metadata.backfill_request" in executed_sql
    assert "project_metadata.source_request_log" in executed_sql
    assert "project_metadata.collector_checkpoint" in executed_sql
    assert "project_metadata.dataset_freshness" in executed_sql
    assert connection.commits == 7


def test_configure_spark_builder_sets_minio_s3a_and_dynamic_overwrite():
    builder = configure_spark_builder(
        FakeBuilder(),
        {
            "app_name": "financial-distress-stage-1",
            "master": "local[*]",
            "minio": {
                "endpoint": "http://minio:9000",
                "access_key": "minioadmin",
                "secret_key": "minioadmin",
                "path_style_access": True,
                "ssl_enabled": False,
            },
        },
    )

    assert builder.configs["appName"] == "financial-distress-stage-1"
    assert builder.configs["spark.hadoop.fs.s3a.endpoint"] == "http://minio:9000"
    assert builder.configs["spark.hadoop.fs.s3a.path.style.access"] == "true"
    assert builder.configs["spark.hadoop.fs.s3a.connection.ssl.enabled"] == "false"
    assert builder.configs["spark.sql.sources.partitionOverwriteMode"] == "dynamic"


def test_news_event_factory_and_bronze_path_include_batch_id():
    event = StreamEvent.news_sentiment(
        "AAA",
        "2026-01-01T09:00:00+00:00",
        "2026-01-01T09:00:01+00:00",
        sentiment_score=-0.4,
        risk_keyword_flag=True,
        severity_score=0.8,
    )
    consumer = MicroBatchConsumer(flush_record_count=1)
    batch = consumer.add_event(event.as_record())[0]

    assert event.topic == "financial.news_events"
    assert event.as_record()["risk_keyword_flag"] is True
    assert f"batch_id={batch['batch_id']}" in batch["bronze_path"]


def test_consume_json_messages_feeds_existing_microbatch_contract():
    payload = StreamEvent.price_update(
        "AAA", "2026-01-01T09:00:00+00:00", "2026-01-01T09:00:01+00:00", 10.0, 100
    ).as_record()
    kafka_consumer = FakeKafkaConsumer([FakeMessage(json.dumps(payload).encode("utf-8"))])
    microbatch = MicroBatchConsumer(flush_record_count=1)

    batches = consume_json_messages(kafka_consumer, microbatch, max_records=1)

    assert batches[0]["record_count"] == 1
    assert kafka_consumer.closed is True


def test_microbatch_splits_mixed_hour_records_into_separate_bronze_partitions():
    first = StreamEvent.price_update(
        "AAA", "2026-01-01T09:59:59+00:00", "2026-01-01T10:00:00+00:00", 10.0, 100
    ).as_record()
    second = StreamEvent.price_update(
        "AAA", "2026-01-01T10:00:01+00:00", "2026-01-01T10:00:02+00:00", 10.1, 120
    ).as_record()
    consumer = MicroBatchConsumer(flush_record_count=2)

    assert consumer.add_event(first) == []
    batches = consumer.add_event(second)

    assert len(batches) == 2
    assert {batch["event_hour"] for batch in batches} == {"09", "10"}
    assert all(batch["record_count"] == 1 for batch in batches)


def test_metadata_writer_from_env_uses_postgres_when_dsn_is_configured(monkeypatch):
    monkeypatch.setenv("PROJECT_METADATA_DSN", "postgresql://airflow:airflow@postgres/db")

    writer = metadata_writer_from_env()

    assert isinstance(writer, PostgresMetadataWriter)
