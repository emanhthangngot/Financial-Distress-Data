from __future__ import annotations

from pathlib import Path

from scripts.capture_platform_evidence import _load_checklist, _run_section

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_evidence_checklist_covers_llm_scope() -> None:
    # Trimmed 2026-08-14 to the LLM-only submission scope; the ML-scoped
    # cluster-operator sections (Kyverno, ESO/Linkerd, lakehouse, CDC, ML,
    # Rollouts, freeze) were removed rather than left to capture evidence for
    # infrastructure this repo no longer claims to run.
    sections = _load_checklist(REPO_ROOT / "configs/evidence-checklist.yaml")
    assert set(sections) == {
        "lakehouse",
        "platform-tests",
        "platform-matrix",
        "platform-quality-gates",
    }
    assert all(section["screenshot"] is False for section in sections.values())


def test_dry_run_records_declared_screenshot_without_faking_capture(tmp_path: Path) -> None:
    record = _run_section(
        "rollouts",
        {
            "command": "true",
            "claim": "planned capture",
            "screenshot": True,
            "screenshot_command": "false",
        },
        tmp_path,
        dry_run=True,
    )
    assert record["status"] == "pass"
    assert record["screenshot_status"] == "planned"


def test_missing_command_is_recorded_as_failure(tmp_path: Path) -> None:
    record = _run_section(
        "missing",
        {"command": "command-that-does-not-exist", "claim": "not available"},
        tmp_path,
        dry_run=False,
    )
    assert record["status"] == "fail"
    assert record["returncode"] == 127


def test_screenshot_command_without_artifact_is_not_a_pass(tmp_path: Path) -> None:
    record = _run_section(
        "empty-screenshot",
        {
            "command": "true",
            "claim": "must capture an image",
            "screenshot": True,
            "screenshot_command": "true",
        },
        tmp_path,
        dry_run=False,
    )
    assert record["status"] == "fail"
    assert record["screenshot_artifacts"] == []
