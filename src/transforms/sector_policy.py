"""Single source of truth loader for sector exclusion policy.

The financial-sector exclusion list (sector terms + GICS codes + policy block)
lives in ``configs/sector_exclusion.yaml``. This module exposes a frozen
dataclass view of that file. Callers (notably ``compute_distress_labels``)
must invoke ``load_sector_policy()`` at call time so that runtime changes
to the YAML are reflected without an import-time cache.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "sector_exclusion.yaml"


@dataclass(frozen=True)
class SectorPolicy:
    """Frozen view of the sector exclusion config.

    Attributes
    ----------
    terms:
        Lower-cased sector / industry text values that exclude a company.
    codes:
        GICS sector codes (top-2 or full) that exclude a company.
    policy:
        The free-form ``policy`` block from the YAML, kept as a dict so
        downstream code can add new fields without changing this loader.
    """

    terms: frozenset[str]
    codes: frozenset[str]
    policy: dict = field(default_factory=dict)


def load_sector_policy(config_path: Path | None = None) -> SectorPolicy:
    """Load sector exclusion policy from YAML.

    Parameters
    ----------
    config_path:
        Optional override for the YAML path. Defaults to the in-repo
        ``configs/sector_exclusion.yaml``.
    """
    path = config_path if config_path is not None else _CONFIG_PATH
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    raw_terms = data.get("z_score_excluded_sectors", []) or []
    raw_codes = data.get("z_score_excluded_gics", []) or []
    policy_block = data.get("policy", {}) or {}

    terms = frozenset(str(t).strip().lower() for t in raw_terms if str(t).strip())
    codes = frozenset(str(c).strip() for c in raw_codes if str(c).strip())

    return SectorPolicy(terms=terms, codes=codes, policy=dict(policy_block))
