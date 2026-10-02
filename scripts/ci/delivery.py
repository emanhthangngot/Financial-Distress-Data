"""Offline-verifiable Jenkins promotion and rollback contracts.

This module prepares evidence and GitOps pull-request payloads; it never calls kubectl,
Argo CD, a registry, or a cloud API.  The merged GitOps revision remains the only cluster
mutator.  Jenkins supplies the build identifier and immutable image digest at runtime.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .catalog import DEFAULT_CATALOG, load_catalog
from .gitops_paths import validate_digest

_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
_SECRET_KEY_RE = re.compile(r"(?:secret|password|token|api[_-]?key|private[_-]?key)", re.I)


class DeliveryContractError(ValueError):
    """Raised when a Jenkins handoff is incomplete or attempts unsafe mutation."""


def _sha40(value: str, name: str) -> str:
    normalized = value.strip()
    if not _SHA40_RE.fullmatch(normalized):
        raise DeliveryContractError(f"{name} must be exactly 40 lowercase hexadecimal characters")
    return normalized


def _required(value: str, name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise DeliveryContractError(f"{name} must not be empty")
    return normalized


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _SECRET_KEY_RE.search(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def build_handoff(
    *,
    deployable: str,
    image_repository: str,
    image_digest: str,
    source_sha: str,
    gitops_base_sha: str,
    jenkins_build_id: str,
    action: str = "promote",
    previous_digest: str | None = None,
    lane: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a redacted, digest-only handoff for a GitOps pull request."""

    if action not in {"promote", "rollback"}:
        raise DeliveryContractError("action must be promote or rollback")
    deployable = _required(deployable, "deployable")
    entries = load_catalog()
    entry = next((item for item in entries if item.name == deployable), None)
    if entry is None:
        raise DeliveryContractError(
            f"deployable is not present in the platform catalog: {deployable}"
        )
    if lane is not None:
        expected_lane = (
            "model-promote"
            if deployable in {"coordinator", "feature-agent", "drift-agent"}
            else "app-ci"
        )
        if lane != expected_lane:
            raise DeliveryContractError(
                f"deployable {deployable!r} belongs to lane {expected_lane!r}, not {lane!r}"
            )
    image_repository = _required(image_repository, "image_repository")
    if any(char.isspace() for char in image_repository) or "@" in image_repository:
        raise DeliveryContractError("image_repository must not contain whitespace or @")
    source_sha = _sha40(source_sha, "source_sha")
    gitops_base_sha = _sha40(gitops_base_sha, "gitops_base_sha")
    jenkins_build_id = _required(jenkins_build_id, "jenkins_build_id")
    candidate_digest = validate_digest(image_digest)
    digest = candidate_digest
    if action == "rollback":
        if previous_digest is None:
            raise DeliveryContractError("rollback requires previous_digest")
        digest = validate_digest(previous_digest)
    elif previous_digest is not None:
        validate_digest(previous_digest)
    return _redact(
        {
            "schema_version": 1,
            "action": action,
            "rolled_back_from_digest": (candidate_digest if action == "rollback" else None),
            "image": f"{image_repository}@{digest}",
            "artifact_digest": digest,
            "source_sha": source_sha,
            "gitops_base_sha": gitops_base_sha,
            "jenkins_build_id": jenkins_build_id,
            "gitops": {
                "operation": "open_pull_request",
                "mutation": "digest_only",
                "mutator": "argo-cd-after-merge",
            },
            "metadata": metadata or {},
        }
    )


def catalog_summary(catalog: Path | str = DEFAULT_CATALOG) -> dict[str, Any]:
    """Return lane metadata without executing a build or touching GitOps."""

    entries = load_catalog(catalog)
    return {
        "schema_version": 1,
        "lane_count": len(entries),
        "lanes": [
            {
                "name": entry.name,
                "kind": (
                    "model-promote"
                    if entry.name in {"coordinator", "feature-agent", "drift-agent"}
                    else "app-ci"
                ),
                "test_selector": entry.test_selector,
                "gitops_target_type": entry.gitops_target_type,
            }
            for entry in entries
        ],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    catalog = subparsers.add_parser("catalog")
    catalog.add_argument("--path", type=Path, default=DEFAULT_CATALOG)

    handoff = subparsers.add_parser("handoff")
    handoff.add_argument("--deployable", required=True)
    handoff.add_argument("--lane", choices=("app-ci", "model-promote"))
    handoff.add_argument("--repository", required=True)
    handoff.add_argument("--digest", required=True)
    handoff.add_argument("--source-sha", required=True)
    handoff.add_argument("--gitops-base-sha", required=True)
    handoff.add_argument("--jenkins-build-id", required=True)
    handoff.add_argument("--output", type=Path)

    rollback = subparsers.add_parser("rollback")
    rollback.add_argument("--deployable", required=True)
    rollback.add_argument("--lane", choices=("app-ci", "model-promote"))
    rollback.add_argument("--repository", required=True)
    rollback.add_argument("--candidate-digest", required=True)
    rollback.add_argument("--previous-digest", required=True)
    rollback.add_argument("--source-sha", required=True)
    rollback.add_argument("--gitops-base-sha", required=True)
    rollback.add_argument("--jenkins-build-id", required=True)
    rollback.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.command == "catalog":
        result = catalog_summary(args.path)
    elif args.command == "handoff":
        result = build_handoff(
            deployable=args.deployable,
            lane=args.lane,
            image_repository=args.repository,
            image_digest=args.digest,
            source_sha=args.source_sha,
            gitops_base_sha=args.gitops_base_sha,
            jenkins_build_id=args.jenkins_build_id,
        )
    else:
        result = build_handoff(
            deployable=args.deployable,
            lane=args.lane,
            image_repository=args.repository,
            image_digest=args.candidate_digest,
            previous_digest=args.previous_digest,
            source_sha=args.source_sha,
            gitops_base_sha=args.gitops_base_sha,
            jenkins_build_id=args.jenkins_build_id,
            action="rollback",
        )
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.command != "catalog" and args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
