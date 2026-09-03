"""Pins M4: the sql/ carve-out for the new Phase 2 file must not widen the
Phase 1 protected-path gate for anything else under sql/."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location(
    "audit_platform_evidence", REPO_ROOT / "scripts" / "audit_platform_evidence.py"
)
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault("audit_platform_evidence", _MODULE)
_SPEC.loader.exec_module(_MODULE)  # type: ignore[union-attr]

_phase1_mutation_from_changed = _MODULE._phase1_mutation_from_changed


def test_new_ml_metadata_sql_is_not_flagged() -> None:
    assert _phase1_mutation_from_changed(["sql/init_ml.sql"]) == []


def test_phase1_project_metadata_sql_is_still_flagged() -> None:
    errors = _phase1_mutation_from_changed(["sql/init_ops.sql"])
    assert errors and "sql/" in errors[0]


def test_unrelated_new_sql_file_is_still_flagged() -> None:
    """A carve-out scoped to one filename, not the whole sql/ tree."""
    errors = _phase1_mutation_from_changed(["sql/some_other_new_file.sql"])
    assert errors and "sql/" in errors[0]
