# ADR-012: Iceberg REST catalog with Lakekeeper

## Status

Accepted — 2026-08-13 (Phase 2 production-hardening overlay).

## Decision

Phase 2 feature, label and drift-reference tables use Apache Iceberg semantics
and are registered through an Iceberg REST catalog. Lakekeeper is the selected
catalog deployment because its Rust implementation and Kubernetes-native REST
surface fit the single-node resource budget. The source repository exposes a
dependency-light local contract in `src/lakehouse/`; the live catalog endpoint
is supplied through `ICEBERG_CATALOG_URI` and a secret managed by the platform
repository.

Iceberg snapshots are the data-version boundary for training reads. A training
manifest records the exact snapshot ID, and a replay resolves that ID rather
than silently reading the current table. Additive columns use Iceberg schema
evolution; existing snapshots and readers remain valid without rewriting old
files.

## Alternatives

| Catalog | Decision |
| --- | --- |
| Apache Polaris | Rejected for this scope: broader multi-engine governance and a larger operational footprint. |
| Nessie | Rejected for now: Git-like data branches are not required by the Phase 2 workflow. |
| Lakekeeper | Selected: lean, REST-compatible and authorization-friendly. |

The REST protocol is the compatibility boundary. Replacing Lakekeeper with
another compliant catalog is a configuration change, not a table-format
migration. Phase 1 Parquet evidence remains frozen and is not migrated into
Phase 2 Iceberg tables.

## Consequences

- Snapshot IDs make incremental training-data pulls auditable and replayable.
- ACID commits, isolation and schema evolution are delegated to Iceberg in the
  live deployment; local tests exercise the same table/snapshot contracts
  without requiring a cluster.
- The deployment still needs compatible versions of Lakekeeper and the chosen
  Iceberg engine; compatibility is checked before a live promotion.
