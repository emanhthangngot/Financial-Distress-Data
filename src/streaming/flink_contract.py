"""Deterministic oracle for the Stage 5 Flink event-time contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class FlinkVariantConfig:
    parallelism: int
    checkpointing: bool
    deduplicate: bool

    def validate(self, name: str) -> None:
        if self.parallelism <= 0:
            raise ValueError(f"{name}.parallelism must be positive")


@dataclass(frozen=True)
class FlinkStreamingConfig:
    schema_version: int
    run_id: str
    flink_version: str
    kafka_bootstrap_servers: str
    source_topic: str
    consumer_group: str
    output_root: str
    window_seconds: int
    max_out_of_orderness_seconds: int
    allowed_lateness_seconds: int
    dedup_ttl_seconds: int
    checkpoint_interval_ms: int
    baseline: FlinkVariantConfig
    optimized: FlinkVariantConfig

    def validate(self) -> None:
        if self.schema_version != 1:
            raise ValueError("schema_version must be 1")
        if not self.run_id or not self.source_topic or not self.kafka_bootstrap_servers:
            raise ValueError("run_id, source_topic and kafka_bootstrap_servers are required")
        for name in (
            "window_seconds",
            "max_out_of_orderness_seconds",
            "allowed_lateness_seconds",
            "dedup_ttl_seconds",
            "checkpoint_interval_ms",
        ):
            minimum = 0 if "lateness" in name or "orderness" in name else 1
            if getattr(self, name) < minimum:
                raise ValueError(f"{name} must be at least {minimum}")
        self.baseline.validate("baseline")
        self.optimized.validate("optimized")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def fixture(cls, **overrides: Any) -> FlinkStreamingConfig:
        values: dict[str, Any] = {
            "schema_version": 1,
            "run_id": "fixture",
            "flink_version": "1.20.3",
            "kafka_bootstrap_servers": "kafka:9092",
            "source_topic": "financial.price_events",
            "consumer_group": "fixture",
            "output_root": "/tmp/flink-fixture",
            "window_seconds": 10,
            "max_out_of_orderness_seconds": 120,
            "allowed_lateness_seconds": 180,
            "dedup_ttl_seconds": 900,
            "checkpoint_interval_ms": 5000,
            "baseline": FlinkVariantConfig(1, False, False),
            "optimized": FlinkVariantConfig(4, True, True),
        }
        values.update(overrides)
        config = cls(**values)
        config.validate()
        return config


def load_flink_streaming_config(path: str | Path) -> FlinkStreamingConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Flink config must be a mapping")
    config = FlinkStreamingConfig(
        **{
            **raw,
            "baseline": FlinkVariantConfig(**raw["baseline"]),
            "optimized": FlinkVariantConfig(**raw["optimized"]),
        }
    )
    config.validate()
    return config


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    # Flink 1.20 image uses Python 3.10, where datetime.UTC is unavailable.
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)  # noqa: UP017


def price_event_error(event: dict[str, Any]) -> str | None:
    """Return the price-event contract error, or None when the event is valid."""
    required = ("event_id", "event_type", "ticker", "event_timestamp", "price", "volume")
    missing = [field for field in required if event.get(field) is None]
    if missing:
        return f"missing required event fields: {', '.join(missing)}"
    try:
        _timestamp(str(event["event_timestamp"]))
        float(event["price"])
        int(event["volume"])
    except (TypeError, ValueError):
        return "event_timestamp, price or volume has an invalid type"
    return None


def process_bounded_events(
    events: list[dict[str, Any]], config: FlinkStreamingConfig, *, optimized: bool
) -> dict[str, Any]:
    """Evaluate a finite replay with the same ordering rules used by the Flink job."""
    seen: set[str] = set()
    invalid: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    allowed_late: list[dict[str, Any]] = []
    too_late: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    max_event_time: datetime | None = None

    for event in events:
        if price_event_error(event):
            invalid.append(event)
            continue
        event_id = str(event["event_id"])
        if optimized and event_id in seen:
            duplicates.append(event)
            continue
        seen.add(event_id)
        event_time = _timestamp(str(event["event_timestamp"]))
        watermark = (
            max_event_time - timedelta(seconds=config.max_out_of_orderness_seconds)
            if max_event_time is not None
            else None
        )
        if watermark is not None and event_time < watermark:
            if event_time + timedelta(seconds=config.allowed_lateness_seconds) < watermark:
                too_late.append(event)
                continue
            allowed_late.append(event)
        accepted.append(event)
        max_event_time = max(max_event_time, event_time) if max_event_time else event_time

    buckets: dict[tuple[str, datetime], list[dict[str, Any]]] = {}
    for event in accepted:
        event_time = _timestamp(str(event["event_timestamp"]))
        epoch = int(event_time.timestamp())
        start = datetime.fromtimestamp(
            epoch - epoch % config.window_seconds,
            tz=timezone.utc,  # noqa: UP017
        )
        buckets.setdefault((str(event["ticker"]), start), []).append(event)
    windows = []
    for (ticker, start), rows in sorted(buckets.items()):
        windows.append(
            {
                "ticker": ticker,
                "window_start": start.isoformat(),
                "window_end": (start + timedelta(seconds=config.window_seconds)).isoformat(),
                "event_count": len(rows),
                "average_price": round(sum(float(row["price"]) for row in rows) / len(rows), 6),
                "total_volume": sum(int(row["volume"]) for row in rows),
            }
        )
    return {
        "counts": {
            "input": len(events),
            "valid": len(events) - len(invalid) - len(duplicates),
            "invalid": len(invalid),
            "duplicates": len(duplicates),
            "allowed_late": len(allowed_late),
            "too_late": len(too_late),
            "window_results": len(windows),
        },
        "windows": windows,
        "allowed_late": allowed_late,
        "too_late": too_late,
        "invalid": invalid,
        "duplicates": duplicates,
    }
