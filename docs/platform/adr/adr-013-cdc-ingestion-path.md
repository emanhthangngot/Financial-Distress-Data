# ADR-013: Flink CDC as a parallel ingestion path

## Status

Accepted — 2026-08-13 (the platform production-hardening overlay).

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
