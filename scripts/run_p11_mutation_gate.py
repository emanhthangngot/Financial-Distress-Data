"""Run a bounded target-plan P11 mutation pilot in an isolated mutmut project."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "plans/260831-1644-rebuild-target-mlops-architecture/reports"
SUMMARY_PATH = REPORT_DIR / "p11-mutation-pilot-summary.json"
RESULTS_PATH = REPORT_DIR / "p11-mutmut-pilot-results.txt"
SOURCE_PATH = "src/ml/reproducibility_manifest.py"
TEST_PATH = "tests/platform/verification/test_mutmut_target.py"


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="p11-mutmut-") as workdir_name:
        workdir = Path(workdir_name)
        shutil.copytree(REPO_ROOT / "src", workdir / "src")
        shutil.copytree(REPO_ROOT / "tests", workdir / "tests")
        (workdir / "pyproject.toml").write_text(
            "[tool.mutmut]\n"
            f'source_paths = ["{SOURCE_PATH}"]\n'
            f'pytest_add_cli_args_test_selection = ["{TEST_PATH}"]\n'
            "mutate_only_covered_lines = false\n",
            encoding="utf-8",
        )
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        run = subprocess.run(
            [sys.executable, "-m", "mutmut", "run"],
            cwd=workdir,
            env=env,
            check=False,
        )
        if run.returncode not in (0, 1):
            return run.returncode
        results = subprocess.run(
            [sys.executable, "-m", "mutmut", "results"],
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        exported = subprocess.run(
            [sys.executable, "-m", "mutmut", "export-cicd-stats"],
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        stats_path = workdir / "mutants/mutmut-cicd-stats.json"
        if results.returncode != 0 or exported.returncode != 0 or not stats_path.is_file():
            print(results.stdout, end="")
            print(results.stderr, end="", file=sys.stderr)
            print(exported.stderr, end="", file=sys.stderr)
            return 1
        stats = json.loads(stats_path.read_text(encoding="utf-8"))
        total = int(stats["total"])
        killed = int(stats["killed"])
        score = round(killed * 100 / total, 2) if total else 0.0
        summary = {
            "scope": SOURCE_PATH,
            "test_selection": TEST_PATH,
            "score": score,
            "killed": killed,
            "survived": int(stats["survived"]),
            "timeout": int(stats["timeout"]),
            "no_tests": int(stats["no_tests"]),
            "total": total,
            "mutmut_run_exit_code": run.returncode,
        }
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        RESULTS_PATH.write_text(results.stdout + results.stderr, encoding="utf-8")
        print(json.dumps(summary, sort_keys=True))
        return 0 if score > 80 else 1


if __name__ == "__main__":
    raise SystemExit(main())
