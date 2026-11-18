"""
Rubric coverage verifier (plan phase-03-contracts-rubric.md, Steps 3 and 6).

Reads ``docs/rubric-matrix-unified.csv`` and fails closed on any of:

- a row missing ``owning_phase``, ``evidence_path``, ``validation_command``,
  or ``behavioral_assertion``
- an ``owning_phase`` outside ``P2``-``P12``
- ``track=mini`` missing coverage in any of P2, P4, P5, P11 (R-12, AC-P3-2c)
- a ``rubric_id`` not cited by an ``AC-P<n>-<m>`` line in its owning phase
  file (R-12, AC-P3-2b) — the check that catches "owned but no assertion",
  which the audit found is the same defect as being unowned

Exits 0 with a summary when every check passes; exits 1 and prints every
finding otherwise.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = REPO_ROOT / "docs" / "rubric-matrix-unified.csv"
PLAN_DIR = REPO_ROOT / "plans" / "260831-1644-rebuild-target-mlops-architecture"

REQUIRED_MINI_PHASES = {"P2", "P4", "P5", "P11"}
VALID_PHASE_RE = re.compile(r"^P(\d{1,2})$")
REQUIRED_NONEMPTY_FIELDS = (
    "owning_phase",
    "evidence_path",
    "validation_command",
    "behavioral_assertion",
)


def _load_matrix(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _phase_file_for(owning_phase: str) -> Path | None:
    match = VALID_PHASE_RE.match(owning_phase.strip())
    if not match:
        return None
    number = int(match.group(1))
    candidates = list(PLAN_DIR.glob(f"phase-{number:02d}-*.md"))
    return candidates[0] if candidates else None


def _ac_line_ids(text: str) -> set[str]:
    """Return every rubric_id-shaped token appearing on an AC-P<n>-<m> line."""
    ids: set[str] = set()
    for line in text.splitlines():
        if not re.search(r"\bAC-P\d+-\w+\b", line):
            continue
        ids.add(line)
    return ids


def verify(matrix_path: Path = MATRIX_PATH) -> list[str]:
    findings: list[str] = []
    if not matrix_path.is_file():
        return [f"💀 {matrix_path} not found"]

    rows = _load_matrix(matrix_path)
    seen_ids: set[str] = set()
    duplicate_ids: set[str] = set()
    for row in rows:
        rid = row.get("rubric_id", "")
        if rid in seen_ids:
            duplicate_ids.add(rid)
        seen_ids.add(rid)
    if duplicate_ids:
        findings.append(f"duplicate rubric_id values: {sorted(duplicate_ids)}")

    total_points = 0
    mini_phases: set[str] = set()
    phase_file_cache: dict[str, str] = {}

    for row in rows:
        rid = row.get("rubric_id", "?")
        owning_phase = row.get("owning_phase", "").strip()

        for field in REQUIRED_NONEMPTY_FIELDS:
            if not row.get(field, "").strip():
                findings.append(f"{rid}: missing required field {field!r}")

        if owning_phase and not VALID_PHASE_RE.match(owning_phase):
            findings.append(f"{rid}: owning_phase {owning_phase!r} is not in P2-P12 form")
        elif owning_phase:
            number = int(VALID_PHASE_RE.match(owning_phase).group(1))
            if not (2 <= number <= 12):
                findings.append(f"{rid}: owning_phase {owning_phase!r} is outside P2-P12")

        try:
            total_points += int(row.get("points", "0") or "0")
        except ValueError:
            findings.append(f"{rid}: points {row.get('points')!r} is not an integer")

        if row.get("track") == "mini" and owning_phase:
            mini_phases.add(owning_phase)

        # AC-citation check (R-12): the rubric_id must appear on a line in the
        # owning phase file that also carries an AC-P<n>-<m> marker.
        if owning_phase:
            phase_file = _phase_file_for(owning_phase)
            if phase_file is None:
                findings.append(f"{rid}: no phase file found for owning_phase {owning_phase!r}")
            else:
                cache_key = str(phase_file)
                if cache_key not in phase_file_cache:
                    phase_file_cache[cache_key] = phase_file.read_text(
                        encoding="utf-8", errors="replace"
                    )
                text = phase_file_cache[cache_key]
                ac_lines = _ac_line_ids(text)
                cited = any(rid in line for line in ac_lines)
                if not cited:
                    findings.append(
                        f"{rid}: not cited by any AC-P<n>-<m> line in {phase_file.name}"
                    )

    if total_points != 300:
        findings.append(f"points sum to {total_points}, expected 300")

    if len(rows) != 161:
        findings.append(f"matrix has {len(rows)} rows, expected 161")

    missing_mini_phases = REQUIRED_MINI_PHASES - mini_phases
    if missing_mini_phases:
        findings.append(
            f"track=mini has zero rows in required phase(s): {sorted(missing_mini_phases)}"
        )

    return findings


def main() -> int:
    findings = verify()
    if findings:
        for finding in findings:
            print(finding)
        print(f"\n{len(findings)} finding(s) — FAIL")
        return 1
    print("Rubric coverage: 161 rows, 300 points, 0 findings — PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
