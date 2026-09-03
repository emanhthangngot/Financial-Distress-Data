#!/usr/bin/env python3
"""Commit and stamp platform .vidence without rewriting implementation history.

The workflow is intentionally explicit about paths. It stages only the paths
provided by the caller, so unrelated worktree changes are never swept into a
submission commit. Evidence is committed once with its captured body, then a
separate commit updates only ``source_sha`` and ``gitops_sha`` lines.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from pathlib import Path


def git(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
    if check and result.returncode:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {root}: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout.strip()


def head(root: Path) -> str:
    value = git(root, "rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise RuntimeError(f"{root} does not have a full 40-hex HEAD")
    return value


def _assert_sha_only_staged_diff(root: Path, paths: list[str]) -> None:
    allowed = re.compile(r"^[+-]\s*(?:[-*]\s*)?(?:\*\*)?(?:source_sha|gitops_sha)(?:\*\*)?\s*:")
    diff = git(root, "diff", "--cached", "--unified=0", "--", *paths)
    current_path = ""
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_path = line[6:]
        elif line.startswith(("diff --git ", "index ", "--- ", "@@")):
            continue
        elif line.startswith(("+", "-")):
            if not current_path.startswith("docs/platform/evidence/") or not allowed.match(line):
                raise RuntimeError("final evidence commit contains a non-SHA-line change")


def commit_paths(root: Path, paths: list[str], message: str, *, sha_only: bool = False) -> str:
    preexisting = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root, check=False)
    if preexisting.returncode != 0:
        raise RuntimeError(f"staged changes already exist in {root}; clear them before stamping")
    if paths:
        git(root, "add", "--", *paths)
    if sha_only:
        _assert_sha_only_staged_diff(root, paths)
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root, check=False)
    if staged.returncode == 0:
        return head(root)
    git(root, "commit", "-m", message)
    return head(root)


def stamp_files(evidence_files: list[Path], source_sha: str, gitops_sha: str) -> None:
    for path in evidence_files:
        text = path.read_text(encoding="utf-8")
        text, source_count = re.subn(
            r"^(\s*(?:[-*]\s*)?(?:\*\*)?source_sha(?:\*\*)?\s*:\s*).*$",
            rf"\g<1>{source_sha}",
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        text, gitops_count = re.subn(
            r"^(\s*(?:[-*]\s*)?(?:\*\*)?gitops_sha(?:\*\*)?\s*:\s*).*$",
            rf"\g<1>{gitops_sha}",
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        if source_count != 1 or gitops_count != 1:
            raise RuntimeError(
                f"{path} must contain exactly one source_sha and one gitops_sha line"
            )
        path.write_text(text, encoding="utf-8")


def canonical_evidence_files(source_root: Path, evidence_dir: Path) -> list[Path]:
    matrix_path = source_root / "docs/platform/rubric-matrix.csv"
    with matrix_path.open(newline="", encoding="utf-8") as handle:
        rows = csv.DictReader(handle)
        paths = sorted(
            {
                (source_root / row["evidence_path"]).resolve()
                for row in rows
                if row.get("track") == "LLM" and row.get("evidence_type") == "executed"
            }
        )
    if not paths:
        raise SystemExit(f"no executed LLM evidence paths found in {matrix_path}")
    if any(path.parent != evidence_dir for path in paths):
        raise SystemExit("canonical executed evidence is outside the requested evidence directory")
    missing = [path for path in paths if not path.is_file()]
    if missing:
        missing_list = ", ".join(str(path.relative_to(source_root)) for path in missing)
        raise SystemExit(f"canonical executed evidence is missing: {missing_list}")
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--gitops-root", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, default=Path("docs/platform/evidence/llm"))
    parser.add_argument("--source-path", action="append", default=[])
    parser.add_argument("--gitops-path", action="append", default=[])
    parser.add_argument(
        "--implementation-message", default="feat(phase2): complete llm evidence artifacts"
    )
    parser.add_argument("--evidence-message", default="docs(phase2): capture llm evidence")
    parser.add_argument("--stamp-message", default="docs(phase2): stamp evidence revisions")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_root = args.source_root.resolve()
    gitops_root = args.gitops_root.resolve()
    evidence_dir = (source_root / args.evidence_dir).resolve()
    evidence_files = canonical_evidence_files(source_root, evidence_dir)

    # The control repo must already be clean except for explicitly supplied
    # paths; otherwise a stamp could silently capture an unrelated manifest.
    if not args.gitops_path and git(gitops_root, "status", "--porcelain"):
        raise SystemExit("GitOps worktree has uncommitted changes; pass --gitops-path explicitly")

    gitops_sha = commit_paths(
        gitops_root, args.gitops_path, "chore(phase2): prepare evidence revision"
    )
    commit_paths(source_root, args.source_path, args.implementation_message)

    # Capture the evidence bodies against a committed implementation revision,
    # then commit those bodies so the final stamp commit is SHA-lines-only.
    source_before_evidence = head(source_root)
    stamp_files(evidence_files, source_before_evidence, gitops_sha)
    relative_evidence = [str(path.relative_to(source_root)) for path in evidence_files]
    commit_paths(source_root, relative_evidence, args.evidence_message)

    source_evidence_head = head(source_root)
    stamp_files(evidence_files, source_evidence_head, head(gitops_root))
    commit_paths(source_root, relative_evidence, args.stamp_message, sha_only=True)
    print(f"source_sha={source_evidence_head}")
    print(f"gitops_sha={head(gitops_root)}")
    print(f"evidence_files={len(evidence_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
