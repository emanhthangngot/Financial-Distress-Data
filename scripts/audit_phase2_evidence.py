#!/usr/bin/env python3
"""Phase 2 evidence auditor — rubric-matrix linter and evidence validator.

Usage:
  python scripts/audit_phase2_evidence.py --matrix-only --strict
  python scripts/audit_phase2_evidence.py --matrix-only --matrix PATH
  python scripts/audit_phase2_evidence.py --require-executed --ml 100 --llm 100

Modes:
  --matrix-only     Validate the rubric-matrix.csv completeness and integrity
                    (phase-01). Checks that every scored row exists with the
                    required fields (including the reproducible `test` command
                    and a role-based owner), both tracks total the expected
                    points, every role owns at least one row, and no Phase 1
                    contract mutation is referenced.
  --matrix PATH     Audit a specific rubric-matrix CSV (fixture-based tests).
  --strict          With --matrix-only: fail (exit 1) on any issue. Without it,
                    warnings still exit 0 (used during phase-01 bring-up).
  --require-executed  Phase-08 promotion gate: every row must record executed
                      evidence and its file must exist on disk and satisfy the
                      evidence contract (rubric_id, execution_timestamp,
                      source_sha, gitops_sha, versions, command,
                      expected/actual result and redaction_status). Values must
                      be non-empty and format-valid (ISO-8601 timestamps, git
                      SHAs/refs). Rows still marked design_only/stretch, and
                      executed rows whose implementation artifact
                      (artifact_path) is absent, fail the gate.

Exit codes:
  0  all checks passed
  1  matrix/evidence errors found (strict mode or phase-08 mode)
  2  script crashed / CSV unreadable
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PHASE1_PROTECTED = [
    "src/collectors/",
    "src/transforms/",
    "src/quality/",
    "src/catalog/",
    "src/metadata/",
    "src/streaming/",
    "src/generator/",
    "dags/",
    "sql/",
    "docs/evidence/",
    "docs/mini_coursework.md",
    "docs/01_data_generator.md",
    "docs/02_schema_design.md",
]

REQUIRED_DOCS = [
    "docs/phase2/requirements.md",
    "docs/phase2/architecture.md",
    "docs/phase2/evidence-contract.md",
    "docs/phase2/low-level-design.md",
    "docs/phase2/novel-ideas.md",
]

VALID_EVIDENCE_TYPES = {"executed", "design_only", "stretch"}
VALID_OWNERS = {"ml_engineer", "llm_engineer", "data_engineer", "platform_operator"}

# Phase 2 implementation roots declared in docs/phase2/requirements.md section 2.
# Every rubric row's artifact_path must live under exactly one of these roots so
# the "exact implementation" a reviewer needs is findable without inference.
ARTIFACT_ROOTS = ("src/ml/", "src/drift/", "src/llm/", "src/agents/", "apps/")

# Per-artifact metadata required by docs/phase2/evidence-contract.md. A file
# that exists but lacks any of these cannot prove a rubric point.
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


def _read_matrix(matrix_path: Path | None = None) -> list[dict[str, str]] | None:
    """Return matrix rows or None if the CSV is unreadable/missing."""
    path = matrix_path or (REPO_ROOT / "docs" / "phase2" / "rubric-matrix.csv")
    if not path.exists():
        return None
    try:
        reader = csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))
        return [dict(r) for r in reader if r]
    except Exception as exc:  # pragma: no cover - defensive
        print(f"💀 Could not read matrix CSV: {exc}")
        return None


def _audit_matrix(
    matrix: list[dict[str, str]],
    expected: dict[str, int],
    enforce_evidence_prefix: bool = True,
) -> list[str]:
    errors: list[str] = []

    # 1. Every scored row has required fields
    required = [
        "rubric_id",
        "track",
        "points",
        "requirement",
        "proof",
        "deliverables",
        "owner",
        "test",
        "evidence_path",
        "evidence_type",
        "artifact_path",
    ]
    totals: dict[str, int] = {"ML": 0, "LLM": 0}
    seen: set[str] = set()
    owners_seen: set[str] = set()
    for row in matrix:
        rid = row.get("rubric_id", "?")
        track = row.get("track", "")
        try:
            points = int(row.get("points", "0") or 0)
        except ValueError:
            points = 0
            errors.append(f"{rid}: points '{row.get('points')}' is not an integer")

        if rid in seen:
            errors.append(f"{rid}: duplicate rubric_id")
        seen.add(rid)

        for field in required:
            if not row.get(field, "").strip():
                errors.append(f"{rid}: missing '{field}'")

        etype = row.get("evidence_type", "")
        if etype not in VALID_EVIDENCE_TYPES:
            errors.append(f"{rid}: evidence_type '{etype}' invalid")

        owner = row.get("owner", "")
        if owner and owner not in VALID_OWNERS:
            errors.append(f"{rid}: owner '{owner}' not a recognized role")
        if owner:
            owners_seen.add(owner)

        epath = row.get("evidence_path", "")
        if epath and enforce_evidence_prefix and not epath.startswith("docs/phase2/evidence/"):
            errors.append(f"{rid}: evidence_path '{epath}' not under docs/phase2/evidence/")

        apath = row.get("artifact_path", "")
        if apath and not apath.startswith(ARTIFACT_ROOTS):
            errors.append(
                f"{rid}: artifact_path '{apath}' not under an allowed Phase 2 root "
                f"{ARTIFACT_ROOTS}"
            )
        elif apath and not apath.endswith(rid):
            errors.append(f"{rid}: artifact_path '{apath}' must end with the rubric_id")

        if re.search(r"row[-_]?\d+$", rid):
            errors.append(f"{rid}: ID looks like a spreadsheet line number, use semantic slug")

        if track in totals:
            totals[track] += points

    # Every role must own at least one scored row (locked taxonomy)
    for role in VALID_OWNERS:
        if role not in owners_seen:
            errors.append(f"owner '{role}' owns no scored row in the rubric matrix")

    # 2. Totals
    for track, exp in expected.items():
        if totals.get(track, 0) != exp:
            errors.append(f"{track}: total points = {totals.get(track, 0)}, expected {exp}")

    return errors


def _audit_phase1_no_mutation(matrix: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    blob = "\n".join(",".join(row.values()) for row in matrix).lower()
    for path in PHASE1_PROTECTED:
        if path.lower() in blob:
            errors.append(f"Matrix references Phase 1 protected path '{path}'")
    return errors


def _phase1_mutation_from_changed(changed: list[str]) -> list[str]:
    """Return errors when a git diff touches Phase 1 protected paths.

    `changed` is a list of repo-relative paths (e.g. from `git diff --name-only`).
    The working tree or branch must not modify Phase 1 collectors, transforms,
    quality, catalog, metadata, streaming, generator, dags, sql, or their docs.
    """
    errors: list[str] = []
    for path in PHASE1_PROTECTED:
        if any(entry == path or entry.startswith(path) for entry in changed):
            errors.append(f"Git diff modifies Phase 1 protected path '{path}'")
    return errors


def _audit_phase1_git_diff(base: str) -> list[str]:
    """Run the Phase 1 no-mutation gate and fail closed when unverifiable.

    Compares the working tree against ``<base>`` (default ``origin/dev``) and
    also lists untracked files, because ``git diff --name-only`` never reports
    brand-new files. A Phase 1 path touched by *either* source is a failure.

    Fail-closed: if the baseline cannot be resolved (missing ref, git error,
    non-zero exit) the gate returns an error instead of silently passing, so an
    unverifiable baseline never turns the mutation check into a no-op.
    """
    import subprocess

    changed: list[str] = []
    try:
        diff = subprocess.run(
            ["git", "diff", "--name-only", base],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - env dependent
        return [f"git check failed: baseline '{base}' unverifiable ({exc})"]
    if diff.returncode != 0:
        detail = next((ln.strip() for ln in (diff.stderr or "").splitlines() if ln.strip()), "")
        return [f"git check failed: baseline '{base}' unresolvable — {detail}"]
    changed.extend(line.strip() for line in diff.stdout.splitlines() if line.strip())

    try:
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - env dependent
        return [f"git check failed: untracked listing unavailable ({exc})"]
    if untracked.returncode != 0:
        lines = (untracked.stderr or "").splitlines()
        detail = next((ln.strip() for ln in lines if ln.strip()), "")
        return [f"git check failed: untracked listing errored — {detail}"]
    changed.extend(line.strip() for line in untracked.stdout.splitlines() if line.strip())

    return _phase1_mutation_from_changed(changed)


def _audit_required_docs() -> list[str]:
    errors: list[str] = []
    for rel in REQUIRED_DOCS:
        if not (REPO_ROOT / rel).exists():
            errors.append(f"Missing required doc: {rel}")
    return errors


def _parse_evidence_fields(text: str) -> dict[str, str]:
    """Extract ``key: value`` metadata pairs from an evidence markdown file.

    Accepts common evidence layouts:
      ``rubric_id: ML-...``
      ``- **execution_timestamp:** 2026-08-02T12:00:00Z``
      ``* source_sha: 0f1a...``

    Keys are lowercased; values are stripped and may be empty. Only the keys
    named by :data:`EVIDENCE_REQUIRED_KEYS` are returned so the audit is
    exactly the contract, nothing more.
    """
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        # Optional bullet, optional markdown bold on the key.
        match = re.match(r"^[-*]?\s*\**([a-z_]+)\**\s*:\s*(.*)$", stripped, re.IGNORECASE)
        if not match:
            continue
        key = match.group(1).strip().lower()
        if key in EVIDENCE_REQUIRED_KEYS:
            fields[key] = match.group(2).strip()
    return fields


def _is_iso_timestamp(value: str) -> bool:
    """True when the value is a parseable ISO-8601 timestamp."""
    from datetime import datetime

    candidate = value.strip().replace("Z", "+00:00")
    try:
        datetime.fromisoformat(candidate)
    except ValueError:
        return False
    return True


def _is_git_sha_or_ref(value: str) -> bool:
    """True for a full 40-hex SHA, a short (>=7 hex) SHA, or a plausible ref."""
    v = value.strip()
    if re.fullmatch(r"[0-9a-f]{40}", v):
        return True
    if re.fullmatch(r"[0-9a-f]{7,40}", v):
        return True
    # Ref-like: HEAD, main, refs/heads/main, v1.2.3, origin/dev.
    return bool(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._/-]*", v))


# Format validators per evidence-contract field. Keys not listed only need a
# non-empty value (they are free-form text).
EVIDENCE_FORMAT_VALIDATORS: dict[str, callable] = {
    "execution_timestamp": _is_iso_timestamp,
    "source_sha": _is_git_sha_or_ref,
    "gitops_sha": _is_git_sha_or_ref,
}


def _audit_executed(matrix: list[dict[str, str]]) -> list[str]:
    """Phase-08: every row must carry executed evidence satisfying the contract.

    `--require-executed` is the phase-08 promotion gate: a row recorded as
    design_only or stretch has *not* been executed and cannot claim a rubric
    point, so it is a failure. For every executed row the evidence file must
    exist, reference its rubric_id, carry every metadata key from
    docs/phase2/evidence-contract.md with a *non-empty* value, and satisfy the
    per-field format contract (ISO-8601 timestamp, git SHAs/refs, a
    reproduction command, and expected/actual results). A design claimed as
    executed but recorded as a mere placeholder — keys present but values
    blank, or formats that cannot be real — is a failure.

    Additionally, an executed row must name an exact implementation artifact
    (artifact_path) that exists on disk: phase-08 proves a running system, not
    a reserved directory.
    """
    errors: list[str] = []
    for row in matrix:
        rid = row.get("rubric_id", "?")
        epath = row.get("evidence_path", "")
        etype = row.get("evidence_type", "")
        if etype != "executed":
            errors.append(
                f"{rid}: evidence_type '{etype}' — --require-executed demands "
                "executed evidence for every row"
            )
            continue
        if not epath:
            errors.append(f"{rid}: no evidence_path")
            continue
        full = REPO_ROOT / epath
        if not full.exists():
            errors.append(f"{rid}: evidence file not found: {epath}")
            continue
        text = full.read_text(encoding="utf-8", errors="replace")
        if rid not in text:
            errors.append(f"{rid}: evidence file '{epath}' does not reference its rubric_id")
        fields = _parse_evidence_fields(text)

        missing = [k for k in EVIDENCE_REQUIRED_KEYS if k not in fields]
        if missing:
            errors.append(
                f"{rid}: evidence file '{epath}' missing metadata keys: {', '.join(missing)}"
            )

        empty = [k for k in EVIDENCE_REQUIRED_KEYS if k in fields and not fields[k]]
        if empty:
            errors.append(
                f"{rid}: evidence file '{epath}' has empty metadata values: {', '.join(empty)}"
            )

        for key, validator in EVIDENCE_FORMAT_VALIDATORS.items():
            value = fields.get(key, "")
            if value and not validator(value):
                errors.append(f"{rid}: evidence field '{key}' is not valid: '{value}'")

        declared_rid = fields.get("rubric_id", "")
        if declared_rid and declared_rid != rid:
            errors.append(f"{rid}: evidence rubric_id '{declared_rid}' does not match the row")

        # P1-1: an executed row must prove a real implementation artifact.
        apath = row.get("artifact_path", "")
        if not apath:
            errors.append(f"{rid}: executed row has no artifact_path")
        else:
            artifact = REPO_ROOT / apath
            if not artifact.exists():
                errors.append(f"{rid}: implementation artifact not found: {apath}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase 2 rubric evidence contract")
    parser.add_argument(
        "--matrix-only", action="store_true", help="Validate the rubric matrix only (phase-01)"
    )
    parser.add_argument(
        "--matrix",
        type=Path,
        default=None,
        help="Path to a rubric-matrix CSV to audit (defaults to docs/phase2/rubric-matrix.csv). "
        "Used for fixture-based tests.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail (exit 1) on any finding; default in phase-08 mode",
    )
    parser.add_argument(
        "--require-executed",
        action="store_true",
        help="Require evidence files to exist on disk (phase-08)",
    )
    parser.add_argument("--ml", type=int, default=100, help="Expected ML total points")
    parser.add_argument("--llm", type=int, default=100, help="Expected LLM total points")
    parser.add_argument(
        "--git-base",
        default="origin/dev",
        help="Base ref for the Phase 1 no-mutation git-diff check "
        "(default: origin/dev; an unresolvable baseline fails the gate)",
    )
    args = parser.parse_args(argv)

    expected = {"ML": args.ml, "LLM": args.llm}
    errors: list[str] = []
    matrix = _read_matrix(args.matrix)

    if matrix is None:
        errors.append("💀 docs/phase2/rubric-matrix.csv not found or unreadable")
    else:
        errors.extend(_audit_matrix(matrix, expected, enforce_evidence_prefix=args.matrix is None))
        errors.extend(_audit_phase1_no_mutation(matrix))

    if args.require_executed:
        if matrix is not None:
            errors.extend(_audit_executed(matrix))
        errors.extend(_audit_required_docs())

    if args.matrix_only:
        errors.extend(_audit_required_docs())
        # Phase 1 must not be mutated in the repository diff either.
        errors.extend(_audit_phase1_git_diff(args.git_base))

    # ── Output ────────────────────────────────────────────────────────
    if errors:
        for e in errors:
            print(e)
        fail = args.strict or args.require_executed
        print(f"\n{len(errors)} finding(s) — {'FAIL' if fail else 'exit 0 (non-strict)'}")
        return 1 if fail else 0

    print("✅ Phase 2 rubric matrix is complete and consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
