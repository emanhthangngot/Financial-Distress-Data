# ADR-005: Feast Stores — Structured and RAG

- Status: **Amended by [ADR-010](./adr-010-llm-only-scope-and-platform-simplification.md) (2026-08-07)**
- Date: 2026-08-02
- Deciders: Phase 2 architecture review, data engineer
- Related: `docs/phase2/architecture.md`, `plan.md` phase-04

> **Amended:** store backends move in-cluster — Redis for the structured online
> store (not ElastiCache Valkey), PGVector in-cluster (not RDS), local object
> storage for offline data and version manifests (not S3). Everything else
> stands. The offline store is still defined with correct `event_timestamp`
> semantics even though only the online store is read during the LLM-only week;
> that is load-bearing for the deferred ML retrofit.

## Context

Both the ML track (structured features) and the LLM track (RAG vectors) need a
feature store with offline/online semantics and point-in-time correctness.

## Decision

- **Structured Feast project**: S3 offline store, ElastiCache Valkey online
  store, entity `ticker`, timestamp-correct feature views with documented TTL
  per table.
- **RAG Feast project**: S3 offline data/version manifests, RDS PGVector
  online vectors and metadata. Milvus is added only after >500k vectors or a
  measured p95 that violates the accepted SLO.
- Every training/RAG run records snapshot ID, parent ID, changed
  partitions/hashes and Feast registry revision.
- TTL derives from business freshness: market/stream features short, quarterly
  financial features long, document embeddings tied to document version.

## Consequences

- Point-in-time correctness is enforceable; incremental data versioning is
  possible.
- Two Feast projects keep structured and vector concerns separate.

## Alternatives Considered

- Single Feast project for both (rejected: vector metadata needs different
  online storage and TTL semantics).
