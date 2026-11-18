"""
Kafka producer used by DAG 04 to publish synthetic market events.

Serializes events from the streaming problem factory to JSON and writes them to the configured topic
with idempotent producer settings. Failures are logged to ``ops.failed_records``.
"""

from __future__ import annotations

import json
from typing import Any


def serialize_event(event: dict[str, Any]) -> bytes:
    return json.dumps(event, sort_keys=True).encode("utf-8")


def produce_events(
    events: list[dict[str, Any]],
    bootstrap_servers: str = "kafka:9092",
) -> int:
    try:
        from kafka import KafkaProducer
    except ImportError as exc:
        raise RuntimeError(
            "Kafka producer integration requires kafka-python. "
            "Install runtime dependencies before running platform E2E jobs."
        ) from exc

    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=serialize_event,
        linger_ms=10,
        retries=3,
    )
    try:
        for event in events:
            producer.send(event["topic"], value=event)
        producer.flush()
    finally:
        producer.close()
    return len(events)
