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
TARGET_MODULES = ["src/ml/reproducibility_manifest.py"]
TEST_SELECTION = ["tests/platform/verification/test_mutmut_target.py"]


ALIAS_CONFTST = """\nfrom importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

_mutant_root = Path(__file__).resolve().parents[1]
_target_modules = {target_modules!r}
for _relative_path in _target_modules:
    _module_name = _relative_path.removesuffix(\".py\").replace(\"/\", \".\")
    _alias = _module_name.removeprefix(\"src.\")
    _path = _mutant_root / _relative_path
    _spec = spec_from_file_location(_alias, _path)
    assert _spec and _spec.loader
    _module = module_from_spec(_spec)
    sys.modules[_alias] = _module
    sys.modules[_module_name] = _module
    _spec.loader.exec_module(_module)
"""


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="p11-mutmut-") as workdir_name:
        workdir = Path(workdir_name)
        shutil.copytree(REPO_ROOT / "src", workdir / "src")
        shutil.copytree(REPO_ROOT / "tests", workdir / "tests")
        conftest_path = workdir / "tests" / "conftest.py"
        existing_conftest = (
            conftest_path.read_text(encoding="utf-8") if conftest_path.exists() else ""
        )
        conftest_path.write_text(
            existing_conftest + ALIAS_CONFTST.format(target_modules=TARGET_MODULES),
            encoding="utf-8",
        )
        selections = ", ".join(f'"{path}"' for path in TEST_SELECTION)
        (workdir / "pyproject.toml").write_text(
            "[tool.pytest.ini_options]\n"
            'pythonpath = ["."]\n'
            "markers = [\n"
            '    "slow: takes more than ~2s; excluded by the fast loop",\n'
            '    "services: requires the docker compose stack to be running",\n'
            '    "postgres: requires local initdb/pg_ctl binaries",\n'
            "]\n\n"
            "[tool.mutmut]\n"
            f"source_paths = {TARGET_MODULES!r}\n"
            f"pytest_add_cli_args_test_selection = [{selections}]\n"
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
        survived = int(stats["survived"])
        no_tests = int(stats["no_tests"])
        if run.returncode not in (0, 1) or killed + survived + no_tests == 0:
            return 1
        score = round(killed * 100 / total, 2) if total else 0.0
        summary = {
            "scope": TARGET_MODULES,
            "test_selection": TEST_SELECTION,
            "score": score,
            "killed": killed,
            "survived": survived,
            "timeout": int(stats["timeout"]),
            "no_tests": no_tests,
            "total": total,
            "mutmut_run_exit_code": run.returncode,
        }
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        RESULTS_PATH.write_text(results.stdout + results.stderr, encoding="utf-8")
        print(json.dumps(summary, sort_keys=True))
        return 0 if score > 80 else 1


if __name__ == "__main__":
    raise SystemExit(main())
