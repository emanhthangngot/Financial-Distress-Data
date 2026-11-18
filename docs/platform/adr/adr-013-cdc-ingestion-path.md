# ADR-013: CDC ingestion path — Debezium, Kafka, Flink

## Status

**Amended 2026-09-05** (unified rebuild,
`plans/260831-1644-rebuild-target-mlops-architecture/phase-05-cdc-streaming.md`).
Originally accepted 2026-08-13 as Flink CDC direct.

> **Amended:** the CDC path is **Debezium → Kafka → Flink**, not Flink CDC
> connecting to Postgres directly. Debezium's Postgres connector captures the
> logical replication stream and publishes change events to Kafka; Flink
> consumes from Kafka, not from the replication slot. This matches the
> target architecture image (`fdd-architecture-full-4k.png` component #36-38:
> Debezium → Kafka → Flink, all in `ns: dataflow`) and phase-05's `owns:`
> scope (`src/cdc/`, `src/streaming/`). The reconciliation contract below
> (`src/cdc/reconcile.py` comparing the CDC path against the generator/Kafka
> path over a bounded window) is unchanged — only the transport between
> Postgres and Flink changes, not the correctness check.

## Decision

Product writes are captured from a dedicated Postgres instance configured with
`wal_level=logical`, a least-privilege replication user, a publication and a
bounded replication slot. Flink CDC reads that logical replication stream and
writes the the platform Iceberg Bronze table through its REST catalog sink. The
initial snapshot and incremental WAL phases are explicit in the source
connector contract.

The path runs in parallel with the existing the platform `generator -> Kafka`
pipeline. `src/cdc/reconcile.py` filters both paths to the same inclusive time
window, compares row counts and business-key sets, and emits a structured
report. A mismatch is reported as a mismatch; it is never presented as live
success without matching evidence.

## Alternatives

- **Debezium plus Kafka Connect:** rejected for this single downstream consumer;
  it adds a second runtime and an unnecessary Kafka hop. Flink CDC embeds the
  Debezium engine and keeps delivery and recovery in the existing Flink plane.
- **Reconfigure the the platform Postgres:** rejected because `src/` the platform
  contracts and its local stack are protected. The dedicated source also
  mirrors a production product-plane ownership boundary.

## Consequences and safety

- CDC can land inserts, updates and deletes while preserving operation metadata
  for the Bronze sink.
- A stalled replication slot can consume disk. Slot lag and retention must be
  monitored and the slot dropped during decommissioning.
- The fast test loop uses pure configuration, normalization and reconciliation
  contracts; a live Flink/Postgres run is separate evidence and is not claimed
  by local tests.
