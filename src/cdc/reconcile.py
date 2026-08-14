"""Windowed reconciliation between generator and CDC Bronze paths."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


@dataclass(frozen=True)
class ReconciliationReport:
    """Structured comparison result suitable for JSON/evidence output."""

    window_start: str | None
    window_end: str | None
    generator_count: int
    cdc_count: int
    generator_keys: frozenset[tuple[Any, ...]]
    cdc_keys: frozenset[tuple[Any, ...]]
    generator_only: frozenset[tuple[Any, ...]]
    cdc_only: frozenset[tuple[Any, ...]]
    duplicate_generator_keys: frozenset[tuple[Any, ...]] = frozenset()
    duplicate_cdc_keys: frozenset[tuple[Any, ...]] = frozenset()

    @property
    def row_count_delta(self) -> int:
        return self.generator_count - self.cdc_count

    @property
    def counts_match(self) -> bool:
        return self.generator_count == self.cdc_count

    @property
    def keys_match(self) -> bool:
        return self.generator_keys == self.cdc_keys

    @property
    def matched(self) -> bool:
        return self.counts_match and self.keys_match

    @property
    def status(self) -> str:
        return "matched" if self.matched else "mismatch"

    @property
    def missing_keys(self) -> frozenset[tuple[Any, ...]]:
        return self.generator_only

    def as_dict(self) -> dict[str, Any]:
        def encode(values: frozenset[tuple[Any, ...]]) -> list[list[Any]]:
            return sorted((list(key) for key in values), key=str)

        return {
            "window_start": self.window_start,
            "window_end": self.window_end,
            "generator_count": self.generator_count,
            "cdc_count": self.cdc_count,
            "row_count_delta": self.row_count_delta,
            "generator_keys": encode(self.generator_keys),
            "cdc_keys": encode(self.cdc_keys),
            "generator_only": encode(self.generator_only),
            "cdc_only": encode(self.cdc_only),
            "duplicate_generator_keys": encode(self.duplicate_generator_keys),
            "duplicate_cdc_keys": encode(self.duplicate_cdc_keys),
            "counts_match": self.counts_match,
            "keys_match": self.keys_match,
            "matched": self.matched,
            "status": self.status,
        }

    def __getitem__(self, key: str) -> Any:
        return self.as_dict()[key]


def _filter_window(
    rows: Iterable[Mapping[str, Any]],
    *,
    timestamp_column: str,
    start: datetime | None,
    end: datetime | None,
) -> list[Mapping[str, Any]]:
    selected: list[Mapping[str, Any]] = []
    for row in rows:
        if start is None and end is None:
            selected.append(row)
            continue
        timestamp = row.get(timestamp_column)
        if timestamp is None:
            continue
        parsed = _parse_time(timestamp)
        if start is not None and parsed < start:
            continue
        if end is not None and parsed > end:
            continue
        selected.append(row)
    return selected


def reconcile_paths(
    generator_rows: Iterable[Mapping[str, Any]],
    cdc_rows: Iterable[Mapping[str, Any]],
    *,
    start_ts: Any | None = None,
    end_ts: Any | None = None,
    key_columns: str | Iterable[str] = "business_key",
    timestamp_column: str = "event_timestamp",
) -> ReconciliationReport:
    """Compare row counts and business-key sets over an inclusive time window."""
    start = _parse_time(start_ts) if start_ts is not None else None
    end = _parse_time(end_ts) if end_ts is not None else None
    if start is not None and end is not None and start > end:
        raise ValueError("start_ts must not be after end_ts")
    keys = (key_columns,) if isinstance(key_columns, str) else tuple(key_columns)
    if not keys or any(not key for key in keys):
        raise ValueError("key_columns must contain at least one field")

    generator = _filter_window(
        generator_rows, timestamp_column=timestamp_column, start=start, end=end
    )
    cdc = _filter_window(cdc_rows, timestamp_column=timestamp_column, start=start, end=end)

    def extract(
        rows: list[Mapping[str, Any]],
    ) -> tuple[frozenset[tuple[Any, ...]], frozenset[tuple[Any, ...]]]:
        seen: set[tuple[Any, ...]] = set()
        duplicate: set[tuple[Any, ...]] = set()
        for row in rows:
            key = tuple(row.get(column) for column in keys)
            if key in seen:
                duplicate.add(key)
            seen.add(key)
        return frozenset(seen), frozenset(duplicate)

    generator_keys, generator_duplicates = extract(generator)
    cdc_keys, cdc_duplicates = extract(cdc)
    return ReconciliationReport(
        window_start=start.isoformat() if start else None,
        window_end=end.isoformat() if end else None,
        generator_count=len(generator),
        cdc_count=len(cdc),
        generator_keys=generator_keys,
        cdc_keys=cdc_keys,
        generator_only=generator_keys - cdc_keys,
        cdc_only=cdc_keys - generator_keys,
        duplicate_generator_keys=generator_duplicates,
        duplicate_cdc_keys=cdc_duplicates,
    )


reconcile = reconcile_paths


def reconciliation_report_json(report: ReconciliationReport) -> dict[str, Any]:
    """Return a JSON-serialisable report payload."""
    return report.as_dict()


def run_reconciliation_task(**context: Any) -> dict[str, Any]:
    """Airflow callable boundary; real deployments inject rows via XCom/files.

    Without injected rows this returns a non-claiming empty report rather than
    fabricating a successful live comparison.
    """
    if "generator_rows" not in context or "cdc_rows" not in context:
        raise RuntimeError(
            "reconciliation requires injected generator_rows and cdc_rows; "
            "refusing to report an empty window as matched"
        )
    generator_rows = context["generator_rows"]
    cdc_rows = context["cdc_rows"]
    if not generator_rows and not cdc_rows:
        raise RuntimeError("reconciliation input rows are empty; refusing a false-green result")
    return reconcile_paths(generator_rows, cdc_rows).as_dict()


__all__ = [
    "ReconciliationReport",
    "reconcile",
    "reconcile_paths",
    "reconciliation_report_json",
    "run_reconciliation_task",
]
