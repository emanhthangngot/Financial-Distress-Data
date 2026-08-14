"""Content-addressed local data versioning for training inputs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def _records(data: Any) -> list[dict[str, Any]]:
    if hasattr(data, "to_dict"):
        try:
            return [dict(row) for row in data.to_dict(orient="records")]
        except TypeError:
            pass
    if isinstance(data, dict):
        return [dict(data)]
    return [dict(row) for row in data]


def _canonical_bytes(data: Any) -> bytes:
    if isinstance(data, Path):
        return data.read_bytes()
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if isinstance(data, str):
        path = Path(data)
        if path.is_file():
            return path.read_bytes()
    records = _records(data)
    normalized = sorted(
        json.dumps(row, sort_keys=True, separators=(",", ":"), default=str) for row in records
    )
    return ("\n".join(normalized)).encode("utf-8")


def snapshot_id(data: Any, *, parent_id: str | None = None) -> str:
    """Return a stable SHA-256 ID for a feature snapshot and its parent."""

    digest = hashlib.sha256()
    digest.update(_canonical_bytes(data))
    if parent_id:
        digest.update(b"\0parent:")
        digest.update(str(parent_id).encode("utf-8"))
    return digest.hexdigest()


@dataclass(frozen=True)
class DataVersion:
    version: str
    row_count: int
    snapshot_id: str
    parent_id: str | None = None
    source: str = "local"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def version_data(
    data: Any,
    *,
    parent_id: str | None = None,
    source: str = "local",
) -> DataVersion:
    records = _records(data)
    digest = snapshot_id(records, parent_id=parent_id)
    return DataVersion(
        version=f"data-{digest[:16]}",
        row_count=len(records),
        snapshot_id=digest,
        parent_id=parent_id,
        source=source,
    )


class DataVersioner:
    """Small state-free facade suitable for injection into training jobs."""

    def create(self, data: Any, **kwargs: Any) -> DataVersion:
        return version_data(data, **kwargs)

    def compare(self, left: Any, right: Any) -> bool:
        return snapshot_id(left) == snapshot_id(right)


create_data_version = version_data
