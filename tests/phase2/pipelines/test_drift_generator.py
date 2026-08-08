"""Pins src/drift/generator.py: deterministic seeded output, observed
direction matches configured direction, PSI crosses threshold, unaffected
fraction stays unchanged, and the real shipped config passes against the
real generator output (not just synthetic literals)."""

from __future__ import annotations

import json
from pathlib import Path

from src.drift.generator import apply_drift, build_drift_report, write_drift_report
from src.drift.generator_config import (
    DERIVED_METRIC_NAMES,
    DriftScenario,
    ShiftSpec,
    get_scenario,
    load_drift_config,
)
from src.generator.config import load_generator_config
from src.generator.offline import generate_offline_data

REPO_ROOT = Path(__file__).resolve().parents[3]
DRIFT_CONFIG_PATH = REPO_ROOT / "configs" / "drift-config.yaml"
GENERATOR_CONFIG_PATH = REPO_ROOT / "configs" / "generator-config.yaml"

FINANCIAL_DETERIORATION = DriftScenario(
    name="financial_deterioration",
    seed=4001,
    start_quarter=2,
    affected_fraction=0.5,
    feature_shifts={
        "total_liabilities": ShiftSpec(mode="multiplicative", magnitude=0.30),
    },
    target_metric="debt_to_asset",
    observed_stat="mean",
    expected_direction="increase",
    threshold=0.10,
)

MARKET_STRESS = DriftScenario(
    name="market_stress",
    seed=4002,
    start_quarter=1,
    affected_fraction=0.6,
    feature_shifts={
        "close_price": ShiftSpec(mode="multiplicative", magnitude=0.60),
    },
    target_metric="close_price",
    observed_stat="std",
    expected_direction="increase",
    threshold=0.05,
)


def _statement_rows(n: int = 40) -> list[dict]:
    return [
        {
            "ticker": f"G{i:04d}",
            "report_period": "2026Q2",
            "total_assets": 1_000_000 + i * 1000,
            "total_liabilities": 500_000 + i * 500,
        }
        for i in range(n)
    ]


def _price_rows(n: int = 40) -> list[dict]:
    return [{"ticker": f"G{i:04d}", "close_price": 50.0 + i} for i in range(n)]


def test_derived_metrics_registry_matches_config_module() -> None:
    """Pins M5: a target_metric name accepted by config validation must
    always resolve in generator.py — checked at generator import time via
    the module-level assert, exercised here by simply importing it."""
    from src.drift import generator

    assert set(generator._DERIVED_METRICS) == DERIVED_METRIC_NAMES


def test_apply_drift_is_deterministic_across_two_runs() -> None:
    rows = _statement_rows()
    first = apply_drift(rows, FINANCIAL_DETERIORATION)
    second = apply_drift(rows, FINANCIAL_DETERIORATION)
    assert first.rows == second.rows
    assert first.affected_tickers == second.affected_tickers


def test_apply_drift_leaves_unaffected_tickers_unchanged() -> None:
    rows = _statement_rows()
    drifted = apply_drift(rows, FINANCIAL_DETERIORATION)
    by_ticker = {row["ticker"]: row for row in rows}
    for row in drifted.rows:
        if row["ticker"] not in drifted.affected_tickers:
            assert row == by_ticker[row["ticker"]]


def test_apply_drift_shifts_only_affected_tickers_feature() -> None:
    rows = _statement_rows()
    drifted = apply_drift(rows, FINANCIAL_DETERIORATION)
    by_ticker = {row["ticker"]: row for row in rows}
    changed = [
        row["ticker"]
        for row in drifted.rows
        if row["total_liabilities"] != by_ticker[row["ticker"]]["total_liabilities"]
    ]
    assert set(changed) == drifted.affected_tickers
    assert 0 < len(drifted.affected_tickers) < len(rows)


def test_financial_deterioration_observed_direction_matches_configured() -> None:
    rows = _statement_rows()
    drifted = apply_drift(rows, FINANCIAL_DETERIORATION)
    report = build_drift_report(rows, drifted.rows, FINANCIAL_DETERIORATION)
    assert report["observed_direction"] == "increase"
    assert report["configured_direction"] == "increase"
    assert report["passed"] is True
    assert report["psi"] > 0


def test_market_stress_observed_direction_matches_configured() -> None:
    rows = _price_rows()
    drifted = apply_drift(rows, MARKET_STRESS)
    report = build_drift_report(rows, drifted.rows, MARKET_STRESS)
    assert report["observed_direction"] == "increase"  # cross-sectional stdev widens
    assert report["passed"] is True


def test_ramp_gates_rows_before_start_quarter() -> None:
    scenario = DriftScenario(
        name="gated",
        seed=1,
        start_quarter=3,
        affected_fraction=1.0,
        feature_shifts={"total_liabilities": ShiftSpec(mode="multiplicative", magnitude=0.5)},
        target_metric="debt_to_asset",
        observed_stat="mean",
        expected_direction="increase",
        threshold=0.01,
    )
    rows = [
        {
            "ticker": "G0000",
            "report_period": "2026Q1",
            "total_assets": 100,
            "total_liabilities": 50,
        },
        {
            "ticker": "G0000",
            "report_period": "2026Q3",
            "total_assets": 100,
            "total_liabilities": 50,
        },
    ]
    drifted = apply_drift(rows, scenario)
    q1_row, q3_row = drifted.rows
    assert q1_row["total_liabilities"] == 50  # before start_quarter: unchanged
    assert q3_row["total_liabilities"] != 50  # at/after start_quarter: shifted


def test_write_drift_report_writes_json_and_markdown(tmp_path) -> None:
    rows = _statement_rows()
    drifted = apply_drift(rows, FINANCIAL_DETERIORATION)
    report = build_drift_report(rows, drifted.rows, FINANCIAL_DETERIORATION)
    directory = write_drift_report(report, "# md", run_id="run-1", output_root=tmp_path)
    assert (directory / "report.json").is_file()
    assert (directory / "report.md").read_text(encoding="utf-8") == "# md"
    assert json.loads((directory / "report.json").read_text(encoding="utf-8"))["scenario"] == (
        "financial_deterioration"
    )


def test_shipped_config_passes_against_real_ci_generator_output() -> None:
    """Pins H3: the exact scenarios in configs/drift-config.yaml (not
    synthetic literals) must clear their own threshold against the real
    src.generator.offline.generate_offline_data ci-profile output — this is
    what scripts/run_phase2_drift_report.py runs as evidence."""
    drift_config = load_drift_config(DRIFT_CONFIG_PATH)
    generator_config = load_generator_config(GENERATOR_CONFIG_PATH, profile="ci")
    offline_data = generate_offline_data(generator_config)

    for scenario_name, dataset in (
        ("financial_deterioration", offline_data.financial_statements),
        ("market_stress", offline_data.market_prices),
    ):
        scenario = get_scenario(drift_config, scenario_name)
        drifted = apply_drift(dataset, scenario)
        report = build_drift_report(dataset, drifted.rows, scenario)
        assert report["observed_direction"] == scenario.expected_direction, scenario_name
        assert report["passed"] is True, (scenario_name, report)
