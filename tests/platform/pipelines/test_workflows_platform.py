"""Verify the reusable platform workflow and its callers."""

from __future__ import annotations

import hashlib
import json
import shlex
from pathlib import Path

import pytest
import yaml

from scripts.generate_platform_requirement_tests import generate
from tests.platform.requirements.conftest import MATRIX
from tests.platform.requirements.test_llm_ac_12_cicd import (
    test_requirement_evidence_contract as _validate_cicd_requirement,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

REUSABLE = WORKFLOWS_DIR / "phase2-ci.yaml"
RAG_CALLER = WORKFLOWS_DIR / "phase2-rag-pipeline.yaml"
RAG_CICD_RUBRIC_ID = "LLM-ci-cd-ci-cd-cho-rag-data-pipeline"
CALLERS = (
    RAG_CALLER,
    WORKFLOWS_DIR / "phase2-stream-feature-offline.yaml",
    WORKFLOWS_DIR / "phase2-stream-feature-online.yaml",
    WORKFLOWS_DIR / "phase2-agent-feature.yaml",
    WORKFLOWS_DIR / "phase2-agent-drift.yaml",
    WORKFLOWS_DIR / "phase2-agent-coordinator.yaml",
    WORKFLOWS_DIR / "phase2-drift-mcp.yaml",
    WORKFLOWS_DIR / "phase2-phase1-pipeline.yaml",
    WORKFLOWS_DIR / "phase2-web.yaml",
)
# platform-feature-api.yaml / platform-drift-api.yaml deleted 2026-08-14 — ML-track
# deployables removed from the catalog; their standalone per-app CI workflows
# would fail on push (no GHCR write:packages scope) with zero LLM benefit.

# Pinned 2026-08-08 (slice 4D) — a platform .I change must update this
# constant deliberately, not as a silent side effect of an unrelated diff.
CI_YML_SHA256 = "41f107015008d9e3123725a4cfe82494542e98e4a86619d01fc9805ce82cc4c6"


def test_all_phase2_workflow_files_exist() -> None:
    assert REUSABLE.is_file()
    for caller in CALLERS:
        assert caller.is_file(), caller


@pytest.mark.parametrize("path", [REUSABLE, *CALLERS], ids=lambda p: p.name)
def test_every_workflow_file_parses_as_yaml(path: Path) -> None:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)


def test_reusable_workflow_is_workflow_call() -> None:
    parsed = yaml.safe_load(REUSABLE.read_text(encoding="utf-8"))
    # YAML parses the bare key `on` as the boolean True unless quoted.
    on_block = parsed.get("on", parsed.get(True))
    assert "workflow_call" in on_block


REQUIRED_INPUTS = ("deployables",)


def test_release_uses_the_workflow_token_without_publishing_on_pull_requests() -> None:
    parsed = yaml.safe_load(REUSABLE.read_text(encoding="utf-8"))
    on_block = parsed.get("on", parsed.get(True))
    inputs = on_block["workflow_call"]["inputs"]
    for required_input in REQUIRED_INPUTS:
        assert inputs[required_input]["required"] is True
    assert "secrets" not in on_block["workflow_call"]

    build = parsed["jobs"]["build"]
    assert build["permissions"]["packages"] == "write"
    steps = build["steps"]
    login = next(step for step in steps if step.get("uses", "").startswith("docker/login-action@"))
    publish = next(
        step for step in steps if step.get("uses", "").startswith("docker/build-push-action@")
    )
    sign = next(step for step in steps if step.get("name") == "Sign immutable image digest")
    non_pr = "github.event_name != 'pull_request'"
    assert login["with"]["password"] == "${{ secrets.GITHUB_TOKEN }}"
    assert login["if"] == sign["if"] == non_pr
    assert publish["with"]["push"] == "${{ " + non_pr + " }}"


@pytest.mark.parametrize("path", CALLERS, ids=lambda p: p.name)
def test_each_caller_supplies_every_required_input(path: Path) -> None:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    supplied = parsed["jobs"]["ci"]["with"]
    missing = [name for name in REQUIRED_INPUTS if name not in supplied]
    assert not missing, f"{path.name} is missing required inputs: {missing}"
    deployables = json.loads(supplied["deployables"])
    assert deployables and isinstance(deployables, list)
    for deployable in deployables:
        assert {
            "name",
            "image_context",
            "dockerfile",
            "test_selector",
            "lint_paths",
        } == set(deployable)
    assert "secrets" not in parsed["jobs"]["ci"]


@pytest.mark.parametrize("path", CALLERS, ids=lambda p: p.name)
def test_each_caller_references_the_reusable_workflow(path: Path) -> None:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert parsed["jobs"].keys() == {"ci"}
    ci_job = parsed["jobs"]["ci"]
    assert ci_job["uses"] == "./.github/workflows/phase2-ci.yaml"


@pytest.mark.parametrize("path", CALLERS, ids=lambda p: p.name)
def test_each_caller_allows_keyless_signing(path: Path) -> None:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert parsed["permissions"]["packages"] == "write"
    assert parsed["permissions"]["id-token"] == "write"


def test_each_caller_declares_a_distinct_paths_trigger() -> None:
    path_sets = []
    for caller in CALLERS:
        parsed = yaml.safe_load(caller.read_text(encoding="utf-8"))
        on_block = parsed.get("on", parsed.get(True))
        push_paths = frozenset(on_block["push"]["paths"])
        assert push_paths == frozenset(on_block["pull_request"]["paths"]), caller
        own_path = caller.relative_to(REPO_ROOT).as_posix()
        assert own_path in push_paths, f"{caller.name} must run when its workflow file changes"
        path_sets.append(push_paths - {own_path})
    # Ignore self-triggers when checking that each caller targets distinct source paths.
    assert len(set(path_sets)) == len(path_sets)


def test_rag_caller_runs_workflow_checks_with_history() -> None:
    parsed = yaml.safe_load(RAG_CALLER.read_text(encoding="utf-8"))
    on_block = parsed.get("on", parsed.get(True))
    assert ".github/workflows/phase2-*.yaml" in on_block["push"]["paths"]
    deployable = json.loads(parsed["jobs"]["ci"]["with"]["deployables"])[0]
    selector = shlex.split(deployable["test_selector"])
    assert "tests/platform/pipelines" in selector
    assert "tests/platform/requirements/test_llm_ac_12_cicd.py" in selector
    parity_check = (
        "tests/platform/test_rubric_matrix.py::TestRubricMatrix::"
        "test_matrix_csv_matches_generator_exactly"
    )
    assert parity_check in selector
    assert {
        "test_workflows_platform",
        "test_llm_ac_12_cicd",
        "test_matrix_csv_matches_generator_exactly",
    } <= set(selector[selector.index("-k") + 1].split(" or "))
    steps = yaml.safe_load(REUSABLE.read_text(encoding="utf-8"))["jobs"]["test"]["steps"]
    checkout = next(step for step in steps if step.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["fetch-depth"] == 0


def test_historical_rag_workflow_revision_matches_executed_run() -> None:
    row = MATRIX[RAG_CICD_RUBRIC_ID]
    assert row["evidence_type"] == "executed"
    assert row["artifact_path"] == REUSABLE.relative_to(REPO_ROOT).as_posix()
    expected = "historical_yaml_path:41940f6c1ed1fa16a80ef886b95302e6c53d8239:jobs.gitops-pr"
    assert row["behavioral_assertion"] == expected
    _validate_cicd_requirement(RAG_CICD_RUBRIC_ID)


def test_canonical_rag_requirement_rejects_receipt_stamp_as_workflow_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        MATRIX[RAG_CICD_RUBRIC_ID],
        "behavioral_assertion",
        "historical_yaml_path:9ec6f065276d316bad1e308c88028c5662edc4db:jobs.gitops-pr",
    )
    with pytest.raises(AssertionError, match="does not match Actions run 31405317841 workflow SHA"):
        _validate_cicd_requirement(RAG_CICD_RUBRIC_ID)


@pytest.mark.parametrize(
    ("original", "replacement", "error"),
    [
        (
            "source_sha: 9ec6f065276d316bad1e308c88028c5662edc4db",
            "source_sha: 41940f6c1ed1fa16a80ef886b95302e6c53d8239",
            "receipt source_sha does not match",
        ),
        (
            "actions/runs/31405317841)",
            "actions/runs/31405317842)",
            "receipt actual_result does not link to Actions run 31405317841",
        ),
    ],
    ids=["restamped-receipt", "different-run-url"],
)
def test_canonical_rag_requirement_rejects_changed_receipt_association(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, original: str, replacement: str, error: str
) -> None:
    row = MATRIX[RAG_CICD_RUBRIC_ID]
    receipt = REPO_ROOT / row["evidence_path"]
    text = receipt.read_text(encoding="utf-8")
    assert original in text
    edited_receipt = tmp_path / receipt.name
    edited_receipt.write_text(text.replace(original, replacement, 1), encoding="utf-8")
    monkeypatch.setitem(row, "evidence_path", str(edited_receipt))
    with pytest.raises(AssertionError, match=error):
        _validate_cicd_requirement(RAG_CICD_RUBRIC_ID)


def test_canonical_rag_requirement_rejects_missing_receipt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setitem(MATRIX[RAG_CICD_RUBRIC_ID], "evidence_path", str(tmp_path / "missing.md"))
    with pytest.raises(AssertionError, match="missing receipt"):
        _validate_cicd_requirement(RAG_CICD_RUBRIC_ID)


def test_generated_requirement_tests_match_generator() -> None:
    assert generate(check=True) == 0


def test_each_caller_has_a_unique_pipeline_name() -> None:
    names = []
    for caller in CALLERS:
        parsed = yaml.safe_load(caller.read_text(encoding="utf-8"))
        deployables = json.loads(parsed["jobs"]["ci"]["with"]["deployables"])
        names.extend(deployable["name"] for deployable in deployables)
    assert len(names) == len(set(names))


def test_reusable_workflow_signs_images_without_deploying_to_a_cluster() -> None:
    text = REUSABLE.read_text(encoding="utf-8")
    assert "fromJSON(inputs.deployables)" in text
    assert "id-token: write" in text
    assert "cosign sign --yes" in text
    assert yaml.safe_load(text)["jobs"].keys() == {"lint", "test", "phase5-verification", "build"}


def test_phase5_verification_blocks_image_builds() -> None:
    parsed = yaml.safe_load(REUSABLE.read_text(encoding="utf-8"))

    assert parsed["jobs"]["phase5-verification"]["needs"] == "test"
    assert parsed["jobs"]["build"]["needs"] == ["test", "phase5-verification"]


def test_ci_yml_is_byte_unchanged() -> None:
    ci_yml = WORKFLOWS_DIR / "ci.yml"
    digest = hashlib.sha256(ci_yml.read_bytes()).hexdigest()
    assert digest == CI_YML_SHA256, (
        "ci.yml (platform .ate) changed — if this is a deliberate platform .I "
        "change, update CI_YML_SHA256 explicitly; if not, revert it"
    )


def test_ci_yml_paths_are_not_narrowed_by_this_slice() -> None:
    """platform's CI must keep running on every push — this slice's new
    workflows must not have added a `paths:` filter to ci.yml itself."""
    parsed = yaml.safe_load((WORKFLOWS_DIR / "ci.yml").read_text(encoding="utf-8"))
    on_block = parsed.get("on", parsed.get(True))
    assert "paths" not in on_block.get("push", {})
    assert "paths" not in on_block.get("pull_request", {})
