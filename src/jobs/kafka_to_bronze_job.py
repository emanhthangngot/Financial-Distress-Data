from __future__ import annotations

import json
import os
import time
from typing import Any

from src.io.minio_writer import write_minio_dataset
from src.streaming.events import StreamEvent
from src.streaming.kafka_producer import produce_events
from src.streaming.kafka_to_bronze_consumer import MicroBatchConsumer

STREAM_TOPICS = [
    "financial.price_events",
    "financial.news_events",
    "financial.alert_events",
]


def build_stage1_stream_events(evidence_run_id: str) -> list[dict[str, Any]]:
    events = [
        StreamEvent.price_update(
            "AAA",
            "2026-01-01T09:00:00+00:00",
            "2026-01-01T09:00:01+00:00",
            10.0,
            100,
        ).as_record(),
        StreamEvent.price_update(
            "AAA",
            "2026-01-01T09:00:02+00:00",
            "2026-01-01T09:00:03+00:00",
            10.1,
            120,
        ).as_record(),
        StreamEvent.price_update(
            "BBB",
            "2026-01-01T09:00:04+00:00",
            "2026-01-01T09:00:05+00:00",
            8.0,
            90,
        ).as_record(),
        StreamEvent.news_sentiment(
            "AAA",
            "2026-01-01T09:00:06+00:00",
            "2026-01-01T09:00:07+00:00",
            -0.2,
            True,
            0.5,
            "https://example.local/news/aaa-risk",
        ).as_record(),
        StreamEvent.news_sentiment(
            "BBB",
            "2026-01-01T09:00:08+00:00",
            "2026-01-01T09:00:09+00:00",
            -0.7,
            True,
            0.9,
            "https://example.local/news/bbb-distress",
        ).as_record(),
        StreamEvent.alert(
            "BBB",
            "2026-01-01T09:00:10+00:00",
            "2026-01-01T09:00:11+00:00",
            "price_drop",
        ).as_record(),
    ]
    return [{**event, "evidence_run_id": evidence_run_id} for event in events]


def kafka_bootstrap_servers() -> str:
    return os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")


def produce_stage1_stream_events(evidence_run_id: str) -> int:
    return produce_events(build_stage1_stream_events(evidence_run_id), kafka_bootstrap_servers())


def _decode_message_value(value: Any) -> dict[str, Any]:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        return json.loads(value)
    if isinstance(value, dict):
        return value
    raise TypeError(f"unsupported Kafka message value type: {type(value).__name__}")


def consume_stage1_stream_events_to_bronze(
    evidence_run_id: str,
    bucket: str,
    expected_records: int = 3,
    timeout_seconds: int = 30,
) -> list[dict[str, Any]]:
    from src.jobs.stage1_evidence_job import _ensure_bucket, _minio_client

    try:
        from kafka import KafkaConsumer
    except ImportError as exc:
        raise RuntimeError(
            "Kafka consumer integration requires kafka-python. "
            "Install runtime dependencies before running Stage 1 E2E jobs."
        ) from exc

    consumer = KafkaConsumer(
        *STREAM_TOPICS,
        bootstrap_servers=kafka_bootstrap_servers(),
        group_id=f"stage1-e2e-{evidence_run_id}",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        consumer_timeout_ms=1000,
    )
    microbatch = MicroBatchConsumer(flush_record_count=expected_records)
    batches: list[dict[str, Any]] = []
    matched = 0
    deadline = time.monotonic() + timeout_seconds
    try:
        while matched < expected_records and time.monotonic() < deadline:
            for message in consumer:
                event = _decode_message_value(message.value)
                if event.get("evidence_run_id") != evidence_run_id:
                    continue
                matched += 1
                batches.extend(microbatch.add_event(event))
                if matched >= expected_records:
                    break
        batches.extend(microbatch.flush())
    finally:
        consumer.close()

    if matched < expected_records:
        raise RuntimeError(
            f"Expected {expected_records} Kafka records for {evidence_run_id}, got {matched}."
        )

    client = _minio_client()
    _ensure_bucket(client, bucket)
    for batch in batches:
        object_key = (
            f"bronze/kafka/{batch['topic']}/event_date={batch['event_date']}/"
            f"event_hour={batch['event_hour']}/batch_id={batch['batch_id']}/data.parquet"
        )
        write_minio_dataset(client, bucket, f"{bucket}/{object_key}", batch["records"])
        batch["bronze_object_key"] = object_key
    return batches
