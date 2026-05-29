from __future__ import annotations

from collections import defaultdict
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
        by_topic: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in self._buffer:
            by_topic[event["topic"]].append(event)
        flushed = []
        for topic, records in by_topic.items():
            event_date = str(records[0]["event_timestamp"])[:10]
            event_hour = str(records[0]["event_timestamp"])[11:13] or "00"
            batch = {
                "batch_id": str(uuid4()),
                "topic": topic,
                "event_date": event_date,
                "event_hour": event_hour,
                "records": records,
                "record_count": len(records),
                "bronze_path": (
                    "s3a://financial-distress-lake/bronze/kafka/"
                    f"{topic}/event_date={event_date}/event_hour={event_hour}/"
                ),
            }
            flushed.append(batch)
            self.batches.append(batch)
        self._buffer = []
        self._elapsed_seconds = 0
        return flushed
