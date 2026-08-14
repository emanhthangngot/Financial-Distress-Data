"""Flink CDC job contract without importing Flink at module load time."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .config import CDCConfig


@dataclass(frozen=True)
class CDCJobSpec:
    source: dict[str, str]
    sink: dict[str, str]
    initial_snapshot: bool = True


def build_job_spec(config: CDCConfig | None = None) -> CDCJobSpec:
    cfg = config or CDCConfig.from_env()
    cfg.validate_logical_replication()
    return CDCJobSpec(
        source=cfg.connector_properties(),
        sink=cfg.sink_properties(),
        initial_snapshot=cfg.snapshot_mode != "never",
    )


build_flink_cdc_job = build_job_spec


def normalize_change(event: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a Debezium/Flink envelope while preserving operation type."""
    operation = str(event.get("op", event.get("operation", "c"))).lower()
    operation = {"r": "read", "c": "insert", "u": "update", "d": "delete"}.get(operation, operation)
    payload = event.get("after")
    if payload is None and operation == "delete":
        payload = event.get("before", {})
    if not isinstance(payload, Mapping):
        payload = event.get("payload", {})
    result = dict(payload) if isinstance(payload, Mapping) else {}
    result["_cdc_operation"] = operation
    if "ts_ms" in event:
        result["_cdc_source_ts_ms"] = event["ts_ms"]
    return result


@dataclass
class FlinkCDCJob:
    """Executable local adapter used by tests and the eventual Flink entrypoint."""

    spec: CDCJobSpec

    def run(
        self,
        events: Iterable[Mapping[str, Any]],
        sink: Callable[[dict[str, Any]], Any] | None = None,
    ) -> dict[str, int]:
        counts = {"insert": 0, "update": 0, "delete": 0, "read": 0, "written": 0}
        for event in events:
            row = normalize_change(event)
            operation = row["_cdc_operation"]
            counts[operation] = counts.get(operation, 0) + 1
            if sink is not None:
                sink(row)
            counts["written"] += 1
        return counts


def run_flink_cdc_job(
    events: Iterable[Mapping[str, Any]],
    *,
    config: CDCConfig | None = None,
    sink: Callable[[dict[str, Any]], Any] | None = None,
) -> dict[str, int]:
    return FlinkCDCJob(build_job_spec(config)).run(events, sink=sink)


__all__ = [
    "CDCJobSpec",
    "FlinkCDCJob",
    "build_flink_cdc_job",
    "build_job_spec",
    "normalize_change",
    "run_flink_cdc_job",
]
