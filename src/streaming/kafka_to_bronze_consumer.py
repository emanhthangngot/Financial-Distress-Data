from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class MicroBatchConsumer:
    flush_record_count: int = 1000
    flush_interval_seconds: int = 60
    batches: list[dict[str, Any]] = field(default_factory=list)
    _buffer: list[dict[str, Any]] = field(default_factory=list)
    _elapsed_seconds: int = 0

    def add_event(self, event: dict[str, Any], elapsed_seconds: int = 0) -> list[dict[str, Any]]:
        self._buffer.append(event)
        self._elapsed_seconds += elapsed_seconds
        should_flush_records = len(self._buffer) >= self.flush_record_count
        should_flush_time = self._elapsed_seconds >= self.flush_interval_seconds
        if should_flush_records or should_flush_time:
            return self.flush()
        return []

    def flush(self) -> list[dict[str, Any]]:
        if not self._buffer:
            return []
        by_partition: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        for event in self._buffer:
            event_date = str(event["event_timestamp"])[:10]
            event_hour = str(event["event_timestamp"])[11:13] or "00"
            by_partition[(event["topic"], event_date, event_hour)].append(event)
        flushed = []
        for (topic, event_date, event_hour), records in by_partition.items():
            batch_id = str(uuid4())
            batch = {
                "batch_id": batch_id,
                "topic": topic,
                "event_date": event_date,
                "event_hour": event_hour,
                "records": records,
                "record_count": len(records),
                "bronze_path": (
                    "s3a://financial-distress-lake/bronze/kafka/"
                    f"{topic}/event_date={event_date}/event_hour={event_hour}/batch_id={batch_id}/"
                ),
            }
            flushed.append(batch)
            self.batches.append(batch)
        self._buffer = []
        self._elapsed_seconds = 0
        return flushed


def decode_json_message(message: Any) -> dict[str, Any]:
    value = message.value
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        return json.loads(value)
    if isinstance(value, dict):
        return value
    raise TypeError(f"unsupported Kafka message value type: {type(value).__name__}")


def consume_json_messages(
    kafka_consumer: Iterable[Any],
    microbatch_consumer: MicroBatchConsumer,
    max_records: int | None = None,
) -> list[dict[str, Any]]:
    batches: list[dict[str, Any]] = []
    try:
        for index, message in enumerate(kafka_consumer, start=1):
            batches.extend(microbatch_consumer.add_event(decode_json_message(message)))
            if max_records is not None and index >= max_records:
                break
        batches.extend(microbatch_consumer.flush())
        return batches
    finally:
        close = getattr(kafka_consumer, "close", None)
        if close is not None:
            close()


def create_kafka_consumer(
    topics: list[str],
    bootstrap_servers: str = "kafka:9092",
    group_id: str = "financial-distress-bronze-writer",
) -> Any:
    try:
        from kafka import KafkaConsumer
    except ImportError as exc:
        raise RuntimeError(
            "Kafka broker integration requires kafka-python. "
            "Install runtime dependencies before running Stage 1 streaming evidence jobs."
        ) from exc

    return KafkaConsumer(
        *topics,
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
