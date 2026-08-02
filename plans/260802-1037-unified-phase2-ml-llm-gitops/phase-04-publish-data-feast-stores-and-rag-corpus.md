---
title: "Phase 4: Publish data, Feast stores and RAG corpus"
status: todo
estimate: "7-10 days"
---

# Phase 4: Publish data, Feast stores and RAG corpus

## Overview

Extend the verified Phase 1 outputs without changing them. Publish immutable snapshots/deltas to cloud stores, materialize structured and RAG features through Feast, add realistic drift/labels, and prove lineage/governance.

## Data Contracts

- Structured Feast project: S3 offline store; ElastiCache Valkey online store; entity `ticker`; timestamp-correct feature views with documented TTL per table.
- RAG Feast project: S3 offline data/version manifests; RDS PGVector online vectors and metadata. Add Milvus only after >500k vectors or measured p95 violates the accepted SLO.
- RAG sources: Vnstock news plus trusted company/filing PDFs; each chunk stores source URI, company, report date, document/content hash, parser version, embedding model/version, created time and access class.
- Label table: `ticker`, `event_timestamp`, `label`, `label_version`, `created_ts`, `training_eligible`; proxy labels remain explicitly non-ground-truth.
- Drift scenarios: financial deterioration and market stress from config, with deterministic seeds and before/after reports.

## Implementation Steps

1. Seed failing schema, PIT leakage, incremental-version, idempotency, TTL, governance and drift tests.
2. Implement cloud publication as additive adapters under `src/ml/` and `src/drift/`; never alter Phase 1 Gold writers or MinIO semantics.
3. Version data incrementally with content-addressed base/delta manifests. Every training/RAG run records snapshot ID, parent ID, changed partitions/hashes and Feast registry revision.
4. Build Airflow-compatible Phase 2 DAGs that can run locally and launch Kubernetes jobs when the evidence plane is ready:
   - materialize latest structured features offline -> online;
   - push stream features to offline;
   - push stream features to online;
   - create label/drift tables;
   - RAG fetch -> parse -> chunk -> embed -> Feast/PGVector.
5. Retain Phase 1 DataHub evidence and emit Phase 2 lineage for every input, step, feature view, vector set, model/agent consumer and output.
6. Define TTL from business freshness: market/stream features short, quarterly financial features long, document embeddings tied to document version; capture reasoning in docs and registry definitions.
7. Add retries, checkpoints, dead-letter/quarantine, source rate limits, content deduplication and PII/licensing checks.
8. Produce a notebook that retrieves data through Feast, joins labels by PIT rules and demonstrates incremental data versions.

## Validation

- `pytest` schema/PIT/idempotency/property tests with Hypothesis.
- Feast plan/apply/materialize smoke tests against disposable stores.
- Re-run each DAG/job twice and prove stable counts/hashes and no duplicate online keys/chunks.
- Compare generated drift against configured direction and threshold.
- DataHub lineage and evidence manifest audit.

## Success Criteria

- [ ] Training consumer -> requests features for a historical label timestamp -> receives only feature values available at or before that timestamp.
- [ ] Materialization job -> reruns the same interval -> produces no duplicate offline rows and the same online values.
- [ ] Stream publisher -> receives new records -> pushes the required job output to both offline and online stores with captured success evidence.
- [ ] RAG pipeline -> reprocesses an unchanged document -> reuses its chunk/content hashes instead of creating duplicate vectors.
- [ ] Reviewer -> inspects Airflow and DataHub -> sees ordered successful steps, two feature push jobs, RAG lineage, TTL rationale, data versions and governed sources.
- [ ] Phase 1 maintainer -> runs Stage 1 quality gates -> receives the same outputs and contracts as before Phase 2 adapters were added.

## Risks and Rollback

- Risk: local MinIO paths and cloud S3 paths diverge. Mitigation: explicit adapter contract and golden manifest tests.
- Rollback: disable Phase 2 DAGs/jobs and restore the previous Feast registry revision; Phase 1 datasets remain authoritative and intact.
