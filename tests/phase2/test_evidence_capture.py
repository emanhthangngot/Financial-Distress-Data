from __future__ import annotations

from pathlib import Path

from scripts.capture_phase2_evidence import _load_checklist, _run_section

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_evidence_checklist_covers_all_overlay_phases() -> None:
    sections = _load_checklist(REPO_ROOT / "configs/evidence-checklist.yaml")
    assert len(sections) >= 12
    assert sections["phase11-rollouts"]["screenshot"] is True
    assert sections["phase12-freeze"]["screenshot_command"]


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
