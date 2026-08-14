"""Deterministic provenance manifests for ML training runs.

The module intentionally has no MLflow, cloud SDK, or git dependency at import
time.  A manifest is a small, serialisable value object that can be attached to
any tracking backend and hashed to provide an immutable run identity.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def current_source_sha(cwd: str | None = None) -> str:
    """Return the current git commit when available, or ``"unknown"``.

    Git is invoked lazily and failures are represented explicitly; importing
    the ML package therefore remains safe in Airflow workers without git.
    """

    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return completed.stdout.strip() or "unknown"


def environment_digest(environment: Mapping[str, Any] | None = None) -> str:
    """Hash a stable environment description.

    Callers should pass dependency versions from their lockfile.  The default
    captures only interpreter/platform values, avoiding host-specific noise.
    """

    values = dict(environment or {})
    values.setdefault("python", platform.python_version())
    values.setdefault("platform", platform.platform())
    return _canonical_digest(values)


@dataclass(frozen=True)
class ReproducibilityManifest:
    """Complete provenance required to reproduce a training run."""

    snapshot_id: str
    source_sha: str
    image_digest: str
    environment_digest: str
    data_version: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        return _canonical_digest(self.as_dict())

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


def build_manifest(
    snapshot_id: str,
    *,
    source_sha: str | None = None,
    image_digest: str = "unknown",
    environment: Mapping[str, Any] | None = None,
    data_version: str | None = None,
) -> ReproducibilityManifest:
    """Build a deterministic manifest from explicit lineage inputs."""

    if not snapshot_id or not str(snapshot_id).strip():
        raise ValueError("snapshot_id is required")
    return ReproducibilityManifest(
        snapshot_id=str(snapshot_id),
        source_sha=source_sha or current_source_sha(),
        image_digest=str(image_digest),
        environment_digest=environment_digest(environment),
        data_version=data_version,
    )


def manifest_from_env(snapshot_id: str) -> ReproducibilityManifest:
    """Build a manifest from standard CI/container environment variables."""

    return build_manifest(
        snapshot_id,
        source_sha=os.getenv("SOURCE_SHA") or os.getenv("GIT_SHA"),
        image_digest=os.getenv("IMAGE_DIGEST", "unknown"),
        environment={"requirements_lock_sha": os.getenv("REQUIREMENTS_LOCK_SHA", "unknown")},
        data_version=os.getenv("DATA_VERSION"),
    )


# Explicit alias used by callers that prefer a factory-style name.
create_manifest = build_manifest
