"""
``gold.distress_holdout`` freeze — knowledge-time-pinned, byte-identical time travel.

phase-04-data-plane.md: "freeze gold.distress_holdout @ holdout-v1 pinned to a knowledge-time
cutoff (the _v1 suffix is dropped from the table name per P2 §Naming Convention — version lives
in the Iceberg tag only)." AC: "holdout-v1 resolves to byte-identical time-travel reads and is
pinned to a knowledge-time cutoff."

Two properties this module guarantees together:

1. **Knowledge-time correctness** — every row in the frozen holdout has ``known_from_ts <=
   knowledge_cutoff``. A row restated after the cutoff never enters the holdout under its
   restated values, even if that restatement has since landed in the live table (ADR-017: this
   is exactly the leakage class the bi-temporal model exists to prevent, applied to the holdout
   itself rather than only to training features).
2. **Byte-identical time travel** — the frozen set is committed as one snapshot and tagged
   ``holdout-v1``. ``LocalIcebergTable._snapshot_id`` is a deterministic hash of the committed
   rows, so re-reading the tag returns the exact same rows every time, and re-freezing identical
   input produces the exact same snapshot ID (verifiable without inspecting row contents).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.lakehouse.catalog import CatalogError, LocalIcebergCatalog, LocalIcebergTable

HOLDOUT_TABLE = "gold.distress_holdout"
HOLDOUT_TAG = "holdout-v1"

# gold.fact_distress_label's grain (ADR-017): report_period is valid time, known_from_ts is
# knowledge time. Holdout membership is a function of knowledge time only.
_REQUIRED_FIELDS = ("ticker", "report_period", "known_from_ts")


class HoldoutFreezeError(CatalogError):
    """Raised when the holdout cannot be frozen — e.g. no rows survive the knowledge-time cutoff."""


@dataclass(frozen=True)
class HoldoutFreezeResult:
    snapshot_id: str
    tag: str
    row_count: int
    knowledge_cutoff: str


def _parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise HoldoutFreezeError(f"unparseable known_from_ts: {value!r}") from exc


def filter_to_knowledge_cutoff(
    rows: list[dict[str, Any]], knowledge_cutoff: datetime
) -> list[dict[str, Any]]:
    """Keep only rows knowable as of ``knowledge_cutoff`` (known_from_ts <= cutoff).

    Raises on a missing/unparseable known_from_ts rather than silently dropping or including
    the row — an ambiguous knowledge time is exactly the failure mode this function exists to
    make loud (D-5/D-6's "raise, never default" rule, applied here).
    """
    kept: list[dict[str, Any]] = []
    for row in rows:
        for field in _REQUIRED_FIELDS:
            if row.get(field) in (None, ""):
                raise HoldoutFreezeError(f"row missing required field {field!r}: {row}")
        known_from = _parse_ts(row["known_from_ts"])
        if known_from <= knowledge_cutoff:
            kept.append(dict(row))
    return kept


def freeze_distress_holdout(
    catalog: LocalIcebergCatalog,
    candidate_rows: list[dict[str, Any]],
    *,
    knowledge_cutoff: datetime,
    schema: dict[str, str] | None = None,
) -> HoldoutFreezeResult:
    """Filter ``candidate_rows`` to the knowledge-time cutoff and freeze them as holdout-v1.

    Idempotent: freezing the same ``candidate_rows``/``knowledge_cutoff`` twice produces the
    same snapshot_id (the content hash is deterministic) and re-tags it to the same value —
    it never accumulates duplicate snapshots for identical input.
    """
    filtered = filter_to_knowledge_cutoff(candidate_rows, knowledge_cutoff)
    if not filtered:
        raise HoldoutFreezeError(
            f"no rows survive knowledge_cutoff={knowledge_cutoff.isoformat()} — "
            "refusing to freeze an empty holdout"
        )

    inferred_schema = schema or {key: "string" for key in filtered[0]}
    try:
        table: LocalIcebergTable = catalog.load_table(HOLDOUT_TABLE)
    except CatalogError:
        table = catalog.create_table(HOLDOUT_TABLE, inferred_schema, partition_spec=())

    snapshot = table.replace(filtered)
    resolved_snapshot_id = table.tag(HOLDOUT_TAG, snapshot.snapshot_id)
    return HoldoutFreezeResult(
        snapshot_id=resolved_snapshot_id,
        tag=HOLDOUT_TAG,
        row_count=len(filtered),
        knowledge_cutoff=knowledge_cutoff.isoformat(),
    )


def read_distress_holdout(catalog: LocalIcebergCatalog) -> list[dict[str, Any]]:
    """Byte-identical time-travel read of the frozen holdout-v1 tag."""
    table = catalog.load_table(HOLDOUT_TABLE)
    return table.read_tag(HOLDOUT_TAG)


__all__ = [
    "HOLDOUT_TABLE",
    "HOLDOUT_TAG",
    "HoldoutFreezeError",
    "HoldoutFreezeResult",
    "filter_to_knowledge_cutoff",
    "freeze_distress_holdout",
    "read_distress_holdout",
]
