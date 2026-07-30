from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


def _manifest_module():
    return importlib.import_module("src.evidence.run_manifest")


def test_manifest_round_trip_and_verification(tmp_path: Path):
    module = _manifest_module()
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "metrics.json").write_text('{"rows": 10}\n', encoding="utf-8")
    config = tmp_path / "config.yaml"
    config.write_text("seed: 42\n", encoding="utf-8")

    manifest = module.build_run_manifest(
        evidence_dir=evidence_dir,
        run_id="run-001",
        git_sha="abc1234",
        config_paths=[config],
        artifacts=[("metrics.json", "metrics")],
        started_at="2026-07-22T00:00:00+00:00",
        completed_at="2026-07-22T00:01:00+00:00",
    )
    output = evidence_dir / "run-manifest.json"
    manifest.write(output)

    loaded = module.RunManifest.read(output)

    assert loaded == manifest
    assert loaded.verify(evidence_dir) == []
    assert loaded.artifacts[0].path == "metrics.json"
    assert loaded.artifacts[0].proof_type == "metrics"
    assert json.loads(output.read_text(encoding="utf-8"))["run_id"] == "run-001"


def test_manifest_detects_artifact_tampering(tmp_path: Path):
    module = _manifest_module()
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    artifact = evidence_dir / "query.txt"
    artifact.write_text("count=10\n", encoding="utf-8")

    manifest = module.build_run_manifest(
        evidence_dir=evidence_dir,
        run_id="run-001",
        git_sha="abc1234",
        config_paths=[],
        artifacts=[("query.txt", "query_output")],
    )
    artifact.write_text("count=999\n", encoding="utf-8")

    errors = manifest.verify(evidence_dir)

    assert errors == ["artifact hash mismatch: query.txt"]


def test_manifest_rejects_unsafe_or_duplicate_artifact_paths(tmp_path: Path):
    module = _manifest_module()
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "same.txt").write_text("proof\n", encoding="utf-8")

    with pytest.raises(ValueError, match="relative path"):
        module.build_run_manifest(
            evidence_dir=evidence_dir,
            run_id="run-001",
            git_sha="abc1234",
            config_paths=[],
            artifacts=[("../same.txt", "log")],
        )

    with pytest.raises(ValueError, match="duplicate artifact"):
        module.build_run_manifest(
            evidence_dir=evidence_dir,
            run_id="run-001",
            git_sha="abc1234",
            config_paths=[],
            artifacts=[("same.txt", "log"), ("same.txt", "document")],
        )
