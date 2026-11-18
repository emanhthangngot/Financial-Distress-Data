"""Rubric completion evidence invariants.

These tests guard the final submission hardening layer: a detailed 100-point
rubric completion spec plus reviewer-facing screenshots generated from checked-in
runtime evidence. They intentionally fail until the spec and screenshots exist.
"""

from __future__ import annotations

import csv
from pathlib import Path

from src.evidence.rubric_audit import load_requirements

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"
EVIDENCE = DOCS / "evidence"
SCREENSHOTS = EVIDENCE / "reviewer_screenshots"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def test_rubric_completion_spec_documents_all_major_sections() -> None:
    spec = DOCS / "11_rubric_completion_spec.md"
    assert spec.exists(), "Missing final rubric completion spec"
    text = _read(spec)
    for section in (
        "Engineering Fundamentals",
        "Implement Data Generator",
        "Processing Jobs",
        "Data Storage",
        "Data Pipeline Orchestration",
        "Data Governance",
        "Documentation",
        "README + Deployment Diagram",
        "Novel Ideas",
    ):
        assert section in text, f"Spec does not document rubric section: {section}"
    assert "WHO -> ACTION -> RESULT" in text
    assert "100/100" in text


def test_streaming_generator_configuration_is_explicit_in_spec() -> None:
    spec_text = _read(DOCS / "11_rubric_completion_spec.md").lower()
    config_text = _read(REPO_ROOT / "configs" / "collector_config.yaml").lower()
    assert "stream_flush_record_count" in config_text
    assert "streaming generator configuration" in spec_text
    assert "stream_flush_record_count" in spec_text
    assert "stream_flush_interval_seconds" in spec_text


def test_scored_requirements_match_the_current_rubric_csv() -> None:
    """Keep package scoring synchronized with the authoritative rubric CSV."""
    rubric_path = DOCS / "Coursework Tracking (Public) - rubic (mini-coursework).csv"
    with rubric_path.open(encoding="utf-8-sig", newline="") as stream:
        rubric_points = [
            int(row[4])
            for row in csv.reader(stream)
            if len(row) >= 5 and row[4].isdigit() and row[3].strip() != "Sum"
        ]

    requirements = load_requirements(REPO_ROOT / "configs" / "rubric-requirements.yaml")
    requirement_points = [item.points for item in requirements.criteria]

    assert requirement_points[0] == 0, "README/deployment evidence is mandatory but unscored"
    assert requirement_points[1:] == rubric_points
    assert sum(requirement_points) == 100


def test_reviewer_screenshot_html_sources_exist() -> None:
    for name in (
        "airflow_dp2_dp3_evidence.html",
        "spark_optimization_evidence.html",
        "flink_streaming_evidence.html",
        "governance_lineage_contracts_evidence.html",
    ):
        path = SCREENSHOTS / name
        assert path.exists(), f"Missing screenshot source HTML: {path}"
        text = _read(path)
        assert "Generated from checked-in platform evidence" in text


def test_reviewer_screenshot_pngs_exist_and_are_nontrivial() -> None:
    for name in (
        "airflow_dp2_dp3_evidence.png",
        "spark_optimization_evidence.png",
        "flink_streaming_evidence.png",
        "governance_lineage_contracts_evidence.png",
    ):
        path = SCREENSHOTS / name
        assert path.exists(), f"Missing reviewer screenshot: {path}"
        assert path.stat().st_size > 20_000, f"Screenshot is too small: {path}"


def test_submission_package_screenshots_are_nontrivial() -> None:
    """Reject blank or nearly blank screenshots before sealing a submission package."""
    from scripts.run_mini_coursework_submission import PROOFS

    screenshots = [proof for proof in PROOFS if proof.proof_type == "screenshot"]
    assert screenshots
    for proof in screenshots:
        source = REPO_ROOT / proof.source
        assert source.is_file(), f"Missing submission screenshot source: {source}"
        assert source.stat().st_size > 20_000, f"Screenshot is too small: {source}"


def test_submission_builder_seals_the_scoring_contract() -> None:
    """The package must contain the rubric config and use criterion-specific proof names."""
    from scripts.run_mini_coursework_submission import PROOFS

    targets = {proof.target for proof in PROOFS}
    assert "config/rubric-requirements.yaml" in targets
    assert "screenshots/flink-dedup.png" in targets
    assert "screenshots/flink-restart.png" not in targets
