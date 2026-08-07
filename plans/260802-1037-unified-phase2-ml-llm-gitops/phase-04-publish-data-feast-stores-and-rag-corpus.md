---
title: "Phase 4: Publish data, Feast stores and RAG corpus"
status: todo
estimate: "1 day (day 2)"
---

# Phase 4: Publish data, Feast stores and RAG corpus

## Overview

Extend the verified Phase 1 outputs without changing them. Build the RAG corpus
and PGVector store, stand up Feast with an online store the MCP tools read and
an offline store defined correctly for the deferred ML retrofit, ship the two
stream-feature jobs the CI/CD rows require, and improve the data generator to
the depth the ML track will later need.

Rewritten 2026-08-07 for the 7-day LLM-only scope.

## Rubric Rows This Phase Buys

| Row group | Points | What it needs |
|---|---:|---|
| RAG: data pipeline + data governance | 4 | ingestion, chunking, dedup, provenance metadata |
| Improve the Data Generator: simulate drift, label table, generator config | 4 | drift scenarios, label table, config-driven generation |
| CI/CD: RAG data pipeline, Job 1 (stream feature → OFFLINE), Job 2 (stream feature → ONLINE) | 6 | three deployable pipelines with CI workflows |
| Backing store for both Web APIs | (enables 18) | Feast online store + PGVector must exist before the APIs mean anything |

## Data Contracts

- **Structured Feast project.** Entity `ticker`. Feature views carry a correct
  `event_timestamp` and a declared **offline source** (parquet on in-cluster
  MinIO) even though only the online store is read this week — see phase-05's
  load-bearing decision 1. Online store is Redis in-cluster. TTL is documented per table from business
  freshness: market/stream features short, quarterly financial features long,
  document embeddings tied to document version.
- **RAG project.** PGVector in-cluster for online vectors and metadata; version
  manifests on object storage. Milvus is out of scope.
- **RAG chunk metadata.** Every chunk records source URI, company, report date,
  document hash, content hash, parser version, embedding model and version,
  created time, and access class. This metadata *is* the data-governance row —
  it is not decoration.
- **Label table.** `ticker`, `event_timestamp`, `label`, `label_version`,
  `created_ts`, `training_eligible`. Proxy labels are explicitly marked
  non-ground-truth. Required by the LLM rubric now and by the ML retrofit later.
- **Drift scenarios.** Financial deterioration and market stress, driven from
  configuration with deterministic seeds and before/after reports.

## Related Code Files

- Create: `src/llm/rag/` (ingestion, chunking, embedding, PGVector writer)
- Create: `src/drift/` (drift computation shared by the drift MCP tool and the future ML track)
- Modify: `src/generator/` (drift simulation, label table, generator configuration)
- Create: `dags/phase2/` thin wrappers — RAG pipeline, stream feature → offline, stream feature → online, label/drift table build
- Create: `feature_repo/` (Feast definitions: entity, feature views, offline + online store config)
- Create: `.github/workflows/` — one workflow per pipeline (RAG, job 1, job 2)

## Implementation Steps

1. Seed failing schema, idempotency, TTL, chunk-dedup and governance tests
   before implementing.
2. Improve the data generator: configuration-driven generation, two drift
   scenarios with deterministic seeds and before/after reports, and the label
   table. Do this to the depth the ML track will need — it is the same work and
   both tracks score it.
3. Build the RAG pipeline: fetch trusted sources → parse → chunk → deduplicate
   by content hash → embed → write to PGVector with the full metadata contract.
   Reprocessing an unchanged document must reuse its hashes rather than create
   duplicate vectors.
4. Define the Feast repository. Apply, materialize into the online store, and
   record the registry revision. The offline store is defined and materialized
   from, even though nothing reads it historically this week.
5. Build the two stream-feature jobs as separate deployables — push to the
   offline store, push to the online store — because the rubric scores them as
   two distinct CI/CD rows.
6. Build thin Airflow wrappers under `dags/phase2/` with zero import-time side
   effects. All business logic stays under `src/`. No Phase 1 DAG is renamed or
   modified.
7. Add retries, checkpoints, dead-letter/quarantine, source rate limits, content
   deduplication, and PII/licensing checks. These are the governance row.
8. Add one GitHub Actions workflow per pipeline: lint, test, build, push an
   immutable digest, open the GitOps digest PR.
9. Emit Phase 2 lineage into the existing DataHub instance for every input,
   step, feature view, vector set and output. Phase 1 lineage evidence is
   retained untouched.

## Validation

- `pytest` schema, idempotency and Hypothesis property tests.
- Feast plan/apply/materialize smoke test against a disposable store.
- Re-run each DAG and job twice; prove stable counts and hashes, and no
  duplicate online keys or chunks.
- Compare generated drift against the configured direction and threshold.
- `scripts/run_stage1_quality_gates.py` still passes — Phase 1 is unchanged.

## Success Criteria

- [ ] RAG pipeline -> reprocesses an unchanged document -> reuses its chunk and content hashes instead of writing duplicate vectors.
- [ ] Materialization job -> reruns the same interval -> produces no duplicate offline rows and identical online values.
- [ ] Stream publisher -> receives new records -> pushes to the offline store and the online store as two separately deployed jobs, each with captured success evidence.
- [ ] Data generator -> runs with a drift scenario configuration -> produces the configured drift direction and a before/after report with a deterministic seed.
- [ ] Reviewer -> inspects any RAG chunk -> finds source URI, company, report date, document and content hashes, parser version, embedding model and version, created time, and access class.
- [ ] Feature consumer -> queries the online store by `ticker` -> receives values whose TTL rationale is documented in the registry definition.
- [ ] Phase 1 maintainer -> runs the Stage 1 quality gates -> receives the same outputs and contracts as before Phase 2 adapters were added.

## Risk Assessment

- **Feast dependency conflicts.** Mitigated by `.venv-phase2` and by running the
  materialization jobs from a container image rather than the local environment.
- **Online-only shortcut.** Skipping the offline definition would save an hour
  now and cost three days in the phase-05 retrofit. Not negotiable.
- **RAG source availability.** Mitigated by caching fetched documents locally so
  evidence runs are reproducible without live network access.
- Rollback: disable the Phase 2 DAGs and restore the previous Feast registry
  revision; Phase 1 datasets remain authoritative and intact.

## Scope Changes

Dropped from the previous version: ElastiCache Valkey (in-cluster Redis instead;
no AWS anywhere in the platform), S3 as the offline store (in-cluster MinIO
instead), content-addressed base/delta
snapshot manifests, the scheduled Kubeflow-Pipelines drift-trigger contract, and
the point-in-time training notebook. All of those serve ML rows only and move to
the phase-05 retrofit. The offline store definition and the label table stay, on
purpose.
