"""Tests for the generator config loader (W17.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.generators.config_loader import (
    BurstConfig,
    CardinalityConfig,
    DuplicationConfig,
    EvolutionConfig,
    GeneratorConfig,
    LateArrivalConfig,
    SkewConfig,
    StreamingConfig,
    load_generator_config,
)


def test_load_generator_config_returns_default_off_when_file_missing(tmp_path: Path) -> None:
    cfg = load_generator_config(tmp_path / "missing.yaml")
    assert cfg.enabled is False
    assert isinstance(cfg, GeneratorConfig)
    assert cfg.fixture_seed == 42
    assert cfg.skew.top_company_share == pytest.approx(0.6)
    assert cfg.duplication.offline_rate == pytest.approx(0.02)
    assert cfg.streaming.burst.enabled is True
    assert cfg.streaming.late_arrival.max_lag_seconds == 3600


def test_load_generator_config_returns_default_off_when_block_absent(tmp_path: Path) -> None:
    cfg_file = tmp_path / "collector.yaml"
    cfg_file.write_text("collector:\n  mode: local\n", encoding="utf-8")
    cfg = load_generator_config(cfg_file)
    assert cfg.enabled is False
    assert cfg.skew.top_company_ticker == "AAA"


def test_load_generator_config_coerces_string_numbers(tmp_path: Path) -> None:
    cfg_file = tmp_path / "collector.yaml"
    cfg_file.write_text(
        "generator:\n"
        "  enabled: true\n"
        "  fixture_seed: '7'\n"
        "  skew:\n"
        "    top_company_share: '0.6'\n"
        "    top_company_ticker: 'AAA'\n"
        "    tail_tickers: ['BBB', 'CCC']\n"
        "  cardinality:\n"
        "    companies_count: '8'\n"
        "    industries_pool: ['Tech']\n"
        "    sectors_pool: ['Financials']\n"
        "  evolution:\n"
        "    legacy_partition_cutoff: '2021Q2'\n"
        "    legacy_null_columns: ['ebit']\n"
        "  duplication:\n"
        "    offline_rate: '0.05'\n"
        "    streaming_rate: '0.025'\n"
        "  streaming:\n"
        "    burst:\n"
        "      window_seconds: '5'\n"
        "      record_count: '50'\n"
        "    late_arrival:\n"
        "      max_lag_seconds: '1800'\n",
        encoding="utf-8",
    )
    cfg = load_generator_config(cfg_file)
    assert cfg.enabled is True
    assert cfg.fixture_seed == 7
    assert cfg.skew.top_company_share == pytest.approx(0.6)
    assert cfg.skew.tail_tickers == ("BBB", "CCC")
    assert cfg.cardinality.companies_count == 8
    assert cfg.cardinality.industries_pool == ("Tech",)
    assert cfg.evolution.legacy_partition_cutoff == "2021Q2"
    assert cfg.duplication.offline_rate == pytest.approx(0.05)
    assert cfg.streaming.burst.window_seconds == 5
    assert cfg.streaming.burst.record_count == 50
    assert cfg.streaming.late_arrival.max_lag_seconds == 1800


def test_load_generator_config_falls_back_on_malformed_yaml(tmp_path: Path) -> None:
    cfg_file = tmp_path / "broken.yaml"
    cfg_file.write_text("generator: {enabled: true,\n", encoding="utf-8")
    cfg = load_generator_config(cfg_file)
    assert cfg.enabled is False


def test_load_generator_config_falls_back_on_non_dict_block(tmp_path: Path) -> None:
    cfg_file = tmp_path / "collector.yaml"
    cfg_file.write_text("generator: not-a-dict\n", encoding="utf-8")
    cfg = load_generator_config(cfg_file)
    assert cfg.enabled is False


def test_sub_configs_have_expected_defaults() -> None:
    assert SkewConfig().top_company_ticker == "AAA"
    assert CardinalityConfig().companies_count == 5
    assert EvolutionConfig().legacy_partition_cutoff == "2020Q1"
    assert DuplicationConfig().offline_rate == pytest.approx(0.02)
    assert BurstConfig().enabled is True
    assert LateArrivalConfig().max_lag_seconds == 3600
    assert isinstance(StreamingConfig().burst, BurstConfig)


def test_load_generator_config_uses_project_default_path() -> None:
    cfg = load_generator_config("configs/collector_config.yaml")
    # Project default file currently has generator block with enabled=true.
    assert cfg.enabled is True
    assert cfg.fixture_seed == 42
    assert cfg.skew.top_company_ticker == "AAA"
