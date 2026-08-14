"""Phase 2 Iceberg table definitions and schema-evolution helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .catalog import CatalogError, LocalIcebergCatalog, LocalIcebergTable


@dataclass(frozen=True)
class TableDefinition:
    identifier: str
    schema: Mapping[str, str]
    partition_spec: tuple[str, ...]


PHASE2_TABLE_DEFINITIONS: tuple[TableDefinition, ...] = (
    TableDefinition(
        "phase2.features",
        {
            "ticker": "string",
            "event_timestamp": "timestamp",
            "created_ts": "timestamp",
            "feature_value": "double",
        },
        ("ticker",),
    ),
    TableDefinition(
        "phase2.labels",
        {
            "ticker": "string",
            "event_timestamp": "timestamp",
            "created_ts": "timestamp",
            "distress_label": "boolean",
        },
        ("ticker",),
    ),
    TableDefinition(
        "phase2.drift_reference",
        {
            "ticker": "string",
            "event_timestamp": "timestamp",
            "created_ts": "timestamp",
            "feature_name": "string",
            "reference_value": "double",
        },
        ("feature_name",),
    ),
)


def register_phase2_tables(catalog: LocalIcebergCatalog) -> dict[str, LocalIcebergTable]:
    """Register all Phase 2 tables and return them by identifier.

    Existing registrations are accepted when their schema and partition spec
    still match; this makes repeated setup calls idempotent without hiding a
    contract drift.
    """
    tables: dict[str, LocalIcebergTable] = {}
    for definition in PHASE2_TABLE_DEFINITIONS:
        if definition.identifier in catalog.list_tables("phase2"):
            table = catalog.load_table(definition.identifier)
            if (
                table.schema != dict(definition.schema)
                or table.partition_spec != definition.partition_spec
            ):
                raise CatalogError(
                    f"registered table does not match definition: {definition.identifier}"
                )
        else:
            table = catalog.create_table(
                definition.identifier,
                definition.schema,
                definition.partition_spec,
            )
        tables[definition.identifier] = table
    return tables


def phase2_table_definitions() -> tuple[TableDefinition, ...]:
    """Return immutable definitions for callers that need to inspect them."""
    return PHASE2_TABLE_DEFINITIONS


__all__ = [
    "PHASE2_TABLE_DEFINITIONS",
    "TableDefinition",
    "phase2_table_definitions",
    "register_phase2_tables",
]
