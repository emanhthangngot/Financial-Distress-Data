"""Typed configuration for deterministic generator runs."""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, TypeVar

import yaml


@dataclass(frozen=True)
class OfflineConfig:
    companies: int
    high_cardinality_ids: int
    quarters: int
    dominant_sector: str
    dominant_sector_rate: float
    dominant_exchange: str
    dominant_exchange_rate: float
    duplicate_rate: float
    schema_change_quarter: int

    def validate(self) -> None:
        if self.companies <= 0 or self.quarters <= 1:
            raise ValueError("offline companies must be positive and quarters must exceed one")
        if not 0 < self.high_cardinality_ids <= self.companies:
            raise ValueError("high_cardinality_ids must be in (0, companies]")
        _validate_rate("dominant_sector_rate", self.dominant_sector_rate)
        _validate_rate("dominant_exchange_rate", self.dominant_exchange_rate)
        _validate_rate("duplicate_rate", self.duplicate_rate)
        if not 1 < self.schema_change_quarter <= self.quarters:
            raise ValueError("schema_change_quarter must split the configured quarters")


@dataclass(frozen=True)
class StreamingConfig:
    events: int
    window_seconds: int
    baseline_events_per_window: int
    burst_window: int
    burst_multiplier: int
    late_rate: float
    duplicate_rate: float
    out_of_order_rate: float
    max_lateness_seconds: int
    max_out_of_order_seconds: int

    def validate(self) -> None:
        if self.events <= 0 or self.window_seconds <= 0 or self.baseline_events_per_window <= 0:
            raise ValueError("streaming volume and window settings must be positive")
        if self.burst_window < 0 or self.burst_multiplier <= 1:
            raise ValueError("burst settings must define a non-negative window and multiplier > 1")
        for name in ("late_rate", "duplicate_rate", "out_of_order_rate"):
            _validate_rate(name, getattr(self, name))
        if self.max_lateness_seconds <= 0 or self.max_out_of_order_seconds <= 0:
            raise ValueError("lateness limits must be positive")
        required = self.burst_window * self.baseline_events_per_window
        required += self.baseline_events_per_window * self.burst_multiplier
        if self.events <= required:
            raise ValueError("streaming events must cover baseline and burst windows")


@dataclass(frozen=True)
class OutputConfig:
    root: str
    format: str
    minio_bucket: str
    minio_prefix: str
    kafka_bootstrap_servers: str

    def validate(self) -> None:
        if self.format != "jsonl":
            raise ValueError("output format must be jsonl")
        if not self.root or not self.minio_bucket or not self.minio_prefix:
            raise ValueError("output paths must not be blank")


@dataclass(frozen=True)
class GeneratorConfig:
    schema_version: int
    seed: int
    run_id: str
    offline: OfflineConfig
    streaming: StreamingConfig
    output: OutputConfig

    def validate(self) -> None:
        if self.schema_version != 1:
            raise ValueError("generator config must use schema_version 1")
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        if not self.run_id or any(char not in allowed for char in self.run_id):
            raise ValueError("run_id must contain only letters, digits, hyphens, and underscores")
        self.offline.validate()
        self.streaming.validate()
        self.output.validate()


T = TypeVar("T")


def _validate_rate(name: str, value: float) -> None:
    if not 0 <= value < 1:
        raise ValueError(f"{name} must be in [0, 1)")


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _typed(cls: type[T], raw: dict[str, Any]) -> T:
    expected = {field.name for field in fields(cls)}
    unknown = set(raw) - expected
    missing = expected - set(raw)
    if unknown or missing:
        raise ValueError(
            f"invalid {cls.__name__} keys: missing={sorted(missing)} unknown={sorted(unknown)}"
        )
    return cls(**raw)


def load_generator_config(path: Path, profile: str = "evidence") -> GeneratorConfig:
    """Load a base YAML config and apply one named profile recursively."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("generator config must be a mapping")
    profiles = raw.pop("profiles", {})
    if profile not in profiles:
        raise ValueError(f"unknown generator profile: {profile}")
    effective = _merge(raw, profiles[profile])
    config = GeneratorConfig(
        schema_version=effective["schema_version"],
        seed=effective["seed"],
        run_id=effective["run_id"],
        offline=_typed(OfflineConfig, effective["offline"]),
        streaming=_typed(StreamingConfig, effective["streaming"]),
        output=_typed(OutputConfig, effective["output"]),
    )
    config.validate()
    return config
