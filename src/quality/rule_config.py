"""Validated loader for executable data-quality rule configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class DQRule:
    """One configured DQ rule and its execution parameters."""

    name: str
    type: str
    severity: str
    parameters: dict[str, Any]


def load_dq_rule_config(path: str | Path) -> dict[str, list[DQRule]]:
    """Load critical and warning rules, rejecting incomplete rule definitions."""
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    output: dict[str, list[DQRule]] = {}
    for severity in ("critical", "warning"):
        output[severity] = []
        for raw in payload.get(severity, []):
            if not raw.get("name") or not raw.get("type"):
                raise ValueError(f"DQ rule in {severity} must define name and type")
            output[severity].append(
                DQRule(
                    name=raw["name"],
                    type=raw["type"],
                    severity=severity,
                    parameters=dict(raw.get("parameters", {})),
                )
            )
    return output
