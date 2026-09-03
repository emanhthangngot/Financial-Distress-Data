"""Typed configuration for deterministic platform .rift scenarios.

Mirrors ``src/generator/config.py``'s style (frozen dataclasses, strict
unknown/missing-key validation) without importing it — platform .ust not
couple to a platform .rivate helper (AGENTS.md; judgment call recorded in
``plans/260802-1037-unified-phase2-ml-llm-gitops/phase-04-implementation-notes.md``,
section 6).
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, TypeVar

import yaml

T = TypeVar("T")

_VALID_SHIFT_MODES = {"multiplicative", "additive"}
_VALID_STATS = {"mean", "std"}
_VALID_DIRECTIONS = {"increase", "decrease"}

# Registry of derived per-row metrics a scenario may target. Keeping this in
# generator_config.py (not generator.py) lets validate() reject an unknown
# target_metric at config-load time instead of failing deep inside a run.
DERIVED_METRIC_NAMES = {"debt_to_asset", "close_price"}


def _validate_rate(name: str, value: float) -> None:
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be within [0, 1], got {value!r}")


@dataclass(frozen=True)
class ShiftSpec:
    mode: str
    magnitude: float

    def validate(self) -> None:
        if self.mode not in _VALID_SHIFT_MODES:
            raise ValueError(
                f"shift mode must be one of {sorted(_VALID_SHIFT_MODES)}, got {self.mode!r}"
            )


@dataclass(frozen=True)
class DriftScenario:
    name: str
    seed: int
    start_quarter: int
    affected_fraction: float
    feature_shifts: dict[str, ShiftSpec]
    target_metric: str
    observed_stat: str
    expected_direction: str
    threshold: float

    def validate(self) -> None:
        if self.start_quarter < 1:
            raise ValueError("start_quarter must be positive")
        _validate_rate("affected_fraction", self.affected_fraction)
        if not self.feature_shifts:
            raise ValueError(f"scenario {self.name!r} must declare at least one feature_shift")
        for feature, shift in self.feature_shifts.items():
            if not feature:
                raise ValueError(f"scenario {self.name!r} has an empty feature_shifts key")
            shift.validate()
        if self.target_metric not in DERIVED_METRIC_NAMES:
            raise ValueError(
                f"target_metric must be one of {sorted(DERIVED_METRIC_NAMES)}, "
                f"got {self.target_metric!r}"
            )
        if self.observed_stat not in _VALID_STATS:
            raise ValueError(
                f"observed_stat must be one of {sorted(_VALID_STATS)}, got {self.observed_stat!r}"
            )
        if self.expected_direction not in _VALID_DIRECTIONS:
            raise ValueError(
                f"expected_direction must be one of {sorted(_VALID_DIRECTIONS)}, "
                f"got {self.expected_direction!r}"
            )
        if self.threshold <= 0:
            raise ValueError("threshold must be positive")


@dataclass(frozen=True)
class DriftConfig:
    schema_version: int
    scenarios: dict[str, DriftScenario]

    def validate(self) -> None:
        if self.schema_version != 1:
            raise ValueError(f"unsupported drift config schema_version {self.schema_version}")
        if not self.scenarios:
            raise ValueError("drift config must declare at least one scenario")
        for scenario in self.scenarios.values():
            scenario.validate()


def _typed(cls: type[T], payload: dict[str, Any], label: str) -> T:
    known = {f.name for f in fields(cls)}
    unknown = set(payload) - known
    if unknown:
        raise ValueError(f"unknown key(s) in {label}: {sorted(unknown)}")
    missing = known - set(payload)
    if missing:
        raise ValueError(f"missing key(s) in {label}: {sorted(missing)}")
    return cls(**payload)


def _load_feature_shifts(raw: dict[str, Any], scenario_name: str) -> dict[str, ShiftSpec]:
    return {
        feature: _typed(ShiftSpec, spec, f"{scenario_name}.feature_shifts.{feature}")
        for feature, spec in raw.items()
    }


def load_drift_config(path: str | Path) -> DriftConfig:
    """Load and validate ``configs/drift-config.yaml``."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("drift config must be a mapping")
    scenarios: dict[str, DriftScenario] = {}
    for scenario_name, scenario_raw in raw.get("scenarios", {}).items():
        payload = dict(scenario_raw)
        payload["name"] = scenario_name
        payload["feature_shifts"] = _load_feature_shifts(
            payload.pop("feature_shifts", {}), scenario_name
        )
        scenarios[scenario_name] = _typed(DriftScenario, payload, f"scenarios.{scenario_name}")
    config = DriftConfig(schema_version=raw.get("schema_version", 1), scenarios=scenarios)
    config.validate()
    return config


def get_scenario(config: DriftConfig, scenario: str) -> DriftScenario:
    if scenario not in config.scenarios:
        raise KeyError(f"unknown drift scenario {scenario!r}; known: {sorted(config.scenarios)}")
    return config.scenarios[scenario]
