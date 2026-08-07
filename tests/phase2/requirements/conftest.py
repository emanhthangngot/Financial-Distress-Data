"""Shared parsing helpers and matrix lookup for the requirement tests.

Mirrors `_parse_evidence_fields`/`EVIDENCE_REQUIRED_KEYS` in
scripts/audit_phase2_evidence.py (duplicated, not imported, to keep these
tests import-light — the auditor script itself is not a service dependency,
but importing it pulls in argparse/subprocess wiring these 60 subprocess
invocations don't need).
"""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
# Mirrors the auditor's --gitops-root: no baked assumption about a sibling
# checkout. PHASE2_GITOPS_ROOT overrides; unset, GITOPS_ROOT is None and every
# gitops-artifact case skips with an explicit "not checked out" reason instead
# of misreporting a missing checkout as a missing implementation artifact.
_gitops_env = os.environ.get("PHASE2_GITOPS_ROOT")
GITOPS_ROOT = Path(_gitops_env) if _gitops_env else None
MATRIX_PATH = REPO_ROOT / "docs" / "phase2" / "rubric-matrix.csv"

EVIDENCE_REQUIRED_KEYS = [
    "rubric_id",
    "execution_timestamp",
    "source_sha",
    "gitops_sha",
    "versions",
    "command",
    "expected_result",
    "actual_result",
    "redaction_status",
]


def _load_matrix() -> dict[str, dict[str, str]]:
    """rubric_id -> row, read fresh from the CSV so tests never bake stale data."""
    rows = csv.DictReader(MATRIX_PATH.read_text(encoding="utf-8").splitlines())
    return {row["rubric_id"]: row for row in rows}


MATRIX = _load_matrix()


def parse_evidence_fields(text: str) -> dict[str, str]:
    """Extract ``key: value`` metadata pairs from an evidence markdown file."""
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        match = re.match(r"^[-*]?\s*\**([a-z_]+)\**\s*:\s*(.*)$", stripped, re.IGNORECASE)
        if not match:
            continue
        key = match.group(1).strip().lower()
        if key in EVIDENCE_REQUIRED_KEYS:
            fields[key] = match.group(2).strip()
    return fields
