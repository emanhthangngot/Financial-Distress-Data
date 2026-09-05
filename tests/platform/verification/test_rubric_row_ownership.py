"""Rubric row ownership contract (plan phase-03-contracts-rubric.md, R-6/R-12).

Exercises scripts/verify_rubric_coverage.py against the real unified matrix
and against synthetic fixtures for each individual failure mode, so the
checker itself — not just today's matrix content — is proven correct.
"""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MATRIX_PATH = REPO_ROOT / "docs" / "rubric-matrix-unified.csv"

_spec = importlib.util.spec_from_file_location(
    "verify_rubric_coverage", REPO_ROOT / "scripts" / "verify_rubric_coverage.py"
)
_module = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_module)


_BASE_FIELDS = [
    "rubric_id",
    "track",
    "section",
    "points",
    "requirement",
    "proof",
    "deliverables",
    "owner",
    "test",
    "validation_command",
    "evidence_path",
    "evidence_type",
    "acceptance_id",
    "source_file",
    "source_row_index",
    "source_digest",
    "artifact_repo",
    "artifact_path",
    "behavioral_assertion",
    "owning_phase",
]


def _write_matrix(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "matrix.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_BASE_FIELDS)
        writer.writeheader()
        for row in rows:
            full = dict.fromkeys(_BASE_FIELDS, "x")
            full.update(row)
            writer.writerow(full)
    return path


def test_unified_matrix_has_161_rows_and_300_points() -> None:
    """AC-P3-1: structural shape is correct regardless of citation state."""
    with open(MATRIX_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 161
    assert sum(int(r["points"]) for r in rows) == 300
    assert len({r["rubric_id"] for r in rows}) == 161


def test_unified_matrix_mini_track_covers_required_phases() -> None:
    """AC-P3-2c: track=mini has at least one row in each of P2, P4, P5, P11."""
    with open(MATRIX_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    mini_phases = {r["owning_phase"] for r in rows if r["track"] == "mini"}
    assert {"P2", "P4", "P5", "P11"} <= mini_phases


def test_verifier_fails_on_missing_owning_phase(tmp_path: Path) -> None:
    matrix = _write_matrix(tmp_path, [{"rubric_id": "r1", "owning_phase": "", "points": "1"}])
    findings = _module.verify(matrix)
    assert any("missing required field 'owning_phase'" in f for f in findings)


def test_verifier_fails_on_owning_phase_outside_p2_p12(tmp_path: Path) -> None:
    matrix = _write_matrix(tmp_path, [{"rubric_id": "r1", "owning_phase": "P99", "points": "1"}])
    findings = _module.verify(matrix)
    assert any("outside P2-P12" in f for f in findings)


def test_verifier_fails_on_duplicate_rubric_id(tmp_path: Path) -> None:
    matrix = _write_matrix(
        tmp_path,
        [
            {"rubric_id": "dupe", "owning_phase": "P4", "points": "1"},
            {"rubric_id": "dupe", "owning_phase": "P4", "points": "1"},
        ],
    )
    findings = _module.verify(matrix)
    assert any("duplicate rubric_id" in f for f in findings)


def test_verifier_fails_on_uncited_rubric_id(tmp_path: Path) -> None:
    """R-12: a row that names a real owning phase but is never cited by that
    phase file's AC-P<n>-<m> lines must fail, not pass vacuously."""
    matrix = _write_matrix(
        tmp_path,
        [{"rubric_id": "definitely-not-a-real-citation-xyz", "owning_phase": "P4", "points": "1"}],
    )
    findings = _module.verify(matrix)
    assert any("not cited by any AC-P<n>-<m> line" in f for f in findings)


def test_verifier_passes_on_a_cited_row(tmp_path: Path) -> None:
    """Positive control: a rubric_id that genuinely appears next to an
    AC-P<n>-<m> marker in its owning phase file passes the citation check."""
    matrix = _write_matrix(
        tmp_path,
        [
            {
                "rubric_id": "AC-P2-1",
                "owning_phase": "P2",
                "points": "1",
                "track": "mini",
            }
        ],
    )
    findings = _module.verify(matrix)
    assert not any("not cited by any AC-P<n>-<m> line" in f for f in findings)
