#!/usr/bin/env python3
"""Run and record the Phase 05 mutmut hard gate for its declared pure subset."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
MUTANT_PATTERN = "llm.rag.chunking.*"
MINIMUM_MUTATION_SCORE = 80.0
REPORT_DIR = REPO_ROOT / "plans/260809-2039-complete-platform-llm-submission/reports"
SUMMARY_PATH = REPORT_DIR / "phase05-mutation-summary.json"
RESULTS_PATH = REPORT_DIR / "phase05-mutmut-results.txt"
STATS_PATH = REPO_ROOT / "mutants/mutmut-cicd-stats.json"


def mutation_score(stats: dict[str, Any]) -> float:
    """Calculate a killed/total percentage, including survivors and timeouts."""
    total = int(stats["total"])
    killed = int(stats["killed"])
    if total < 1:
        raise ValueError("mutmut did not generate any mutants")
    if not 0 <= killed <= total:
        raise ValueError("mutmut returned an invalid killed/total count")
    return round(killed / total * 100, 2)


def meets_mutation_gate(score: float) -> bool:
    """The rubric is strict: exactly 80% does not satisfy 'above 80%'."""
    return score > MINIMUM_MUTATION_SCORE


def mutmut_run_succeeded(exit_code: int) -> bool:
    """Prevent stale results from satisfying the gate after a fresh-run failure."""
    return exit_code == 0


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    run = subprocess.run(
        [sys.executable, "-m", "mutmut", "run", MUTANT_PATTERN], cwd=REPO_ROOT, check=False
    )
    if not mutmut_run_succeeded(run.returncode):
        print(f"mutmut run failed with exit code {run.returncode}", file=sys.stderr)
        return 1
    exported = subprocess.run(
        [sys.executable, "-m", "mutmut", "export-cicd-stats"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    results = subprocess.run(
        [sys.executable, "-m", "mutmut", "results"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if results.returncode != 0:
        print(results.stdout, end="")
        print(results.stderr, end="", file=sys.stderr)
        return 1
    RESULTS_PATH.write_text(results.stdout + results.stderr, encoding="utf-8")
    if exported.returncode != 0 or not STATS_PATH.is_file():
        print(exported.stdout, end="")
        print(exported.stderr, end="", file=sys.stderr)
        return 1

    stats = json.loads(STATS_PATH.read_text(encoding="utf-8"))
    score = mutation_score(stats)
    summary = {
        "scope": MUTANT_PATTERN,
        "minimum_score_exclusive": MINIMUM_MUTATION_SCORE,
        "score": score,
        "killed": int(stats["killed"]),
        "survived": int(stats["survived"]),
        "timeout": int(stats["timeout"]),
        "no_tests": int(stats["no_tests"]),
        "total": int(stats["total"]),
        "mutmut_run_exit_code": run.returncode,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0 if meets_mutation_gate(score) else 1


if __name__ == "__main__":
    sys.exit(main())
