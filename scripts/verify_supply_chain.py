#!/usr/bin/env python3
"""Verify keyless signatures and attestations for one immutable image.

The command performs no network work for ``--help`` and fails with a concise
runtime error when cosign is unavailable. Registry access is intentionally left
to cosign; this keeps the developer tool usable offline for argument and
digest validation tests.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

try:
    from phase2_ci.gitops_paths import GitOpsPathError, validate_digest
except ModuleNotFoundError:  # package import from the repository root
    from scripts.phase2_ci.gitops_paths import GitOpsPathError, validate_digest

DEFAULT_ISSUER = "https://token.actions.githubusercontent.com"
DEFAULT_IDENTITY = r"^repo:emanhthangngot/Financial-Distress-Data:ref:refs/heads/(main|dev)$"


def validate_image_reference(reference: str) -> str:
    """Require an image reference pinned to a lowercase sha256 digest."""

    value = reference.strip()
    if not value or any(char.isspace() for char in value):
        raise ValueError("image reference must be non-empty and contain no whitespace")
    if "@" not in value:
        raise ValueError("image reference must be digest-pinned with @sha256:<64 hex>")
    repository, digest = value.rsplit("@", 1)
    if not repository:
        raise ValueError("image reference is missing its repository")
    try:
        validate_digest(digest)
    except GitOpsPathError as exc:
        raise ValueError(str(exc)) from exc
    return f"{repository}@{digest}"


@dataclass(frozen=True)
class VerificationResult:
    image: str
    signature: Any
    provenance: Any
    sbom: Any


def _cosign_json(args: Sequence[str], *, runner=subprocess.run) -> Any:
    completed = runner(
        ("cosign", *args),
        check=True,
        capture_output=True,
        text=True,
    )
    output = completed.stdout.strip()
    if not output:
        raise RuntimeError(f"cosign returned no verification output for {' '.join(args)}")
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"cosign returned non-JSON verification output for {' '.join(args)}"
        ) from exc
    if not isinstance(parsed, (list, dict)) or not parsed:
        raise RuntimeError(f"cosign returned an empty verification payload for {' '.join(args)}")
    return parsed


def verify_supply_chain(
    image: str,
    *,
    issuer: str = DEFAULT_ISSUER,
    identity_regexp: str = DEFAULT_IDENTITY,
    runner=subprocess.run,
) -> VerificationResult:
    """Verify signature, SLSA provenance, and SPDX SBOM attestations."""

    image = validate_image_reference(image)
    if shutil.which("cosign") is None:
        raise RuntimeError("cosign is required for registry verification but was not found on PATH")
    certificate_args = (
        "--certificate-oidc-issuer",
        issuer,
        "--certificate-identity-regexp",
        identity_regexp,
    )
    signature = _cosign_json(("verify", *certificate_args, image), runner=runner)
    provenance = _cosign_json(
        ("verify-attestation", *certificate_args, "--type", "slsaprovenance", image), runner=runner
    )
    sbom = _cosign_json(
        ("verify-attestation", *certificate_args, "--type", "spdxjson", image), runner=runner
    )
    return VerificationResult(image, signature, provenance, sbom)


def _print_result(result: VerificationResult) -> None:
    print(f"verified image: {result.image}")
    for label, value in (
        ("signature", result.signature),
        ("provenance", result.provenance),
        ("sbom", result.sbom),
    ):
        print(
            f"{label}: {json.dumps(value, sort_keys=True) if not isinstance(value, str) else value}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify cosign signature, SLSA provenance, and SPDX SBOM."
    )
    parser.add_argument(
        "image", help="registry image pinned as repository@sha256:<64 lowercase hex>"
    )
    parser.add_argument("--issuer", default=DEFAULT_ISSUER, help="expected OIDC certificate issuer")
    parser.add_argument(
        "--identity-regexp", default=DEFAULT_IDENTITY, help="expected certificate identity regexp"
    )
    args = parser.parse_args(argv)
    try:
        _print_result(
            verify_supply_chain(
                args.image,
                issuer=args.issuer,
                identity_regexp=args.identity_regexp,
            )
        )
    except (ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"supply-chain verification failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
