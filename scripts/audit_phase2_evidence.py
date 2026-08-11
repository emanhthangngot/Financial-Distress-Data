#!/usr/bin/env python3
"""Phase 2 evidence auditor — rubric-matrix linter and evidence validator.

Usage:
  python scripts/audit_phase2_evidence.py --matrix-only --strict
  python scripts/audit_phase2_evidence.py --matrix-only --matrix PATH
  python scripts/audit_phase2_evidence.py --require-executed --run-validations \
    --phase1-base "$PHASE1_BASE_SHA" --gitops-root ../financial-distress-gitops \
    --ml 100 --llm 100

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
                      be non-empty and format-valid (ISO-8601 timestamps, full
                      40-hex SHAs). Rows still marked design_only/stretch, and
                      executed rows whose implementation artifact
                      (artifact_path) is absent, fail the gate.
  --run-validations   Execute every feature-specific validation command after
                      evidence/artifact checks; canonical matrix only, without
                      invoking a shell.
  --track {ML,LLM}    Repeatable; restrict --require-executed/--run-validations
                      to one track (default both). The 117-row canonical
                      coverage and matrix-completeness checks are never
                      filtered — they always demand all rows present.

Exit codes:
  0  all checks passed
  1  matrix/evidence errors found (strict mode or phase-08 mode)
  2  script crashed / CSV unreadable
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
import re
import shlex
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
    "sql/",
    "docs/evidence/",
    "docs/mini_coursework.md",
    "docs/01_data_generator.md",
    "docs/02_schema_design.md",
]

# Carve-outs inside a PHASE1_PROTECTED prefix that hold no Phase 1 pipeline
# behavior. `src/streaming/flink/jobs/` is the opt-in W26 Flink job home: by
# design (see its README) it holds no burst/late-arrival/dedup logic — that
# lives in `kafka_to_bronze_consumer.py`, which stays fully protected. A diff
# confined to this carve-out is not a Phase 1 behavior mutation.
# `sql/init_ml_metadata.sql` is the Phase 2 `ml_metadata` schema (plan-pinned:
# phase-04-implementation-notes.md section 1) — a new file, never touching
# `sql/init_project_metadata.sql` or any other Phase 1 SQL.
PHASE1_PROTECTED_EXCEPTIONS = [
    "src/streaming/flink/jobs/",
    "sql/init_ml_metadata.sql",
]

REQUIRED_DOCS = [
    "docs/phase2/requirements.md",
    "docs/phase2/acceptance-criteria.md",
    "docs/phase2/architecture.md",
    "docs/phase2/evidence-contract.md",
    "docs/phase2/low-level-design.md",
    "docs/phase2/novel-ideas.md",
]

VALID_EVIDENCE_TYPES = {"executed", "design_only", "stretch"}
VALID_OWNERS = {"ml_engineer", "llm_engineer", "data_engineer", "platform_operator"}

SOURCE_ARTIFACT_ROOTS = (
    "src/ml/",
    "src/drift/",
    "src/llm/",
    "src/agents/",
    "apps/",
    "dags/phase2/",
    ".github/workflows/",
    "notebooks/",
    "tests/phase2/requirements/",
    "docs/phase2/",
)
GITOPS_ARTIFACT_ROOTS = (
    ".github/workflows/",
    "terraform/",
    "ansible/",
    "charts/",
    "platform/",
    "argocd/",
)

CANONICAL_RUBRICS = {
    "ML": REPO_ROOT / "docs/Coursework Tracking (Public) - rubic final-coursework (final - ml).csv",
    "LLM": REPO_ROOT
    / "docs/Coursework Tracking (Public) - rubic final-coursework (final - llm).csv",
}
EXPECTED_ROW_COUNTS = {"ML": 57, "LLM": 60}
TRACKS = ("ML", "LLM")

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


def _acceptance_ids() -> set[str]:
    """Return all declared acceptance IDs from the normative catalog."""
    path = REPO_ROOT / "docs/phase2/acceptance-criteria.md"
    if not path.exists():
        return set()
    return set(re.findall(r"`((?:ML|LLM)-AC-[A-Z0-9-]+)`", path.read_text(encoding="utf-8")))


def _normalized_source_digest(cells: list[str]) -> str:
    normalized = [" ".join(cell.split()) for cell in cells[:5]]
    return hashlib.sha256("\x1f".join(normalized).encode("utf-8")).hexdigest()


def _canonical_source_contracts() -> list[tuple[str, str, int, str, int]]:
    """Parse canonical CSVs independently of the matrix generator."""
    contracts: list[tuple[str, str, int, str, int]] = []
    for track, path in CANONICAL_RUBRICS.items():
        rows = csv.reader(io.StringIO(path.read_text(encoding="utf-8", errors="replace")))
        next(rows, None)
        for source_row_index, raw in enumerate(rows, start=1):
            cells = list(raw)
            while len(cells) < 5:
                cells.append("")
            try:
                points = int(cells[4].strip())
            except (ValueError, TypeError):
                continue
            if cells[3].strip().lower() == "sum" and not any(cell.strip() for cell in cells[:3]):
                continue
            if points <= 0:
                continue
            contracts.append(
                (
                    track,
                    path.relative_to(REPO_ROOT).as_posix(),
                    source_row_index,
                    _normalized_source_digest(cells),
                    points,
                )
            )
    return contracts


def _audit_canonical_coverage(matrix: list[dict[str, str]]) -> list[str]:
    """Reject omitted/substituted source rows even when totals still equal 100."""
    errors: list[str] = []
    canonical = _canonical_source_contracts()
    actual: list[tuple[str, str, int, str, int]] = []
    for row in matrix:
        try:
            actual.append(
                (
                    row.get("track", ""),
                    row.get("source_file", ""),
                    int(row.get("source_row_index", "0") or 0),
                    row.get("source_digest", ""),
                    int(row.get("points", "0") or 0),
                )
            )
        except ValueError:
            continue
    missing = sorted(set(canonical) - set(actual))
    extra = sorted(set(actual) - set(canonical))
    if missing:
        errors.append(f"canonical source coverage missing {len(missing)} row(s): {missing[:3]}")
    if extra:
        errors.append(
            f"canonical source coverage has {len(extra)} altered/extra row(s): {extra[:3]}"
        )
    return errors


def _audit_matrix(
    matrix: list[dict[str, str]],
    expected: dict[str, int],
    enforce_evidence_prefix: bool = True,
    enforce_explicit_implementation: bool = False,
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
    ]
    totals: dict[str, int] = {"ML": 0, "LLM": 0}
    seen: set[str] = set()
    owners_seen: set[str] = set()
    row_counts: dict[str, int] = {"ML": 0, "LLM": 0}
    declared_acceptance = _acceptance_ids()
    explicit_map: dict[str, tuple[str, str, str]] = {}
    if enforce_explicit_implementation:
        try:
            try:
                from scripts._phase2_rubric_items import EXPLICIT_IMPLEMENTATION
            except ImportError:
                from _phase2_rubric_items import EXPLICIT_IMPLEMENTATION

            explicit_map = EXPLICIT_IMPLEMENTATION
        except (ImportError, AttributeError) as exc:
            errors.append(f"explicit implementation map is unavailable: {exc}")
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

        if re.search(r"row[-_]?\d+$", rid):
            errors.append(f"{rid}: ID looks like a spreadsheet line number, use semantic slug")

        if track in totals:
            totals[track] += points
            row_counts[track] += 1

        acceptance_id = row.get("acceptance_id", "")
        if acceptance_id and acceptance_id not in declared_acceptance:
            errors.append(f"{rid}: acceptance_id '{acceptance_id}' does not resolve")

        source_digest = row.get("source_digest", "")
        if source_digest and not re.fullmatch(r"[0-9a-f]{64}", source_digest):
            errors.append(f"{rid}: source_digest must be 64 lowercase hex characters")

        source_row_index = row.get("source_row_index", "")
        if source_row_index and not re.fullmatch(r"[1-9][0-9]*", source_row_index):
            errors.append(f"{rid}: source_row_index '{source_row_index}' invalid")

        validation = row.get("validation_command", "")
        acceptance_id = row.get("acceptance_id", "")
        expected_validation = (
            "pytest tests/phase2/requirements/test_"
            f"{acceptance_id.lower().replace('-', '_')}.py -k '{rid}'"
        )
        if validation != expected_validation:
            errors.append(f"{rid}: validation_command must be the exact acceptance-row target")

        artifact_repo = row.get("artifact_repo", "")
        if artifact_repo not in {"source", "gitops"}:
            errors.append(f"{rid}: artifact_repo '{artifact_repo}' invalid")
        apath = row.get("artifact_path", "")
        if artifact_repo == "source" and apath and not apath.startswith(SOURCE_ARTIFACT_ROOTS):
            errors.append(f"{rid}: source artifact_path '{apath}' outside source roots")
        if artifact_repo == "gitops" and apath and not apath.startswith(GITOPS_ARTIFACT_ROOTS):
            errors.append(f"{rid}: GitOps artifact_path '{apath}' outside GitOps roots")
        if apath and apath.endswith("/"):
            errors.append(f"{rid}: artifact_path must name a concrete file, not a directory")

        if enforce_explicit_implementation and rid in explicit_map:
            expected_owner, expected_repo, expected_path = explicit_map[rid]
            actual = (owner, artifact_repo, apath)
            if actual != (expected_owner, expected_repo, expected_path):
                errors.append(f"{rid}: implementation mapping diverges from reviewed explicit map")
        elif enforce_explicit_implementation and rid not in explicit_map:
            errors.append(f"{rid}: missing explicit implementation map entry")

    # Every role must own at least one scored row (locked taxonomy)
    for role in VALID_OWNERS:
        if role not in owners_seen:
            errors.append(f"owner '{role}' owns no scored row in the rubric matrix")

    # 2. Totals
    for track, exp in expected.items():
        if totals.get(track, 0) != exp:
            errors.append(f"{track}: total points = {totals.get(track, 0)}, expected {exp}")
        expected_rows = EXPECTED_ROW_COUNTS.get(track)
        if expected_rows is not None and row_counts.get(track, 0) != expected_rows:
            errors.append(
                f"{track}: scored row count = {row_counts.get(track, 0)}, expected {expected_rows}"
            )

    if enforce_explicit_implementation and explicit_map:
        matrix_ids = {row.get("rubric_id", "") for row in matrix}
        missing = sorted(set(explicit_map) - matrix_ids)
        extra = sorted(matrix_ids - set(explicit_map))
        if missing:
            errors.append(f"explicit implementation map rows missing from matrix: {missing[:3]}")
        if extra:
            errors.append(
                f"matrix contains rows absent from explicit implementation map: {extra[:3]}"
            )

    return errors


def _audit_phase1_no_mutation(matrix: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    blob = "\n".join(",".join(row.values()) for row in matrix).lower()
    for path in PHASE1_PROTECTED:
        if path.lower() in blob:
            errors.append(f"Matrix references Phase 1 protected path '{path}'")
    for row in matrix:
        for value in row.values():
            lowered = value.lower()
            if "dags/" in lowered and "dags/phase2/" not in lowered:
                errors.append(f"{row.get('rubric_id', '?')}: matrix references a Phase 1 DAG path")
                break
    return errors


def _phase1_mutation_from_changed(changed: list[str]) -> list[str]:
    """Return errors when a git diff touches Phase 1 protected paths.

    `changed` is a list of repo-relative paths (e.g. from `git diff --name-only`).
    The working tree or branch must not modify Phase 1 collectors, transforms,
    quality, catalog, metadata, streaming, generator, dags, sql, or their docs.
    """
    errors: list[str] = []
    for path in PHASE1_PROTECTED:
        matched = [entry for entry in changed if entry == path or entry.startswith(path)]
        unexcepted = [
            entry
            for entry in matched
            if not any(entry.startswith(exc) for exc in PHASE1_PROTECTED_EXCEPTIONS)
        ]
        if unexcepted:
            errors.append(f"Git diff modifies Phase 1 protected path '{path}'")
    if any(entry.startswith("dags/") and not entry.startswith("dags/phase2/") for entry in changed):
        errors.append("Git diff modifies Phase 1 protected DAG path 'dags/'")
    return errors


def _audit_phase1_git_diff(base: str) -> list[str]:
    """Run the Phase 1 no-mutation gate and fail closed when unverifiable.

    Compares the working tree against ``<base>`` (default ``origin/dev``) and
    also lists untracked files, because ``git diff --name-only`` never reports
    brand-new files. A Phase 1 path touched by *either* source is a failure.

    Fail-closed: if the baseline cannot be resolved (missing ref, git error,
    non-zero exit) the gate returns an error instead of silently passing, so an
    unverifiable baseline never turns the mutation check into a no-op.

    ``PHASE1_HYGIENE_OVERRIDE=1`` suppresses only the protected-path findings
    below, after the baseline has been resolved and the diff computed — a
    missing/unresolvable baseline still fails closed regardless of this var.
    It exists for Phase 1's own architecture-hygiene work (moving/renaming
    Phase 1 files without changing Phase 1 behavior), which this gate cannot
    distinguish from a Phase 2 task mutating Phase 1 — it only sees changed
    paths, not intent. Unset by default so a real Phase 2 task is still
    blocked.
    """
    import subprocess

    changed: list[str] = []
    try:
        resolved = subprocess.run(
            ["git", "rev-parse", "--verify", f"{base}^{{commit}}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if resolved.returncode != 0:
            return [f"git check failed: baseline '{base}' is not a commit"]
        baseline = resolved.stdout.strip()
        ancestry = subprocess.run(
            ["git", "merge-base", "--is-ancestor", resolved.stdout.strip(), "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if ancestry.returncode != 0:
            # A remote tracking branch can contain a merge commit whose first
            # parent is this checkout. In that topology, comparing the
            # checkout against itself is the precise working-tree check; it
            # does not erase any local diff. True branch divergence remains a
            # hard failure.
            checkout_is_ancestor = subprocess.run(
                ["git", "merge-base", "--is-ancestor", "HEAD", baseline],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if checkout_is_ancestor.returncode != 0:
                return [f"git check failed: baseline '{base}' is not an ancestor of source HEAD"]
            baseline = "HEAD"
        diff = subprocess.run(
            ["git", "diff", "--name-only", baseline],
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

    findings = _phase1_mutation_from_changed(changed)
    if findings and os.environ.get("PHASE1_HYGIENE_OVERRIDE") == "1":
        return []
    return findings


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


def _is_full_git_sha(value: str) -> bool:
    """True only for a frozen 40-hex commit SHA."""
    return bool(re.fullmatch(r"[0-9a-f]{40}", value.strip()))


def _git_head(root: Path) -> str | None:
    """Return the exact checkout HEAD, or ``None`` when it is unverifiable."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value if _is_full_git_sha(value) else None


def _git_worktree_clean(root: Path) -> bool:
    """Return true only when tracked and untracked checkout state is clean."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and not result.stdout.strip()


def _revision_is_ancestor(root: Path, revision: str, head: str) -> bool:
    """Return whether revision is HEAD or a reachable ancestor of HEAD."""
    import subprocess

    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", revision, head],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode == 0


def _only_evidence_sha_lines_changed(root: Path, revision: str, head: str) -> bool:
    """Allow post-evidence commits only when they stamp SHA metadata lines."""
    import subprocess

    if revision == head:
        return True
    result = subprocess.run(
        ["git", "diff", "--unified=0", revision, head, "--"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return False
    current_path = ""
    saw_change = False
    allowed_line = re.compile(
        r"^[+-]\s*(?:[-*]\s*)?(?:\*\*)?(?:source_sha|gitops_sha)(?:\*\*)?\s*:"
    )
    for line in result.stdout.splitlines():
        if line.startswith("+++ b/"):
            current_path = line[6:]
        elif line.startswith(("diff --git ", "index ", "--- ", "@@")):
            continue
        elif line.startswith(("+", "-")):
            saw_change = True
            if not current_path.startswith("docs/phase2/evidence/") or not allowed_line.match(line):
                return False
    return saw_change


def _audit_frozen_revisions(matrix: list[dict[str, str]], gitops_root: Path | None) -> list[str]:
    """Ensure evidence SHAs are HEAD or tightly constrained ancestors.

    A syntactically valid SHA is not sufficient: promotion must be reproducible
    from the exact source and GitOps revisions that were actually checked out.
    """
    import subprocess

    errors: list[str] = []
    source_head = _git_head(REPO_ROOT)
    if source_head is None:
        return ["source checkout HEAD is unavailable; cannot verify frozen source_sha"]
    if gitops_root is None:
        return ["--gitops-root is required to verify frozen gitops_sha"]
    gitops_head = _git_head(gitops_root)
    if gitops_head is None:
        return ["GitOps checkout HEAD is unavailable; cannot verify frozen gitops_sha"]
    if not _git_worktree_clean(REPO_ROOT):
        errors.append(
            "source checkout is not clean; commit evidence and implementation "
            "files before promotion"
        )
    if not _git_worktree_clean(gitops_root):
        errors.append(
            "GitOps checkout is not clean; commit all declared manifests before promotion"
        )

    checked: set[tuple[str, str]] = set()
    for row in matrix:
        rid = row.get("rubric_id", "?")
        epath = row.get("evidence_path", "")
        full = REPO_ROOT / epath
        if not full.is_file():
            continue
        fields = _parse_evidence_fields(full.read_text(encoding="utf-8", errors="replace"))
        source_sha = fields.get("source_sha", "")
        gitops_sha = fields.get("gitops_sha", "")
        for label, sha, root, expected in (
            ("source_sha", source_sha, REPO_ROOT, source_head),
            ("gitops_sha", gitops_sha, gitops_root, gitops_head),
        ):
            if not _is_full_git_sha(sha):
                continue
            key = (str(root), sha)
            if key not in checked:
                checked.add(key)
                try:
                    result = subprocess.run(
                        ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                except (OSError, subprocess.SubprocessError) as exc:
                    errors.append(f"{rid}: cannot verify {label} commit {sha}: {exc}")
                    continue
                if result.returncode != 0:
                    errors.append(f"{rid}: {label} does not resolve to a commit: {sha}")
            if not _revision_is_ancestor(root, sha, expected):
                errors.append(
                    f"{rid}: {label}={sha} is not an ancestor of checkout HEAD {expected}"
                )
            elif sha != expected and not _only_evidence_sha_lines_changed(root, sha, expected):
                errors.append(
                    f"{rid}: changes after {label}={sha} are not limited to SHA lines "
                    "in evidence files"
                )
    return errors


EVIDENCE_SECRET_DENYLIST = (
    ("GCP project ID", re.compile(r"\bproject-60655616-d84a-4883-867\b")),
    ("control-plane IP", re.compile(r"\b136\.85\.120\.118\b")),
    ("retained ingress IP", re.compile(r"\b34\.21\.242\.110\b")),
    ("GitHub token", re.compile(r"\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")),
    ("private key", re.compile(r"-----BEGIN(?: [A-Z]+)* PRIVATE KEY-----")),
    ("authorization header", re.compile(r"(?i)\bAuthorization\s*:")),
    (
        "long base64 value",
        re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{200,}={0,2}(?![A-Za-z0-9+/=])"),
    ),
    (
        "GCP project ID",
        re.compile(r"(?im)\b(?:project_id|gcp_project)\s*[:=]\s*[a-z][a-z0-9-]{4,28}[a-z0-9]\b"),
    ),
    (
        "control-plane endpoint",
        re.compile(
            r"(?im)\b(?:control[_ -]?plane|cluster_endpoint)\s*[:=]\s*(?:https?://)?\d{1,3}(?:\.\d{1,3}){3}\b"
        ),
    ),
    (
        "SSH username",
        re.compile(
            r"(?im)(?:\b(?:ansible_user|ssh_user|ssh_username)\s*[:=]\s*"
            r"[A-Za-z_][A-Za-z0-9_-]*\b|\bssh(?:\s+-[A-Za-z]+(?:\s+\S+)*)*\s+"
            r"[A-Za-z_][A-Za-z0-9_-]*@)"
        ),
    ),
)


def _audit_evidence_secrets(rid: str, evidence_path: str, text: str) -> list[str]:
    """Reject known infrastructure identifiers and credential-shaped data."""
    return [
        f"{rid}: evidence file '{evidence_path}' contains denylisted {label}"
        for label, pattern in EVIDENCE_SECRET_DENYLIST
        if pattern.search(text)
    ]


def _audit_all_evidence_bodies() -> list[str]:
    """Scan every committed evidence markdown body, including accepted cuts."""
    errors: list[str] = []
    evidence_root = REPO_ROOT / "docs/phase2/evidence"
    if not evidence_root.is_dir():
        return errors
    for path in sorted(evidence_root.rglob("*.md")):
        relative = path.relative_to(REPO_ROOT).as_posix()
        errors.extend(
            _audit_evidence_secrets(
                path.stem,
                relative,
                path.read_text(encoding="utf-8", errors="replace"),
            )
        )
    return errors


# Format validators per evidence-contract field. Keys not listed only need a
# non-empty value (they are free-form text).
EVIDENCE_FORMAT_VALIDATORS: dict[str, callable] = {
    "execution_timestamp": _is_iso_timestamp,
    "source_sha": _is_full_git_sha,
    "gitops_sha": _is_full_git_sha,
}


def _audit_executed(
    matrix: list[dict[str, str]],
    gitops_root: Path | None,
    accept_design_only: set[str] | None = None,
) -> list[str]:
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
    accepted = accept_design_only or set()
    for row in matrix:
        rid = row.get("rubric_id", "?")
        epath = row.get("evidence_path", "")
        etype = row.get("evidence_type", "")
        if etype != "executed":
            if rid in accepted:
                if etype != "design_only":
                    errors.append(
                        f"{rid}: --accept-design-only cannot accept evidence_type '{etype}'"
                    )
                continue
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
            if (
                key == "gitops_sha"
                and row.get("artifact_repo") == "source"
                and value.casefold().startswith("none")
            ):
                continue
            if value and not validator(value):
                errors.append(f"{rid}: evidence field '{key}' is not valid: '{value}'")

        declared_rid = fields.get("rubric_id", "")
        if declared_rid and declared_rid != rid:
            errors.append(f"{rid}: evidence rubric_id '{declared_rid}' does not match the row")

        # An executed row must prove a real implementation file in the repo it
        # declares. GitOps paths are resolved only from an explicit checkout.
        apath = row.get("artifact_path", "")
        artifact_repo = row.get("artifact_repo", "")
        if not apath:
            errors.append(f"{rid}: executed row has no artifact_path")
        else:
            if artifact_repo == "gitops" and gitops_root is None:
                errors.append(f"{rid}: --gitops-root is required for GitOps artifact validation")
                continue
            root = gitops_root if artifact_repo == "gitops" else REPO_ROOT
            assert root is not None
            artifact = root / apath
            if not artifact.is_file():
                errors.append(f"{rid}: implementation artifact not found: {apath}")
    return errors


def _audit_behavior_validations(matrix: list[dict[str, str]]) -> list[str]:
    """Execute feature-specific validation commands without invoking a shell."""
    import subprocess

    errors: list[str] = []
    allowed = re.compile(r"pytest tests/phase2/requirements/test_[a-z0-9_]+\.py -k '[A-Za-z0-9-]+'")
    for row in matrix:
        rid = row.get("rubric_id", "?")
        command = row.get("validation_command", "")
        if not allowed.fullmatch(command):
            errors.append(f"{rid}: behavior validation command is missing or unsafe")
            continue
        try:
            result = subprocess.run(
                shlex.split(command),
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append(f"{rid}: behavior validation could not run ({exc})")
            continue
        if result.returncode != 0:
            detail = (result.stdout + result.stderr).strip().splitlines()
            errors.append(
                f"{rid}: behavior validation failed with exit {result.returncode}"
                + (f" — {detail[-1]}" if detail else "")
            )
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
    parser.add_argument(
        "--gitops-root",
        type=Path,
        default=None,
        help="Checked-out GitOps repository root used to validate GitOps artifact files",
    )
    parser.add_argument(
        "--run-validations",
        action="store_true",
        help="Execute every row's feature-specific validation command (Phase 8)",
    )
    parser.add_argument(
        "--track",
        action="append",
        choices=TRACKS,
        default=None,
        help="Restrict executed/frozen-revision/behavior-validation auditing to one "
        "track (repeatable); default both. Canonical coverage and the 117-row "
        "matrix contract are never filtered by this flag.",
    )
    parser.add_argument(
        "--accept-design-only",
        action="append",
        default=[],
        metavar="RUBRIC_ID[,RUBRIC_ID...]",
        help="Name pending design-only rows for an interim audit; during final promotion "
        "(--phase1-base or --run-validations), these become documented unearned cuts",
    )
    parser.add_argument("--ml", type=int, default=100, help="Expected ML total points")
    parser.add_argument("--llm", type=int, default=100, help="Expected LLM total points")
    parser.add_argument(
        "--git-base",
        default="origin/dev",
        help="Base ref for the matrix-only Phase 1 no-mutation check "
        "(default: origin/dev; an unresolvable baseline fails the gate)",
    )
    parser.add_argument(
        "--phase1-base",
        default=None,
        help="Frozen 40-hex Phase 1 baseline commit required by the promotion gate",
    )
    args = parser.parse_args(argv)

    expected = {"ML": args.ml, "LLM": args.llm}
    errors: list[str] = []
    matrix = _read_matrix(args.matrix)
    selected_tracks = tuple(args.track) if args.track else TRACKS
    accepted_design_only = {
        rid.strip() for group in args.accept_design_only for rid in group.split(",") if rid.strip()
    }
    final_promotion = bool(args.phase1_base) or args.run_validations
    scoped = (
        [row for row in matrix if row.get("track", "") in selected_tracks]
        if matrix is not None
        else None
    )

    if matrix is None:
        errors.append("💀 docs/phase2/rubric-matrix.csv not found or unreadable")
    else:
        errors.extend(
            _audit_matrix(
                matrix,
                expected,
                enforce_evidence_prefix=args.matrix is None,
                enforce_explicit_implementation=args.matrix is None,
            )
        )
        errors.extend(_audit_phase1_no_mutation(matrix))
        if args.matrix is None:
            errors.extend(_audit_canonical_coverage(matrix))

    if args.require_executed:
        errors.extend(_audit_all_evidence_bodies())
        if scoped is not None:
            scoped_ids = {row.get("rubric_id", "") for row in scoped}
            unknown_cuts = sorted(accepted_design_only - scoped_ids)
            if unknown_cuts:
                errors.append(
                    f"--accept-design-only names unknown/out-of-scope rows: {unknown_cuts}"
                )
            if final_promotion:
                submission_readme = REPO_ROOT / "docs/submission/README.md"
                readme_text = (
                    submission_readme.read_text(encoding="utf-8", errors="replace")
                    if submission_readme.is_file()
                    else ""
                )
                undocumented_cuts = sorted(
                    rid for rid in accepted_design_only if rid not in readme_text
                )
                if undocumented_cuts:
                    errors.append(
                        "final --accept-design-only cuts must be documented in "
                        f"docs/submission/README.md: {undocumented_cuts}"
                    )
            invalid_cut_types = sorted(
                row.get("rubric_id", "")
                for row in scoped
                if row.get("rubric_id", "") in accepted_design_only
                and row.get("evidence_type", "") != "design_only"
            )
            if invalid_cut_types:
                errors.append(
                    "--accept-design-only requires evidence_type design_only: "
                    f"{invalid_cut_types}"
                )
            errors.extend(_audit_executed(scoped, args.gitops_root, accepted_design_only))
            valid_cuts = {
                row.get("rubric_id", "")
                for row in scoped
                if row.get("evidence_type", "") == "design_only"
            }
            for rid in sorted(accepted_design_only & valid_cuts):
                label = "accepted final cut" if final_promotion else "pending interim row"
                print(f"WARNING: {rid}: {label}; no rubric points claimed")
            if args.matrix is None and final_promotion:
                if not args.phase1_base or not _is_full_git_sha(args.phase1_base):
                    errors.append("final promotion requires --phase1-base as a frozen 40-hex SHA")
                else:
                    errors.extend(_audit_phase1_git_diff(args.phase1_base))
                    errors.extend(_audit_frozen_revisions(scoped, args.gitops_root))
        errors.extend(_audit_required_docs())

    if args.run_validations:
        if not args.require_executed:
            errors.append("--run-validations requires --require-executed")
        elif args.matrix is not None:
            errors.append("--run-validations is allowed only for the canonical matrix")
        elif not args.phase1_base or not _is_full_git_sha(args.phase1_base):
            errors.append("--run-validations requires --phase1-base as a frozen 40-hex SHA")
        elif scoped is not None:
            errors.extend(_audit_behavior_validations(scoped))

    if args.matrix_only:
        errors.extend(_audit_required_docs())
        # Phase 1 must not be mutated in the repository diff either.
        errors.extend(_audit_phase1_git_diff(args.git_base))

    # ── Output ────────────────────────────────────────────────────────
    if errors:
        for e in errors:
            print(e)
        fail = args.strict or args.require_executed or args.run_validations
        print(f"\n{len(errors)} finding(s) — {'FAIL' if fail else 'exit 0 (non-strict)'}")
        return 1 if fail else 0

    print("✅ Phase 2 rubric matrix is complete and consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
