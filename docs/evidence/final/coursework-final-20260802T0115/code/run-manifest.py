"""Create and verify cryptographically correlated evidence manifests."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or str(path) in {".", ""}:
        raise ValueError(f"artifact must use a safe relative path: {value!r}")
    return path


def _config_hash(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted((item.resolve() for item in paths), key=str):
        if not path.is_file():
            raise FileNotFoundError(f"config file not found: {path}")
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


@dataclass(frozen=True)
class ArtifactRecord:
    """Immutable hash record for one evidence artifact."""

    path: str
    proof_type: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class RunManifest:
    """Metadata that binds all evidence artifacts to one reproducible run."""

    schema_version: int
    run_id: str
    git_sha: str
    config_sha256: str
    started_at: str
    completed_at: str
    artifacts: tuple[ArtifactRecord, ...]

    def write(self, path: Path) -> None:
        """Write a deterministic JSON representation of this manifest."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @classmethod
    def read(cls, path: Path) -> RunManifest:
        """Load and minimally validate a manifest from disk."""
        data = json.loads(path.read_text(encoding="utf-8"))
        artifacts = tuple(ArtifactRecord(**item) for item in data.pop("artifacts"))
        manifest = cls(artifacts=artifacts, **data)
        if manifest.schema_version != 1:
            raise ValueError(f"unsupported manifest schema: {manifest.schema_version}")
        return manifest

    def verify(self, evidence_dir: Path) -> list[str]:
        """Return integrity errors without mutating the evidence package."""
        errors: list[str] = []
        seen: set[str] = set()
        for artifact in self.artifacts:
            try:
                relative = _artifact_path(artifact.path)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if artifact.path in seen:
                errors.append(f"duplicate artifact path: {artifact.path}")
                continue
            seen.add(artifact.path)
            path = evidence_dir / Path(*relative.parts)
            if not path.is_file():
                errors.append(f"artifact missing: {artifact.path}")
                continue
            actual = _sha256_file(path)
            if actual != artifact.sha256:
                errors.append(f"artifact hash mismatch: {artifact.path}")
            elif path.stat().st_size != artifact.size_bytes:
                errors.append(f"artifact size mismatch: {artifact.path}")
        return errors


def build_run_manifest(
    *,
    evidence_dir: Path,
    run_id: str,
    git_sha: str,
    config_paths: Iterable[Path],
    artifacts: Iterable[tuple[str, str]],
    started_at: str | None = None,
    completed_at: str | None = None,
) -> RunManifest:
    """Hash a completed evidence set and return its correlated manifest."""
    if not run_id.strip():
        raise ValueError("run_id must not be empty")
    if not git_sha.strip():
        raise ValueError("git_sha must not be empty")
    now = datetime.now(UTC).isoformat()
    records: list[ArtifactRecord] = []
    seen: set[str] = set()
    for value, proof_type in artifacts:
        relative = _artifact_path(value)
        normalized = relative.as_posix()
        if normalized in seen:
            raise ValueError(f"duplicate artifact path: {normalized}")
        seen.add(normalized)
        path = evidence_dir / Path(*relative.parts)
        if not path.is_file():
            raise FileNotFoundError(f"artifact file not found: {normalized}")
        records.append(
            ArtifactRecord(normalized, proof_type, _sha256_file(path), path.stat().st_size)
        )
    return RunManifest(
        schema_version=1,
        run_id=run_id,
        git_sha=git_sha,
        config_sha256=_config_hash(config_paths),
        started_at=started_at or now,
        completed_at=completed_at or now,
        artifacts=tuple(records),
    )
