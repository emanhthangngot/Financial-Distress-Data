"""Dependency-light Iceberg/Lakekeeper catalog contracts.

The production deployment uses an Iceberg REST catalog (Lakekeeper).  The
source repository deliberately keeps the unit-test contract local and
network-free: :func:`load_catalog` validates the same connection settings and
returns an in-memory catalog implementing the table/snapshot operations used by
the Phase 2 jobs.  A real REST client can be substituted at the boundary
without changing callers.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import threading
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse


class CatalogError(ValueError):
    """Raised when catalog or table contracts are invalid."""


class ConcurrentCommitError(CatalogError):
    """Raised when a caller commits against a stale parent snapshot."""


@dataclass(frozen=True)
class CatalogConfig:
    """Connection contract shared by local tests and the REST deployment."""

    name: str = "lakekeeper"
    uri: str = "http://lakekeeper:8181/catalog"
    warehouse: str = "s3://financial-distress-lake/phase2"
    mode: str = "memory"
    token: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        parsed = urlparse(self.uri)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise CatalogError("catalog uri must be an absolute http(s) URL")
        if self.mode not in {"memory", "rest"}:
            raise CatalogError("catalog mode must be 'memory' or 'rest'")
        if not self.warehouse.strip():
            raise CatalogError("warehouse must not be empty")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> CatalogConfig:
        env = os.environ if environ is None else environ
        return cls(
            name=env.get("ICEBERG_CATALOG_NAME", "lakekeeper"),
            uri=env.get("ICEBERG_CATALOG_URI", "http://lakekeeper:8181/catalog"),
            warehouse=env.get("ICEBERG_WAREHOUSE", "s3://financial-distress-lake/phase2"),
            mode=env.get("ICEBERG_CATALOG_MODE", "memory"),
            token=env.get("ICEBERG_CATALOG_TOKEN"),
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _snapshot_id(rows: list[dict[str, Any]], schema: tuple[str, ...], sequence: int) -> str:
    payload = json.dumps(
        {"rows": rows, "schema": schema, "sequence": sequence},
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:20]


@dataclass(frozen=True)
class Snapshot:
    """Immutable table state at one commit."""

    snapshot_id: str
    sequence_number: int
    committed_at: str
    rows: tuple[dict[str, Any], ...]
    schema: tuple[str, ...]
    parent_snapshot_id: str | None = None


class LocalIcebergTable:
    """Small local table model with atomic commits and time-travel reads."""

    def __init__(
        self,
        identifier: str,
        schema: Mapping[str, str] | Iterable[str],
        partition_spec: Iterable[str] = (),
    ) -> None:
        self.identifier = identifier
        self._schema: dict[str, str] = (
            dict(schema)
            if isinstance(schema, Mapping)
            else {str(name): "string" for name in schema}
        )
        if not self._schema:
            raise CatalogError("table schema must contain at least one field")
        self.partition_spec = tuple(str(part) for part in partition_spec)
        unknown_partitions = set(self.partition_spec) - set(self._schema)
        if unknown_partitions:
            raise CatalogError(
                f"partition fields not found in schema: {sorted(unknown_partitions)}"
            )
        self._snapshots: list[Snapshot] = []
        self._lock = threading.RLock()

    @property
    def schema(self) -> dict[str, str]:
        with self._lock:
            return dict(self._schema)

    @property
    def current_snapshot_id(self) -> str | None:
        with self._lock:
            return self._snapshots[-1].snapshot_id if self._snapshots else None

    @property
    def snapshots(self) -> tuple[Snapshot, ...]:
        with self._lock:
            return tuple(self._snapshots)

    def _commit(
        self,
        rows: list[dict[str, Any]],
        *,
        expected_snapshot_id: str | None = None,
    ) -> Snapshot:
        with self._lock:
            parent = self.current_snapshot_id
            if expected_snapshot_id is not None and expected_snapshot_id != parent:
                raise ConcurrentCommitError(
                    f"stale snapshot for {self.identifier}: expected {expected_snapshot_id!r}, "
                    f"current is {parent!r}"
                )
            normalized = [self._normalize_row(row) for row in rows]
            sequence = len(self._snapshots) + 1
            snapshot = Snapshot(
                snapshot_id=_snapshot_id(normalized, tuple(self._schema), sequence),
                sequence_number=sequence,
                committed_at=_utc_now(),
                rows=tuple(copy.deepcopy(normalized)),
                schema=tuple(self._schema),
                parent_snapshot_id=parent,
            )
            self._snapshots.append(snapshot)
            return snapshot

    def _normalize_row(self, row: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(row, Mapping):
            raise CatalogError("table rows must be mappings")
        unknown = set(row) - set(self._schema)
        if unknown:
            raise CatalogError(f"row contains fields outside schema: {sorted(unknown)}")
        # Missing fields are represented as null, matching Iceberg's additive
        # schema evolution semantics and keeping old readers valid.
        return {name: copy.deepcopy(row.get(name)) for name in self._schema}

    def append(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        expected_snapshot_id: str | None = None,
    ) -> Snapshot:
        """Atomically append rows and create one new snapshot."""
        with self._lock:
            previous = list(self._snapshots[-1].rows) if self._snapshots else []
            previous.extend(dict(row) for row in rows)
            return self._commit(previous, expected_snapshot_id=expected_snapshot_id)

    def replace(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        expected_snapshot_id: str | None = None,
    ) -> Snapshot:
        """Atomically replace the current table contents."""
        return self._commit([dict(row) for row in rows], expected_snapshot_id=expected_snapshot_id)

    def evolve_schema(self, name: str, field_type: str = "string") -> None:
        """Add one nullable column without rewriting existing snapshots."""
        name = str(name).strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise CatalogError(f"invalid field name: {name!r}")
        with self._lock:
            if name in self._schema:
                raise CatalogError(f"field already exists: {name}")
            self._schema[name] = str(field_type)

    add_column = evolve_schema

    def read(self, snapshot_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            snapshot = self._resolve_snapshot(snapshot_id)
            return copy.deepcopy(list(snapshot.rows)) if snapshot else []

    def _resolve_snapshot(self, snapshot_id: str | None) -> Snapshot | None:
        if not self._snapshots:
            return None
        if snapshot_id is None:
            return self._snapshots[-1]
        for snapshot in self._snapshots:
            if snapshot.snapshot_id == snapshot_id:
                return snapshot
        raise CatalogError(f"unknown snapshot {snapshot_id!r} for {self.identifier}")


class LocalIcebergCatalog:
    """In-memory implementation of the subset used by Phase 2 contracts."""

    def __init__(self, config: CatalogConfig | None = None) -> None:
        self.config = config or CatalogConfig()
        self._tables: dict[str, LocalIcebergTable] = {}
        self._lock = threading.RLock()

    def create_table(
        self,
        identifier: str,
        schema: Mapping[str, str] | Iterable[str],
        partition_spec: Iterable[str] = (),
    ) -> LocalIcebergTable:
        normalized = str(identifier).strip()
        if "." not in normalized:
            raise CatalogError("table identifier must include a namespace, e.g. phase2.features")
        with self._lock:
            if normalized in self._tables:
                raise CatalogError(f"table already exists: {normalized}")
            table = LocalIcebergTable(normalized, schema, partition_spec)
            self._tables[normalized] = table
            return table

    register_table = create_table

    def load_table(self, identifier: str) -> LocalIcebergTable:
        try:
            return self._tables[str(identifier)]
        except KeyError as exc:
            raise CatalogError(f"unknown table: {identifier}") from exc

    def list_tables(self, namespace: str = "phase2") -> list[str]:
        prefix = f"{namespace}."
        return sorted(name for name in self._tables if name.startswith(prefix))


def load_catalog(
    config: CatalogConfig | None = None,
    *,
    register_defaults: bool = False,
) -> LocalIcebergCatalog:
    """Load a validated catalog contract without making a network call.

    ``mode='rest'`` records that the eventual client is Lakekeeper REST, while
    the local implementation remains available for deterministic tests and
    offline development.
    """
    catalog = LocalIcebergCatalog(config or CatalogConfig.from_env())
    if register_defaults:
        from .tables import register_phase2_tables

        register_phase2_tables(catalog)
    return catalog


__all__ = [
    "CatalogConfig",
    "CatalogError",
    "ConcurrentCommitError",
    "LocalIcebergCatalog",
    "LocalIcebergTable",
    "Snapshot",
    "load_catalog",
]
