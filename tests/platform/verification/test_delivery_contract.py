from __future__ import annotations

import pytest

from scripts.ci.catalog import load_catalog
from scripts.ci.delivery import DeliveryContractError, build_handoff, catalog_summary

SOURCE_SHA = "a" * 40
GITOPS_SHA = "b" * 40
CANDIDATE = "sha256:" + "1" * 64
PREVIOUS = "sha256:" + "2" * 64


def test_promotion_handoff_is_digest_only_and_redacted() -> None:
    handoff = build_handoff(
        deployable="feature-agent",
        image_repository="ghcr.io/example/feature-agent",
        image_digest=CANDIDATE,
        source_sha=SOURCE_SHA,
        gitops_base_sha=GITOPS_SHA,
        jenkins_build_id="build-42",
        metadata={"api_token": "secret-value", "suite": "focused"},
    )

    assert handoff["image"] == f"ghcr.io/example/feature-agent@{CANDIDATE}"
    assert handoff["gitops"] == {
        "operation": "open_pull_request",
        "mutation": "digest_only",
        "mutator": "argo-cd-after-merge",
    }
    assert handoff["metadata"] == {"api_token": "[REDACTED]", "suite": "focused"}
    assert "secret-value" not in str(handoff)


def test_rollback_selects_prior_digest_and_keeps_candidate_attributable() -> None:
    handoff = build_handoff(
        deployable="feature-agent",
        image_repository="ghcr.io/example/feature-agent",
        image_digest=CANDIDATE,
        previous_digest=PREVIOUS,
        source_sha=SOURCE_SHA,
        gitops_base_sha=GITOPS_SHA,
        jenkins_build_id="build-43",
        action="rollback",
    )

    assert handoff["action"] == "rollback"
    assert handoff["artifact_digest"] == PREVIOUS
    assert handoff["image"].endswith("@" + PREVIOUS)
    assert handoff["source_sha"] == SOURCE_SHA
    assert handoff["rolled_back_from_digest"] == CANDIDATE


def test_handoff_rejects_lane_mismatch() -> None:
    with pytest.raises(DeliveryContractError, match="belongs to lane"):
        build_handoff(
            deployable="feature-agent",
            lane="app-ci",
            image_repository="ghcr.io/example/feature-agent",
            image_digest=CANDIDATE,
            source_sha=SOURCE_SHA,
            gitops_base_sha=GITOPS_SHA,
            jenkins_build_id="build-45",
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"image_digest": "latest"},
        {"image_digest": "sha256:" + "A" * 64},
        {"image_digest": CANDIDATE, "source_sha": "short"},
        {"image_digest": CANDIDATE, "gitops_base_sha": "../" + "b" * 38},
    ],
)
def test_handoff_rejects_mutable_or_unattributable_inputs(kwargs) -> None:
    params = {
        "deployable": "web",
        "image_repository": "ghcr.io/example/web",
        "image_digest": CANDIDATE,
        "source_sha": SOURCE_SHA,
        "gitops_base_sha": GITOPS_SHA,
        "jenkins_build_id": "build-44",
    }
    params.update(kwargs)
    with pytest.raises((DeliveryContractError, ValueError)):
        build_handoff(**params)


def test_catalog_maps_all_deployables_to_delivery_lanes() -> None:
    entries = load_catalog()
    summary = catalog_summary()

    assert summary["lane_count"] == len(entries) == 9
    assert {lane["name"] for lane in summary["lanes"]} == {entry.name for entry in entries}
    assert {lane["kind"] for lane in summary["lanes"]} == {"app-ci", "model-promote"}
