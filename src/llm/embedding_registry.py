"""Versioned embedding registry with a dual-read, atomic alias swap.

The registry is intentionally transport-neutral.  A deployment can persist
the version records in ``ml_metadata`` and provide a reader that queries the
old and candidate vector namespaces.  The state transition itself remains
small and testable: validate both reads first, then change the active alias
under one lock so a query never observes a mixed version.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from typing import Any

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class EmbeddingVersion:
    """Immutable model/vector compatibility record."""

    version_id: str
    model_name: str
    dimensions: int
    image_digest: str


@dataclass(frozen=True)
class DualReadValidation:
    """Evidence that old and candidate namespaces were read compatibly."""

    previous_version: str
    candidate_version: str
    previous_count: int
    candidate_count: int
    dimensions: int
    validated_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "previous_version": self.previous_version,
            "candidate_version": self.candidate_version,
            "previous_count": self.previous_count,
            "candidate_count": self.candidate_count,
            "dimensions": self.dimensions,
            "validated_at": self.validated_at,
        }


class EmbeddingVersionRegistry:
    """In-memory reference implementation of embedding-version hot swap.

    ``dual_read`` returns one result per version.  Results may be sequences
    of vectors or mappings with a ``vector`` value; only shape is validated
    here because semantic similarity thresholds belong to the RAG adapter.
    When no reader is supplied, metadata-only validation is still performed,
    which keeps local contract tests deterministic without pretending that a
    live vector store was queried.
    """

    def __init__(self) -> None:
        self._versions: dict[str, EmbeddingVersion] = {}
        self._active: str | None = None
        self._lock = RLock()

    def register_version(self, model_name: str, dimensions: int, image_digest: str) -> str:
        """Register a model and return its deterministic version identifier."""

        if not model_name.strip():
            raise ValueError("model_name must not be empty")
        if dimensions < 1:
            raise ValueError("dimensions must be positive")
        if not _DIGEST_RE.fullmatch(image_digest):
            raise ValueError("image_digest must be a sha256:<64 hex> digest")
        version_id = hashlib.sha256(
            f"{model_name}|{dimensions}|{image_digest}".encode()
        ).hexdigest()[:16]
        record = EmbeddingVersion(version_id, model_name, dimensions, image_digest)
        with self._lock:
            self._versions[version_id] = record
            if self._active is None:
                self._active = version_id
        return version_id

    def resolve_active(self) -> str:
        """Return the active alias or fail closed when no version is ready."""

        with self._lock:
            if self._active is None:
                raise LookupError("no active embedding version")
            return self._active

    def compatibility_check(self, left: str, right: str) -> bool:
        """Return whether two registered versions share vector dimensions."""

        with self._lock:
            first, second = self._versions.get(left), self._versions.get(right)
            return bool(first and second and first.dimensions == second.dimensions)

    def validate_dual_read(
        self,
        candidate_version: str,
        dual_read: Callable[[str], Sequence[Any] | Mapping[str, Any]] | None = None,
    ) -> DualReadValidation:
        """Read both namespaces and validate the candidate before an alias swap."""

        with self._lock:
            previous_version = self.resolve_active()
            previous = self._versions[previous_version]
            candidate = self._versions.get(candidate_version)
            if candidate is None:
                raise KeyError(f"unknown embedding version: {candidate_version}")
            if previous.dimensions != candidate.dimensions:
                raise ValueError("embedding dimensions are incompatible")

        if dual_read is None:
            previous_result: Sequence[Any] | Mapping[str, Any] = ()
            candidate_result: Sequence[Any] | Mapping[str, Any] = ()
        else:
            previous_result = dual_read(previous_version)
            candidate_result = dual_read(candidate_version)
            self._validate_result_shape(previous, previous_result)
            self._validate_result_shape(candidate, candidate_result)

        return DualReadValidation(
            previous_version=previous_version,
            candidate_version=candidate_version,
            previous_count=self._result_count(previous_result),
            candidate_count=self._result_count(candidate_result),
            dimensions=previous.dimensions,
            validated_at=datetime.now(UTC).isoformat(),
        )

    def hot_swap(
        self,
        candidate_version: str,
        *,
        dual_read: Callable[[str], Sequence[Any] | Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Dual-read validate, then atomically move the active alias."""

        validation = self.validate_dual_read(candidate_version, dual_read)
        with self._lock:
            # Re-check the alias after the potentially slow reads.  A second
            # concurrent swap must not silently overwrite a newer decision.
            if self._active != validation.previous_version:
                raise RuntimeError("active embedding version changed during dual-read validation")
            self._active = candidate_version
        return {
            "status": "swapped",
            "active_version": candidate_version,
            "previous_version": validation.previous_version,
            "dual_read": validation.as_dict(),
        }

    def validate_query(self, version: str, vector: Sequence[float]) -> None:
        """Reject a query vector whose dimension does not match its namespace."""

        with self._lock:
            record = self._versions.get(version)
            if record is None:
                raise KeyError(f"unknown embedding version: {version}")
            if len(vector) != record.dimensions:
                raise ValueError(
                    f"vector dimensions {len(vector)} do not match {record.dimensions}"
                )

    @staticmethod
    def _result_count(result: Sequence[Any] | Mapping[str, Any]) -> int:
        if isinstance(result, Mapping):
            return len(result.get("matches", ()))
        return len(result)

    @staticmethod
    def _validate_result_shape(record: EmbeddingVersion, result: Any) -> None:
        values = result.get("matches", ()) if isinstance(result, Mapping) else result
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            raise TypeError("dual-read result must expose a sequence of matches")
        for item in values:
            vector = item.get("vector") if isinstance(item, Mapping) else item
            if vector is not None and len(vector) != record.dimensions:
                raise ValueError(f"dual-read vector dimensions do not match {record.dimensions}")


# Short alias used in examples and notebooks.
EmbeddingRegistry = EmbeddingVersionRegistry
