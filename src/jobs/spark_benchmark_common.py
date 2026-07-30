"""Shared contracts for reproducible Spark optimization benchmarks."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any

import yaml


@dataclass(frozen=True)
class VariantConfig:
    shuffle_partitions: int
    output_files: int
    adaptive_enabled: bool
    auto_broadcast_enabled: bool

    def validate(self, name: str) -> None:
        if self.shuffle_partitions <= 0 or self.output_files <= 0:
            raise ValueError(f"{name} partition counts must be positive")


@dataclass(frozen=True)
class StorageConfig:
    query_filter_year: int
    partition_columns: tuple[str, ...]
    target_files_per_partition: int

    def validate(self) -> None:
        if not self.partition_columns or self.target_files_per_partition <= 0:
            raise ValueError("storage partition settings must be non-empty and positive")


@dataclass(frozen=True)
class BenchmarkConfig:
    schema_version: int
    run_id: str
    input_root: str
    output_root: str
    repetitions: int
    warmup_runs: int
    salt_buckets: int
    baseline: VariantConfig
    optimized: VariantConfig
    storage: StorageConfig

    def validate(self) -> None:
        if self.schema_version != 1:
            raise ValueError("benchmark config must use schema_version 1")
        if not self.run_id or not self.input_root or not self.output_root:
            raise ValueError("benchmark run and paths must not be blank")
        if self.repetitions <= 0:
            raise ValueError("repetitions must be positive")
        if self.warmup_runs < 0 or self.salt_buckets <= 1:
            raise ValueError("warmup_runs must be non-negative and salt_buckets must exceed one")
        self.baseline.validate("baseline")
        self.optimized.validate("optimized")
        self.storage.validate()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_benchmark_config(path: str | Path) -> BenchmarkConfig:
    """Load the checked-in YAML/JSON benchmark protocol."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("benchmark config must be a mapping")
    config = BenchmarkConfig(
        schema_version=int(raw["schema_version"]),
        run_id=str(raw["run_id"]),
        input_root=str(raw["input_root"]),
        output_root=str(raw["output_root"]),
        repetitions=int(raw["repetitions"]),
        warmup_runs=int(raw["warmup_runs"]),
        salt_buckets=int(raw["salt_buckets"]),
        baseline=VariantConfig(**raw["baseline"]),
        optimized=VariantConfig(**raw["optimized"]),
        storage=StorageConfig(
            query_filter_year=int(raw["storage"]["query_filter_year"]),
            partition_columns=tuple(raw["storage"]["partition_columns"]),
            target_files_per_partition=int(raw["storage"]["target_files_per_partition"]),
        ),
    )
    config.validate()
    return config


def canonical_output_digest(rows: list[dict[str, Any]]) -> str:
    """Hash logical output independently of Spark partition or collection order."""
    payload = "\n".join(
        sorted(json.dumps(row, sort_keys=True, separators=(",", ":"), default=str) for row in rows)
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def summarize_durations(durations: list[float]) -> dict[str, Any]:
    if not durations:
        raise ValueError("at least one measured duration is required")
    rounded = [round(value, 6) for value in durations]
    return {
        "runs_seconds": rounded,
        "median_seconds": round(median(rounded), 6),
        "min_seconds": min(rounded),
        "max_seconds": max(rounded),
    }


def assert_equivalent_reports(baseline: dict[str, Any], optimized: dict[str, Any]) -> None:
    """Reject comparisons that do not use identical inputs and logical outputs."""
    for field in ("run_id", "input_digest", "input_counts", "output_digest", "output_rows"):
        if baseline.get(field) != optimized.get(field):
            raise ValueError(
                f"benchmark {field} mismatch: "
                f"baseline={baseline.get(field)!r} optimized={optimized.get(field)!r}"
            )
    baseline_storage = baseline.get("storage")
    optimized_storage = optimized.get("storage")
    if (baseline_storage is None) != (optimized_storage is None):
        raise ValueError("benchmark storage evidence must be present in both reports")
    if baseline_storage is not None:
        for field in ("row_count", "filtered_year", "filtered_row_count"):
            if baseline_storage.get(field) != optimized_storage.get(field):
                raise ValueError(
                    f"benchmark storage {field} mismatch: "
                    f"baseline={baseline_storage.get(field)!r} "
                    f"optimized={optimized_storage.get(field)!r}"
                )


def file_digest(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
