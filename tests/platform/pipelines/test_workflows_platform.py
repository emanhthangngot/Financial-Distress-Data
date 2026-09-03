"""Pins the platform .eusable workflow and its list-driven callers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

REUSABLE = WORKFLOWS_DIR / "platform-ci.yaml"
CALLERS = (
    WORKFLOWS_DIR / "platform-rag-pipeline.yaml",
    WORKFLOWS_DIR / "platform-stream-feature-offline.yaml",
    WORKFLOWS_DIR / "platform-stream-feature-online.yaml",
    WORKFLOWS_DIR / "platform-agent-feature.yaml",
    WORKFLOWS_DIR / "platform-agent-drift.yaml",
    WORKFLOWS_DIR / "platform-agent-coordinator.yaml",
)
# platform-feature-api.yaml / platform-drift-api.yaml deleted 2026-08-14 — ML-track
# deployables removed from the catalog; their standalone per-app CI workflows
# would fail on push (no GHCR write:packages scope) with zero LLM benefit.

# Pinned 2026-08-08 (slice 4D) — a platform .I change must update this
# constant deliberately, not as a silent side effect of an unrelated diff.
CI_YML_SHA256 = "a24aceb639dbef1b00f35e720d5327afb5f97e21d20af2f2309448957ff72904"


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


def test_reusable_workflow_requires_pipeline_name_and_secrets() -> None:
    parsed = yaml.safe_load(REUSABLE.read_text(encoding="utf-8"))
    on_block = parsed.get("on", parsed.get(True))
    inputs = on_block["workflow_call"]["inputs"]
    secrets = on_block["workflow_call"]["secrets"]
    for required_input in REQUIRED_INPUTS:
        assert inputs[required_input]["required"] is True
    for required_secret in ("GHCR_TOKEN", "GITOPS_PAT"):
        assert secrets[required_secret]["required"] is True


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
            "gitops_path",
            "gitops_target_type",
            "gitops_target_kind",
            "gitops_target_selector",
        } <= set(deployable)


@pytest.mark.parametrize("path", CALLERS, ids=lambda p: p.name)
def test_each_caller_references_the_reusable_workflow(path: Path) -> None:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    ci_job = parsed["jobs"]["ci"]
    assert ci_job["uses"] == "./.github/workflows/platform-ci.yaml"


@pytest.mark.parametrize("path", CALLERS, ids=lambda p: p.name)
def test_each_caller_allows_keyless_signing(path: Path) -> None:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert parsed["permissions"]["id-token"] == "write"


def test_each_caller_declares_a_distinct_paths_trigger() -> None:
    path_sets = []
    for caller in CALLERS:
        parsed = yaml.safe_load(caller.read_text(encoding="utf-8"))
        on_block = parsed.get("on", parsed.get(True))
        path_sets.append(frozenset(on_block["push"]["paths"]))
    # Distinct callers must not all trigger on the exact same file set —
    # otherwise every push runs all three "separately named" pipelines
    # regardless of what actually changed.
    assert len(set(path_sets)) == len(path_sets)


def test_each_caller_has_a_unique_pipeline_name() -> None:
    names = []
    for caller in CALLERS:
        parsed = yaml.safe_load(caller.read_text(encoding="utf-8"))
        deployables = json.loads(parsed["jobs"]["ci"]["with"]["deployables"])
        names.extend(deployable["name"] for deployable in deployables)
    assert len(names) == len(set(names))


def test_reusable_workflow_signs_and_consumes_digest_handoffs() -> None:
    text = REUSABLE.read_text(encoding="utf-8")
    assert "fromJSON(inputs.deployables)" in text
    assert "id-token: write" in text
    assert "cosign sign --yes" in text
    assert "actions/download-artifact@v4" in text
    assert "gitops_values_path" not in text
    assert "pipelines/${" not in text


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
