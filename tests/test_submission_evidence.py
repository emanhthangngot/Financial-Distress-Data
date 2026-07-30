from __future__ import annotations

import importlib
from pathlib import Path


def test_submission_maps_all_rubric_criteria_and_proof_paths():
    module = importlib.import_module("scripts.run_mini_coursework_submission")
    audit = importlib.import_module("src.evidence.rubric_audit")
    requirements = audit.load_requirements(Path("configs/rubric-requirements.yaml"))
    proof_types = {proof.target: proof.proof_type for proof in module.PROOFS}
    proof_types["logs/quality-gates.txt"] = "log"

    assert set(module.CRITERIA) == {criterion.id for criterion in requirements.criteria}
    for criterion in requirements.criteria:
        entry = module.CRITERIA[criterion.id]
        assert entry["status"] == "accepted"
        actual_types = {proof_types[path] for path in entry["artifacts"]}
        assert set(criterion.required_proof_types) <= actual_types


def test_all_submission_sources_exist_and_screenshots_are_reviewable():
    module = importlib.import_module("scripts.run_mini_coursework_submission")

    for proof in module.PROOFS:
        source = module.ROOT / proof.source
        assert source.is_file()
        assert source.stat().st_size > 0
        if proof.proof_type == "screenshot":
            width, height = module._png_dimensions(source)
            assert width >= 800
            assert height >= 300
