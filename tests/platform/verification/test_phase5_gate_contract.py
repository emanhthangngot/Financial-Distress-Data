"""Regression contracts for the Phase 05 CI verification gates."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_script(name: str):
    path = REPO_ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_web_gate_requires_line_and_branch_rates(tmp_path: Path) -> None:
    module = _load_script("run_phase5_web_gate.py")
    report = tmp_path / "coverage.xml"
    report.write_text('<coverage line-rate="0.9563" branch-rate="0.8043" />', encoding="utf-8")

    line_rate, branch_rate = module.coverage_rates(report)

    assert line_rate == 95.63
    assert branch_rate == 80.43
    assert module.meets_coverage_gate(line_rate, branch_rate) is False


def test_mutation_gate_rejects_scores_at_or_below_eighty_percent() -> None:
    module = _load_script("run_phase5_mutation_gate.py")

    assert module.mutation_score({"killed": 62, "total": 72}) == 86.11
    assert module.mutmut_run_succeeded(0) is True
    assert module.mutmut_run_succeeded(1) is False
    assert module.meets_mutation_gate(80.0) is False
    assert module.meets_mutation_gate(80.01) is True


def test_mutation_gate_does_not_reuse_stats_after_a_failed_run(monkeypatch, tmp_path: Path) -> None:
    module = _load_script("run_phase5_mutation_gate.py")
    calls = []
    monkeypatch.setattr(module, "REPORT_DIR", tmp_path)

    def failed_run(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr(module.subprocess, "run", failed_run)

    assert module.main() == 1
    assert len(calls) == 1


def test_mutation_gate_rejects_an_invalid_survivor_report(monkeypatch, tmp_path: Path) -> None:
    module = _load_script("run_phase5_mutation_gate.py")
    stats_path = tmp_path / "mutmut-cicd-stats.json"
    stats_path.write_text(
        '{"killed": 62, "survived": 9, "timeout": 1, "no_tests": 0, "total": 72}',
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "REPORT_DIR", tmp_path)
    monkeypatch.setattr(module, "STATS_PATH", stats_path)
    outcomes = iter(
        [
            SimpleNamespace(returncode=0),
            SimpleNamespace(returncode=0, stdout="", stderr=""),
            SimpleNamespace(returncode=1, stdout="bad results", stderr=""),
        ]
    )
    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: next(outcomes))

    assert module.main() == 1
    assert not (tmp_path / "phase05-mutmut-results.txt").exists()


def test_reusable_ci_executes_phase5_hard_gates() -> None:
    workflow = (REPO_ROOT / ".github/workflows/platform-ci.yaml").read_text(encoding="utf-8")

    assert "scripts/run_phase5_web_gate.py" in workflow
    assert "scripts/run_phase5_mutation_gate.py" in workflow
