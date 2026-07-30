"""
Loader and validator for generator configuration files.

Reads YAML configs (e.g. ``configs/generator/*.yaml``), applies environment overrides, validates
against the schema in ``docs/01_data_generator.md``, and returns a typed config object. The fixture
adapter and streaming factory both consume this config.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path("configs/collector_config.yaml")


@dataclass(frozen=True)
class SkewConfig:
    top_company_ticker: str = "AAA"
    top_company_share: float = 0.6
    tail_tickers: tuple[str, ...] = ("BBB", "CCC", "DDD", "EEE")


@dataclass(frozen=True)
class CardinalityConfig:
    industries_pool: tuple[str, ...] = (
        "Manufacturing",
        "Real Estate",
        "Technology",
        "Financials",
        "Energy",
        "Consumer Goods",
        "Healthcare",
        "Utilities",
        "Materials",
        "Industrials",
        "Telecom",
        "Retail",
    )
    sectors_pool: tuple[str, ...] = (
        "Industrials",
        "Financials",
        "Technology",
        "Energy",
        "Consumer Discretionary",
        "Healthcare",
    )
    companies_count: int = 5


@dataclass(frozen=True)
class EvolutionConfig:
    legacy_null_columns: tuple[str, ...] = (
        "ebit",
        "operating_cash_flow",
        "retained_earnings",
    )
    legacy_partition_cutoff: str = "2020Q1"


@dataclass(frozen=True)
class DuplicationConfig:
    offline_rate: float = 0.02
    streaming_rate: float = 0.015


@dataclass(frozen=True)
class BurstConfig:
    enabled: bool = True
    window_seconds: int = 10
    record_count: int = 200


@dataclass(frozen=True)
class LateArrivalConfig:
    enabled: bool = True
    max_lag_seconds: int = 3600


@dataclass(frozen=True)
class StreamingConfig:
    burst: BurstConfig = field(default_factory=BurstConfig)
    late_arrival: LateArrivalConfig = field(default_factory=LateArrivalConfig)


@dataclass(frozen=True)
class GeneratorConfig:
    """Top-level generator knobs loaded from `configs/collector_config.yaml`.

    `enabled` is the master switch. When False, callers must keep the legacy
    hard-coded fixture behavior. The default keeps back-compat for any test or
    smoke path that constructs the adapter without a config object.
    """

    enabled: bool = False
    fixture_seed: int = 42
    skew: SkewConfig = field(default_factory=SkewConfig)
    cardinality: CardinalityConfig = field(default_factory=CardinalityConfig)
    evolution: EvolutionConfig = field(default_factory=EvolutionConfig)
    duplication: DuplicationConfig = field(default_factory=DuplicationConfig)
    streaming: StreamingConfig = field(default_factory=StreamingConfig)


def _as_tuple(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(value)
    raise TypeError(f"Expected list or tuple, got {type(value).__name__}")


def _coerce_float(value: Any, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    raise TypeError(f"Expected float-like, got {type(value).__name__}")


def _coerce_int(value: Any, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"Expected int-like, got {type(value).__name__}")


def _build_skew(block: dict[str, Any] | None) -> SkewConfig:
    block = block or {}
    return SkewConfig(
        top_company_ticker=str(block.get("top_company_ticker", "AAA")),
        top_company_share=_coerce_float(block.get("top_company_share"), 0.6),
        tail_tickers=_as_tuple(block.get("tail_tickers", ("BBB", "CCC", "DDD", "EEE"))),
    )


def _build_cardinality(block: dict[str, Any] | None) -> CardinalityConfig:
    block = block or {}
    return CardinalityConfig(
        industries_pool=_as_tuple(block.get("industries_pool")),
        sectors_pool=_as_tuple(block.get("sectors_pool")),
        companies_count=_coerce_int(block.get("companies_count"), 5),
    )


def _build_evolution(block: dict[str, Any] | None) -> EvolutionConfig:
    block = block or {}
    return EvolutionConfig(
        legacy_null_columns=_as_tuple(block.get("legacy_null_columns")),
        legacy_partition_cutoff=str(block.get("legacy_partition_cutoff", "2020Q1")),
    )


def _build_duplication(block: dict[str, Any] | None) -> DuplicationConfig:
    block = block or {}
    return DuplicationConfig(
        offline_rate=_coerce_float(block.get("offline_rate"), 0.02),
        streaming_rate=_coerce_float(block.get("streaming_rate"), 0.015),
    )


def _build_burst(block: dict[str, Any] | None) -> BurstConfig:
    block = block or {}
    return BurstConfig(
        enabled=bool(block.get("enabled", True)),
        window_seconds=_coerce_int(block.get("window_seconds"), 10),
        record_count=_coerce_int(block.get("record_count"), 200),
    )


def _build_late_arrival(block: dict[str, Any] | None) -> LateArrivalConfig:
    block = block or {}
    return LateArrivalConfig(
        enabled=bool(block.get("enabled", True)),
        max_lag_seconds=_coerce_int(block.get("max_lag_seconds"), 3600),
    )


def _build_streaming(block: dict[str, Any] | None) -> StreamingConfig:
    block = block or {}
    return StreamingConfig(
        burst=_build_burst(block.get("burst")),
        late_arrival=_build_late_arrival(block.get("late_arrival")),
    )


def load_generator_config(path: str | Path = DEFAULT_CONFIG_PATH) -> GeneratorConfig:
    """Load `generator:` block from the collector config YAML.

    Returns a default-off `GeneratorConfig` when the file is missing, the
    `generator:` block is absent, or any nested key is malformed. Existing
    callers that build the adapter without a config object are unaffected.
    """
    config_path = Path(path)
    if not config_path.exists():
        return GeneratorConfig()

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return GeneratorConfig()

    block = raw.get("generator")
    if not isinstance(block, dict):
        return GeneratorConfig()

    return GeneratorConfig(
        enabled=bool(block.get("enabled", False)),
        fixture_seed=_coerce_int(block.get("fixture_seed"), 42),
        skew=_build_skew(block.get("skew")),
        cardinality=_build_cardinality(block.get("cardinality")),
        evolution=_build_evolution(block.get("evolution")),
        duplication=_build_duplication(block.get("duplication")),
        streaming=_build_streaming(block.get("streaming")),
    )


__all__ = [
    "BurstConfig",
    "CardinalityConfig",
    "DuplicationConfig",
    "EvolutionConfig",
    "GeneratorConfig",
    "LateArrivalConfig",
    "SkewConfig",
    "StreamingConfig",
    "load_generator_config",
]
