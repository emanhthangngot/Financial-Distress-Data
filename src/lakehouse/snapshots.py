"""Snapshot and incremental-read helpers for the local Iceberg contract."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .catalog import CatalogError, LocalIcebergTable, Snapshot


@dataclass(frozen=True)
class SnapshotDiff:
    added: tuple[dict[str, Any], ...]
    removed: tuple[dict[str, Any], ...]
    updated: tuple[dict[str, Any], ...]
    from_snapshot_id: str | None
    to_snapshot_id: str | None

    @property
    def added_count(self) -> int:
        return len(self.added)

    @property
    def removed_count(self) -> int:
        return len(self.removed)

    @property
    def updated_count(self) -> int:
        return len(self.updated)

    @property
    def row_delta(self) -> int:
        return self.added_count - self.removed_count

    def as_dict(self) -> dict[str, Any]:
        return {
            "from_snapshot_id": self.from_snapshot_id,
            "to_snapshot_id": self.to_snapshot_id,
            "added": list(self.added),
            "removed": list(self.removed),
            "updated": list(self.updated),
            "added_count": self.added_count,
            "removed_count": self.removed_count,
            "updated_count": self.updated_count,
            "row_delta": self.row_delta,
        }

    def __getitem__(self, key: str) -> Any:
        return self.as_dict()[key]


def current_snapshot_id(table: LocalIcebergTable) -> str | None:
    return table.current_snapshot_id


resolve_current_snapshot = current_snapshot_id


def read_as_of(table: LocalIcebergTable, snapshot_id: str | None) -> list[dict[str, Any]]:
    """Read a copy of rows from a recorded snapshot ID."""
    return table.read(snapshot_id)


read_snapshot = read_as_of


def snapshot_metadata(table: LocalIcebergTable, snapshot_id: str | None = None) -> Snapshot:
    """Return immutable metadata for a snapshot, raising on an unknown ID."""
    snapshots = table.snapshots
    if not snapshots:
        raise CatalogError(f"table has no snapshots: {table.identifier}")
    wanted = snapshot_id or snapshots[-1].snapshot_id
    for snapshot in snapshots:
        if snapshot.snapshot_id == wanted:
            return snapshot
    raise CatalogError(f"unknown snapshot {wanted!r} for {table.identifier}")


def _row_key(row: dict[str, Any], key_columns: tuple[str, ...]) -> tuple[Any, ...]:
    return tuple(row.get(column) for column in key_columns)


def diff_snapshots(
    table: LocalIcebergTable,
    from_snapshot_id: str | None,
    to_snapshot_id: str | None = None,
    *,
    key_columns: Iterable[str] = ("ticker", "event_timestamp"),
) -> SnapshotDiff:
    """Compare two snapshots by business key and classify adds/removes/updates."""
    from_rows = read_as_of(table, from_snapshot_id) if from_snapshot_id else []
    to_id = to_snapshot_id or current_snapshot_id(table)
    to_rows = read_as_of(table, to_id) if to_id else []
    keys = tuple(key_columns)
    if not keys:
        raise ValueError("key_columns must contain at least one field")

    before = {_row_key(row, keys): row for row in from_rows}
    after = {_row_key(row, keys): row for row in to_rows}
    added = tuple(after[key] for key in sorted(set(after) - set(before), key=str))
    removed = tuple(before[key] for key in sorted(set(before) - set(after), key=str))
    updated = tuple(
        after[key] for key in sorted(set(before) & set(after), key=str) if before[key] != after[key]
    )
    return SnapshotDiff(added, removed, updated, from_snapshot_id, to_id)


snapshot_diff = diff_snapshots


__all__ = [
    "SnapshotDiff",
    "current_snapshot_id",
    "diff_snapshots",
    "read_as_of",
    "read_snapshot",
    "resolve_current_snapshot",
    "snapshot_diff",
    "snapshot_metadata",
]
