"""Generate deterministic bursty, late, out-of-order stream events."""

from __future__ import annotations

import hashlib
import random
from datetime import UTC, datetime, timedelta
from typing import Any

from src.generator.config import GeneratorConfig


def _event_id(seed: int, sequence: int) -> str:
    return hashlib.sha256(f"{seed}:price:{sequence}".encode()).hexdigest()


def _flagged_indexes(count: int, rate: float, rng: random.Random) -> set[int]:
    return set(rng.sample(range(count), min(round(count * rate), count)))


def generate_stream_events(config: GeneratorConfig) -> list[dict[str, Any]]:
    """Create a finite Kafka-ready replay schedule ordered by ingest time."""
    config.validate()
    settings = config.streaming
    rng = random.Random(config.seed + 1)
    duplicate_count = round(settings.events * settings.duplicate_rate)
    unique_count = settings.events - duplicate_count
    late_indexes = _flagged_indexes(unique_count, settings.late_rate, rng)
    out_of_order_indexes = _flagged_indexes(unique_count, settings.out_of_order_rate, rng)
    duplicate_indexes = rng.sample(range(unique_count), duplicate_count)
    start = datetime(2026, 1, 2, 9, tzinfo=UTC)
    baseline = settings.baseline_events_per_window
    burst_size = baseline * settings.burst_multiplier
    events: list[dict[str, Any]] = []

    for sequence in range(unique_count):
        before_burst = settings.burst_window * baseline
        if sequence < before_burst:
            window = sequence // baseline
            position = sequence % baseline
        elif sequence < before_burst + burst_size:
            window = settings.burst_window
            position = sequence - before_burst
        else:
            after = sequence - before_burst - burst_size
            window = settings.burst_window + 1 + after // baseline
            position = after % baseline
        ingest = start + timedelta(
            seconds=window * settings.window_seconds,
            microseconds=position,
        )
        lateness = 0
        if sequence in late_indexes:
            lateness = 1 + sequence % settings.max_lateness_seconds
        elif sequence in out_of_order_indexes:
            lateness = 1 + sequence % settings.max_out_of_order_seconds
        event_time = ingest - timedelta(seconds=lateness)
        event = {
            "topic": "financial.price_events",
            "event_id": _event_id(config.seed, sequence),
            "event_type": "price_update",
            "ticker": f"G{sequence % config.offline.companies:07d}",
            "event_timestamp": event_time.isoformat(),
            "created_ts": ingest.isoformat(),
            "ingest_timestamp": ingest.isoformat(),
            "price": round(10 + rng.random() * 90, 2),
            "volume": 1000 + sequence,
            "source_sequence": sequence,
            "is_burst": window == settings.burst_window,
            "is_late": sequence in late_indexes,
            "is_out_of_order": sequence in out_of_order_indexes,
            "is_injected_duplicate": False,
        }
        events.append(event)

    for source_index in duplicate_indexes:
        duplicate = dict(events[source_index])
        duplicate["ingest_timestamp"] = (
            datetime.fromisoformat(duplicate["ingest_timestamp"]) + timedelta(microseconds=500_000)
        ).isoformat()
        duplicate["created_ts"] = duplicate["ingest_timestamp"]
        duplicate["is_injected_duplicate"] = True
        events.append(duplicate)
    events.sort(key=lambda row: (row["ingest_timestamp"], row["is_injected_duplicate"]))
    return events
