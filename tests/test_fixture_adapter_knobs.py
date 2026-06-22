"""Tests for VnstockFixtureAdapter config knobs (W17.2)."""
from __future__ import annotations

import pytest

from src.collectors.source_adapters.vnstock_fixture_adapter import VnstockFixtureAdapter
from src.generators.config_loader import (
    CardinalityConfig,
    DuplicationConfig,
    EvolutionConfig,
    GeneratorConfig,
    SkewConfig,
)


def _enabled_config(**overrides) -> GeneratorConfig:
    base = GeneratorConfig(
        enabled=True,
        fixture_seed=42,
        skew=SkewConfig(
            top_company_ticker="AAA",
            top_company_share=0.6,
            tail_tickers=("BBB", "CCC", "DDD", "EEE"),
        ),
        cardinality=CardinalityConfig(
            industries_pool=("Tech", "Energy", "Healthcare"),
            sectors_pool=("Industrials", "Financials"),
            companies_count=5,
        ),
        evolution=EvolutionConfig(
            legacy_null_columns=("ebit", "operating_cash_flow"),
            legacy_partition_cutoff="2020Q1",
        ),
        duplication=DuplicationConfig(offline_rate=0.02, streaming_rate=0.015),
    )
    if overrides:
        from dataclasses import replace

        base = replace(base, **overrides)
    return base


def test_legacy_default_behavior_when_config_is_none() -> None:
    adapter = VnstockFixtureAdapter()
    companies = adapter.fetch_companies()
    assert [c["ticker"] for c in companies] == ["AAA", "BBB"]


def test_legacy_default_behavior_when_config_disabled() -> None:
    adapter = VnstockFixtureAdapter(config=GeneratorConfig(enabled=False))
    companies = adapter.fetch_companies()
    assert [c["ticker"] for c in companies] == ["AAA", "BBB"]


def test_cardinality_knots_emit_expected_company_count() -> None:
    adapter = VnstockFixtureAdapter(config=_enabled_config())
    companies = adapter.fetch_companies()
    assert len(companies) == 5
    tickers = [c["ticker"] for c in companies]
    assert "AAA" in tickers
    # Tail tickers come from a known pool
    assert all(t in {"AAA", "BBB", "CCC", "DDD", "EEE"} for t in tickers)


def test_skew_top_share_within_tolerance() -> None:
    adapter = VnstockFixtureAdapter(config=_enabled_config())
    companies = adapter.fetch_companies()
    top_count = sum(1 for c in companies if c["ticker"] == "AAA")
    actual_share = top_count / len(companies)
    # 60% target with ±2pp tolerance and integer rounding
    assert 0.55 <= actual_share <= 0.65


def test_industry_and_sector_drawn_from_pools() -> None:
    adapter = VnstockFixtureAdapter(config=_enabled_config())
    companies = adapter.fetch_companies()
    for c in companies:
        assert c["industry"] in {"Tech", "Energy", "Healthcare"}
        assert c["sector"] in {"Industrials", "Financials"}


def test_evolution_marks_legacy_columns_none_before_cutoff() -> None:
    adapter = VnstockFixtureAdapter(config=_enabled_config())
    rows = adapter.fetch_financial_statements("AAA", 2019, 2020)
    legacy = [r for r in rows if r["report_period"] < "2020Q1"]
    assert legacy, "expected at least one legacy row"
    for r in legacy:
        assert r["ebit"] is None
        assert r["operating_cash_flow"] is None
    modern = [r for r in rows if r["report_period"] >= "2020Q1"]
    assert modern, "expected at least one modern row"
    for r in modern:
        assert r["ebit"] is not None
        assert r["operating_cash_flow"] is not None


def test_offline_duplication_adds_expected_count() -> None:
    adapter = VnstockFixtureAdapter(config=_enabled_config())
    rows = adapter.fetch_financial_statements("AAA", 2020, 2020)
    base = sum(1 for r in rows if r.get("_is_duplicate") is not True)
    dups = sum(1 for r in rows if r.get("_is_duplicate") is True)
    assert dups == int(0.02 * base)


def test_dup_rows_match_canonical_row() -> None:
    adapter = VnstockFixtureAdapter(config=_enabled_config(duplication=DuplicationConfig(offline_rate=0.5, streaming_rate=0.015)))
    rows = adapter.fetch_financial_statements("AAA", 2020, 2020)
    canonical = next(r for r in rows if r.get("_is_duplicate") is not True)
    dup = next(r for r in rows if r.get("_is_duplicate") is True)
    for k, v in canonical.items():
        if k == "_is_duplicate":
            continue
        assert dup[k] == v


def test_market_prices_also_receive_duplicates() -> None:
    adapter = VnstockFixtureAdapter(config=_enabled_config(duplication=DuplicationConfig(offline_rate=0.1, streaming_rate=0.015)))
    rows = adapter.fetch_market_prices("AAA", 2020, 2020)
    base = sum(1 for r in rows if r.get("_is_duplicate") is not True)
    dups = sum(1 for r in rows if r.get("_is_duplicate") is True)
    assert dups == int(0.1 * base)


def test_determinism_with_same_seed() -> None:
    cfg = _enabled_config()
    a = VnstockFixtureAdapter(config=cfg)
    b = VnstockFixtureAdapter(config=cfg)
    assert a.fetch_companies() == b.fetch_companies()
