"""W12 single-source-of-truth invariants for sector exclusion.

These tests are RED until ``configs/sector_exclusion.yaml`` becomes the only
source of truth and ``src/transforms/compute_distress_labels.is_financial_sector``
reads it at call time via ``src.transforms.sector_policy.load_sector_policy``.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
YAML_PATH = REPO_ROOT / "configs" / "sector_exclusion.yaml"

EXPECTED_TERMS_LOWER = frozenset(
    {
        "banks",
        "insurance",
        "securities",
        "diversified financials",
        "financial services",
    }
)
EXPECTED_CODES = frozenset({"40", "4010", "4020", "4030"})


def _load_helper():
    """Import the helper. ImportError is what makes this test RED pre-W12."""
    from src.transforms.sector_policy import load_sector_policy

    return load_sector_policy


def test_load_sector_policy_returns_yaml_contents() -> None:
    """The helper must return terms (lowercased) and codes that match the YAML."""
    load_sector_policy = _load_helper()
    policy = load_sector_policy()

    assert hasattr(policy, "terms"), "policy must expose .terms"
    assert hasattr(policy, "codes"), "policy must expose .codes"
    assert hasattr(policy, "policy"), "policy must expose .policy dict"

    assert policy.terms == EXPECTED_TERMS_LOWER, (
        f"Expected terms to be {EXPECTED_TERMS_LOWER!r}, got {policy.terms!r}"
    )
    assert policy.codes == EXPECTED_CODES, (
        f"Expected codes to be {EXPECTED_CODES!r}, got {policy.codes!r}"
    )
    assert policy.policy.get("excluded_reason") == "financial_sector_excluded"


def test_no_inline_financial_constants_in_src() -> None:
    """After refactor, no src/ module may define the literal sets by name."""
    import re

    src_dir = REPO_ROOT / "src"
    pattern = re.compile(r"^FINANCIAL_SECTOR_TERMS\s*=", re.M)
    pattern2 = re.compile(r"^FINANCIAL_GICS_CODES\s*=", re.M)
    hits: list[str] = []
    for py_path in src_dir.rglob("*.py"):
        text = py_path.read_text(encoding="utf-8")
        for sym, pat in (("FINANCIAL_SECTOR_TERMS", pattern), ("FINANCIAL_GICS_CODES", pattern2)):
            if pat.search(text):
                hits.append(f"{py_path.relative_to(REPO_ROOT)}: {sym}")

    assert not hits, (
        "src/ still defines FINANCIAL_SECTOR_TERMS / FINANCIAL_GICS_CODES: " + ", ".join(hits)
    )


def test_is_financial_sector_reads_yaml_at_call_time() -> None:
    """is_financial_sector must read the YAML at call time, not import time.

    We assert this by mutating the YAML to a new term, calling the function,
    and observing the new term is now matched. Then we restore the YAML.
    """
    import yaml

    from src.transforms.compute_distress_labels import is_financial_sector

    original_text = YAML_PATH.read_text(encoding="utf-8")
    original_data = yaml.safe_load(original_text)
    try:
        mutated = {
            **original_data,
            "z_score_excluded_sectors": ["TimeW12MarkerSector"],
            "z_score_excluded_gics": ["99"],
        }
        YAML_PATH.write_text(yaml.safe_dump(mutated), encoding="utf-8")

        row = {"sector": "timew12markersector", "gics_sector_code": "99"}
        assert is_financial_sector(row) is True, (
            "is_financial_sector must reflect YAML changes at call time"
        )

        non_match_row = {"sector": "Industrials", "gics_sector_code": "20"}
        assert is_financial_sector(non_match_row) is False
    finally:
        YAML_PATH.write_text(original_text, encoding="utf-8")
