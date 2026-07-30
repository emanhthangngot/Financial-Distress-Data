from __future__ import annotations

import importlib
import inspect
from pathlib import Path

import yaml


def _audit_module():
    return importlib.import_module("src.evidence.rubric_audit")


def _manifest_module():
    return importlib.import_module("src.evidence.run_manifest")


def _write_requirements(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "allowed_proof_types": ["document", "metrics", "screenshot"],
                "criteria": [
                    {
                        "id": "R01",
                        "title": "Documentation",
                        "category": "docs",
                        "points": 3,
                        "required_proof_types": ["document", "screenshot"],
                    },
                    {
                        "id": "R02",
                        "title": "Metrics",
                        "category": "processing",
                        "points": 2,
                        "required_proof_types": ["metrics"],
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _write_complete_evidence(tmp_path: Path, run_id: str = "run-001") -> tuple[Path, Path]:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    files = {
        "docs.md": ("document", "docs\n"),
        "ui.png": ("screenshot", "png-placeholder\n"),
        "metrics.json": ("metrics", '{"value": 1}\n'),
    }
    for name, (_, content) in files.items():
        (evidence_dir / name).write_text(content, encoding="utf-8")

    manifest = _manifest_module().build_run_manifest(
        evidence_dir=evidence_dir,
        run_id=run_id,
        git_sha="abc1234",
        config_paths=[],
        artifacts=[(name, proof_type) for name, (proof_type, _) in files.items()],
    )
    manifest.write(evidence_dir / "run-manifest.json")
    evidence = {
        "schema_version": 1,
        "run_id": run_id,
        "criteria": {
            "R01": {"status": "accepted", "artifacts": ["docs.md", "ui.png"]},
            "R02": {"status": "accepted", "artifacts": ["metrics.json"]},
        },
    }
    (evidence_dir / "rubric-evidence.yaml").write_text(
        yaml.safe_dump(evidence, sort_keys=False), encoding="utf-8"
    )
    requirements = tmp_path / "requirements.yaml"
    _write_requirements(requirements)
    return evidence_dir, requirements


def test_repository_rubric_registry_has_45_unique_criteria_and_100_points():
    module = _audit_module()

    requirements = module.load_requirements(Path("configs/rubric-requirements.yaml"))

    assert len(requirements.criteria) == 45
    assert len({criterion.id for criterion in requirements.criteria}) == 45
    assert [criterion.id for criterion in requirements.criteria] == [
        f"R{number:02d}" for number in range(1, 46)
    ]
    assert requirements.total_points == 100


def test_real_e2e_runner_wires_shared_run_id_and_manifest():
    module = importlib.import_module("scripts.run_stage1_real_e2e")
    source = inspect.getsource(module.main)

    assert "STAGE1_EVIDENCE_RUN_ID" in source
    assert "build_run_manifest" in source


def test_gitignore_allows_curated_evidence_screenshots():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "!docs/evidence/screenshots/**/*.png" in gitignore
    assert "!docs/evidence/screenshots/**/*.jpg" in gitignore
    assert "!docs/evidence/final/**/*.png" in gitignore
    assert "!docs/evidence/final/**/*.jpg" in gitignore


def test_complete_correlated_evidence_receives_full_score(tmp_path: Path):
    module = _audit_module()
    evidence_dir, requirements = _write_complete_evidence(tmp_path)

    report = module.audit_rubric(requirements, evidence_dir)

    assert report.status == "pass"
    assert report.earned_points == 5
    assert report.total_points == 5
    assert report.failed_criteria == []
    assert report.errors == []


def test_missing_proof_only_fails_its_criterion(tmp_path: Path):
    module = _audit_module()
    evidence_dir, requirements = _write_complete_evidence(tmp_path)
    evidence = yaml.safe_load((evidence_dir / "rubric-evidence.yaml").read_text())
    evidence["criteria"]["R01"]["artifacts"] = ["docs.md"]
    (evidence_dir / "rubric-evidence.yaml").write_text(
        yaml.safe_dump(evidence, sort_keys=False), encoding="utf-8"
    )

    report = module.audit_rubric(requirements, evidence_dir)

    assert report.status == "fail"
    assert report.earned_points == 2
    assert report.failed_criteria == ["R01"]
    assert report.criteria[0].missing_proof_types == ["screenshot"]
    assert report.criteria[1].status == "accepted"


def test_mixed_run_ids_are_rejected_before_scoring(tmp_path: Path):
    module = _audit_module()
    evidence_dir, requirements = _write_complete_evidence(tmp_path, run_id="run-001")
    evidence = yaml.safe_load((evidence_dir / "rubric-evidence.yaml").read_text())
    evidence["run_id"] = "run-002"
    (evidence_dir / "rubric-evidence.yaml").write_text(
        yaml.safe_dump(evidence, sort_keys=False), encoding="utf-8"
    )

    report = module.audit_rubric(requirements, evidence_dir)

    assert report.status == "fail"
    assert report.earned_points == 0
    assert report.errors == ["run_id mismatch: manifest=run-001 evidence=run-002"]


def test_rendered_index_links_each_artifact(tmp_path: Path):
    module = _audit_module()
    evidence_dir, requirements = _write_complete_evidence(tmp_path)
    report = module.audit_rubric(requirements, evidence_dir)

    rendered = module.render_evidence_index(report, evidence_dir_name="evidence")

    assert "# Mini-Coursework Evidence Index" in rendered
    assert "[docs.md](evidence/docs.md)" in rendered
    assert "[ui.png](evidence/ui.png)" in rendered
    assert "5/5" in rendered
