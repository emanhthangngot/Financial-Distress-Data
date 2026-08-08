"""Pins src/drift/generator_config.py: loading, strict validation, both
configured scenarios present."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.drift.generator_config import (
    DriftConfig,
    ShiftSpec,
    get_scenario,
    load_drift_config,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO_ROOT / "configs" / "drift-config.yaml"


def test_loads_real_config_with_both_scenarios() -> None:
    config = load_drift_config(CONFIG_PATH)
    assert set(config.scenarios) == {"financial_deterioration", "market_stress"}


def test_scenario_fields_are_typed() -> None:
    config = load_drift_config(CONFIG_PATH)
    scenario = get_scenario(config, "financial_deterioration")
    assert scenario.seed == 4001
    assert scenario.expected_direction == "increase"
    assert isinstance(scenario.feature_shifts["total_liabilities"], ShiftSpec)


def test_get_scenario_rejects_unknown_name() -> None:
    config = load_drift_config(CONFIG_PATH)
    with pytest.raises(KeyError):
        get_scenario(config, "does_not_exist")


def test_rejects_unknown_top_level_key(tmp_path: Path) -> None:
    bad = tmp_path / "drift.yaml"
    bad.write_text(
        """
schema_version: 1
scenarios:
  s1:
    seed: 1
    start_quarter: 1
    affected_fraction: 0.1
    feature_shifts:
      close_price:
        mode: multiplicative
        magnitude: 0.1
    target_metric: close_price
    observed_stat: std
    expected_direction: increase
    threshold: 0.1
    unexpected_key: true
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown key"):
        load_drift_config(bad)


def test_rejects_missing_threshold(tmp_path: Path) -> None:
    bad = tmp_path / "drift.yaml"
    bad.write_text(
        """
schema_version: 1
scenarios:
  s1:
    seed: 1
    start_quarter: 1
    affected_fraction: 0.1
    feature_shifts:
      close_price:
        mode: multiplicative
        magnitude: 0.1
    target_metric: close_price
    observed_stat: std
    expected_direction: increase
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing key"):
        load_drift_config(bad)


@pytest.mark.parametrize("magnitude", [-0.1, 1.5])
def test_rejects_out_of_range_affected_fraction(tmp_path: Path, magnitude: float) -> None:
    bad = tmp_path / "drift.yaml"
    bad.write_text(
        f"""
schema_version: 1
scenarios:
  s1:
    seed: 1
    start_quarter: 1
    affected_fraction: {magnitude}
    feature_shifts:
      close_price:
        mode: multiplicative
        magnitude: 0.1
    target_metric: close_price
    observed_stat: std
    expected_direction: increase
    threshold: 0.1
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="affected_fraction"):
        load_drift_config(bad)


def test_config_validate_rejects_empty_scenarios() -> None:
    with pytest.raises(ValueError, match="at least one scenario"):
        DriftConfig(schema_version=1, scenarios={}).validate()
