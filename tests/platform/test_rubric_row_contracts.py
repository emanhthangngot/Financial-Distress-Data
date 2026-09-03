"""Per-rubric-row contract tests (Phase 2).

Every scored rubric row gets its own parametrized test keyed by ``rubric_id``
so the matrix's ``test`` field — ``pytest tests/platform -k '<rubric_id>'`` —
collects and runs at least one real test (exit 0, not pytest's "no tests ran"
exit code 5). Each test re-derives the row contract from the same source of
truth the generator uses, so a missing field or an invalid owner fails loudly
with the row's id instead of being silently deselected.

Also proves *all* validation commands are runnable: a single collection pass
asserts every rubric_id appears in at least one collected node id, and the
first row's command is executed end-to-end as a smoke test.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from _platform_rubric_items import EXPLICIT_IMPLEMENTATION, ITEMS  # noqa: E402

VALID_OWNERS = {"ml_engineer", "llm_engineer", "data_engineer", "platform_operator"}
VALID_EVIDENCE_TYPES = {"executed", "design_only", "stretch"}

ARTIFACT_ROOTS = {
    "source": (
        "src/ml/",
        "src/drift/",
        "src/llm/",
        "src/agents/",
        "apps/",
        "dags/",
        ".github/workflows/",
        "notebooks/",
        "tests/platform/requirements/",
        "docs/phase2/",
    ),
    "gitops": (
        ".github/workflows/",
        "terraform/",
        "ansible/",
        "charts/",
        "platform/",
        "argocd/",
    ),
}

ITEMS_BY_ID = {item.rubric_id: item for item in ITEMS}
RUBRIC_IDS = list(ITEMS_BY_ID)


def _run(*argv: str) -> subprocess.CompletedProcess[str]:
    """Run pytest for the phase-2 suite and return the completed process."""
    return subprocess.run(
        [sys.executable, "-m", "pytest", *argv],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.parametrize("rid", RUBRIC_IDS, ids=RUBRIC_IDS)
def test_rubric_row_contract(rid: str) -> None:
    """Every field the matrix contract requires must be present and valid."""
    item = ITEMS_BY_ID[rid]
    assert item.track in {"ML", "LLM"}, f"{rid}: track {item.track!r} invalid"
    assert item.points > 0, f"{rid}: points must be > 0"
    for field in ("section", "requirement", "proof", "deliverables"):
        assert getattr(item, field).strip(), f"{rid}: missing '{field}'"
    assert item.owner in VALID_OWNERS, f"{rid}: owner {item.owner!r} not a recognized role"
    assert (
        item.evidence_type in VALID_EVIDENCE_TYPES
    ), f"{rid}: evidence_type {item.evidence_type!r} invalid"
    assert item.evidence_path.startswith(
        "docs/phase2/evidence/"
    ), f"{rid}: evidence_path {item.evidence_path!r} not under docs/phase2/evidence/"
    assert item.acceptance_id, f"{rid}: missing acceptance_id"
    assert item.source_file.startswith("docs/Coursework Tracking"), f"{rid}: source_file invalid"
    assert item.source_row_index > 0, f"{rid}: source_row_index invalid"
    assert re.fullmatch(r"[0-9a-f]{64}", item.source_digest), f"{rid}: source_digest invalid"
    expected_validation = (
        "pytest tests/platform/requirements/test_"
        f"{item.acceptance_id.lower().replace('-', '_')}.py -k '{rid}'"
    )
    assert (
        item.validation_command == expected_validation
    ), f"{rid}: validation_command={item.validation_command!r} != {expected_validation!r}"
    assert item.artifact_path, f"{rid}: missing artifact_path"
    assert item.artifact_repo in ARTIFACT_ROOTS, f"{rid}: artifact_repo invalid"
    assert item.artifact_path.startswith(
        ARTIFACT_ROOTS[item.artifact_repo]
    ), f"{rid}: artifact_path {item.artifact_path!r} invalid for {item.artifact_repo}"
    assert not item.artifact_path.endswith("/"), f"{rid}: artifact_path must be a file"
    expected_test = f"pytest tests/platform -k '{rid}'"
    assert item.test == expected_test, f"{rid}: test={item.test!r} != {expected_test!r}"
    assert not re.search(r"row[-_]?\d+$", rid), f"{rid}: ID looks like a spreadsheet line number"
    mapped_owner, mapped_repo, mapped_path = EXPLICIT_IMPLEMENTATION[rid]
    assert (item.owner, item.artifact_repo, item.artifact_path) == (
        mapped_owner,
        mapped_repo,
        mapped_path,
    ), f"{rid}: generated row diverges from reviewed explicit implementation map"


def test_executed_rows_prove_a_real_artifact() -> None:
    """An executed row must point at an implementation artifact on disk.

    A row can only claim `executed` evidence when the implementation it names
    actually exists in the working tree — otherwise the per-row validation is a
    false positive (the Coordinator-Agent-style gap the reviewer flagged). The
    real matrix is design_only at phase-01, so this guard bites at phase-08.
    """
    missing = [
        item.rubric_id
        for item in ITEMS
        if item.evidence_type == "executed"
        and item.artifact_repo == "source"
        and not (REPO_ROOT / item.artifact_path).is_file()
    ]
    assert not missing, (
        "Executed rows must have their implementation artifact on disk, " f"missing for: {missing}"
    )


def test_artifact_path_domain_consistency() -> None:
    """The artifact root must match the row's owner domain.

    Each rubric_id's artifact_path is derived from the row's owner + content
    domain. This test re-derives the expected root independently so a row
    mis-mapped to the wrong Phase 2 root (e.g. an agent row parked under
    src/ml/) fails loudly.
    """
    agent_domains = {
        "LLM-1-coordinator-agent-i-u-ph-i-2-agent-tr-n",
        "LLM-ci-cd-agent-k-o-d-li-u",
        "LLM-web-api-cho-real-time-dri-1-agent-s-d-ng-mcp-tool-tr-n-v",
        "LLM-demonstrate-basic-underst-jupyter-notebook-demonstrate-a",
    }
    drift_domains = {
        "LLM-improve-the-data-generato-simulate-data-drift",
        "ML-web-api-cho-real-time-dri-c-s-d-ng-fastapi-data-validati",
        "ML-observability-airflow-data-drift-pipeline-to",
    }
    platform_domains = {
        "LLM-routing-gateway-ui-test-agent",
        "ML-security-centralize-secret-management",
        "LLM-iac-d-ng-terraform-setup-gke-ho-c-",
    }
    for rid, item in ITEMS_BY_ID.items():
        if rid in agent_domains:
            assert item.artifact_path.startswith(
                ("src/agents/", "notebooks/", ".github/workflows/")
            ), f"{rid}: agent row must map to src/agents/, got {item.artifact_path!r}"
        if rid in drift_domains:
            assert item.artifact_path.startswith(
                ("src/drift/", "dags/", "apps/drift-api/", "apps/drift-mcp/")
            ), f"{rid}: drift row must map to drift code/DAG, got {item.artifact_path!r}"
        if rid in platform_domains:
            assert item.artifact_repo == "gitops", f"{rid}: platform row must map to GitOps"


def test_every_validation_command_collects_at_least_one_test() -> None:
    """Every row's `pytest tests/platform -k '<rubric_id>'` must select a test.

    pytest `-k` matches a bare keyword as a case-sensitive substring of the
    collected node id, so asserting each rubric_id appears in some node id is
    equivalent to that command collecting at least one test (exit != 5).
    """
    proc = _run("tests/platform", "--collect-only", "-q")
    assert (
        proc.returncode == 0
    ), f"pytest --collect-only failed: {proc.stdout[-400:]}{proc.stderr[-400:]}"
    nodeids = [line.strip() for line in proc.stdout.splitlines() if "::" in line]
    missing = [rid for rid in RUBRIC_IDS if not any(rid in nid for nid in nodeids)]
    assert not missing, (
        f"No test matches `-k` for rubric ids: {missing}\n"
        "Add a per-row contract test so each validation command runs a real test."
    )


def test_first_row_validation_command_runs() -> None:
    """End-to-end smoke: the first row's exact `test` command runs and passes."""
    rid = RUBRIC_IDS[0]
    proc = _run("tests/platform", "-k", rid, "-q")
    assert proc.returncode == 0, (
        f"`pytest tests/platform -k '{rid}'` failed (rc {proc.returncode}): "
        f"{proc.stdout[-400:]}{proc.stderr[-400:]}"
    )
