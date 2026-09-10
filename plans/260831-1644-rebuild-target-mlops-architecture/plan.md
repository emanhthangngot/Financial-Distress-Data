---
title: "Rubric-first financial AI platform: temporal data, evaluated RAG and LangGraph agents"
description: "Upgrade the unified rebuild in place: 161 rubric rows, verified temporal data, bounded LangChain/LangGraph agents, free inference and Kaggle experiments."
status: pending
priority: P1
effort: "Re-estimate from unfinished ACs after P0 inventory; previous 111-158 day estimate is not a current commitment"
branch: dev
tags: [coursework, ml, llm, temporal-data, rag, langchain, langgraph, kaggle, gitops]
blockedBy: []
blocks: [260802-1037-unified-phase2-ml-llm-gitops, 260806-2234-architecture-hygiene-before-phase-3, 260809-2039-complete-phase2-llm-submission, 260811-1627-close-llm-rubric-to-100, 260813-1846-production-hardening-overlay, 260814-2218-production-feast-ghcr, 260818-0832-rebuild-unified-ml-and-llm-platform]
created: 2026-08-31
revised: 2026-09-10
---

# Rubric-first financial AI platform

## Overview and accepted outcome

Update this plan in place; do not execute its predecessor plans concurrently. Deliver all three
checked-in rubrics (mini 44/100, ML 57/100, LLM 60/100: 161 rows / 300 points), plus the selected
session extensions below. JD coverage guides useful extensions; full nice-to-have coverage is not
an acceptance condition. This is a plan, not a claim that deployment or scoring is complete.

User flow: authenticated analyst selects ticker and knowledge cutoff, requests a risk explanation,
receives deterministic financial calculations and model output with eligible document citations,
source/vintage provenance, and explicit missing-data or unavailable states. No future information
or target labels may enter the predictor/context path.

## Decision ledger — 2026-09-10 replaces conflicting earlier design decisions

| Decision | Binding contract | Owner |
|---|---|---|
| Rubric before image fidelity | Every rubric row remains required. The old 83-component image is a historical reference, not a deployment checklist. No automatic point cuts. | P3/P12 |
| No additional monetary spend | No paid API route, subscription, GPU rental or unverified cloud apply. Free credits are usable only after validity, residual charges and teardown are verified. Missing capacity blocks the affected live AC, not local development. | P0/P6 |
| Session demo | Domain + HTTPS, authentication, gateway and cloud evidence remain required where named. No public URL 24/7 requirement; private/local HTTPS acceptance is not assumed. | P9/P12 |
| Data before model claims | Repair SCD2 replay, label joins, vintage preservation, as-of returns and real rolling features before training or quality comparisons. | P2/P4/P5 |
| LangChain + LangGraph | Model/tool integration and bounded stateful agent orchestration. One parity pilot, then clean cutover of the old agent implementation; retain MCP servers, API compatibility, auth and telemetry. Not an ETL rewrite. | P8 |
| Free inference | Groq Free primary; one independently verified free provider, Gemini candidate. Models/capabilities/quota rechecked per account. Never silently fall back during evaluation or after partial streaming. | P0/P8 |
| Evaluated RAG | pgvector retained; temporal/authorization filters before context; source-supported citations; human-reviewed eval. Hybrid retrieval and reranker are paired experiments, kept only on measured improvement. | P8/P11 |
| Kaggle | MCP-controlled bounded GPU batch jobs, artifact manifests/checksums/resume. Not permanent hosting, a cloud-IaC substitute, or a replacement for graded KFP/distributed training. | P7 |
| Fine-tuning | Conditional narrow-task experiment after prompt/RAG baseline and licensed dataset; defer is an honest decision outcome. No automatic LoRA, QLoRA, full training, RLHF or DPO. | P7 |
| Memory | Session-only state, scoped identity and TTL; no automatic cross-session semantic memory. | P8/P9 |
| Keep nonduplicative infrastructure | PostgreSQL/pgvector, Airflow, Feast, Kafka/Flink, Spark, KFP, MLflow and the necessary deployment/security/observability capabilities. Retain working choices; no second vector DB or hosted tracing stack merely for logos. | Respective phases |

### Non-goals

No investment/trading advice guarantee, arbitrary shell/code-execution agent, GraphRAG, new entity
registry without a real source, multiple competing agent frameworks, paid inference, 24/7 SLA,
or claim that this project replaces employment experience. Do not delete working auth or CI only
to match an image. Non-rubric additions (Kiali, Trino/Superset/dbt, Triton, llm-d/LWS/GIE, Jenkins)
are not automatic new deployments; reuse existing working instances when no-spend, otherwise
require a capability-specific justification. Actual rubric capabilities are never replaced by stubs.

## Observed baseline and source of truth

The existing code is partially migrated; `status: pending` does not mean every file is v1.
Read source and executed evidence before each phase. V2 is the P2 contract; do not copy it into
unowned v1 callers ahead of their cutover. Preserve existing evidence with a resolvable
`evidence-baseline-pre-rebuild` tag before deleting any evidence tree; regenerate affected evidence,
not claimed scores. No evidence deletion occurs during this planning update.

Session probes found: Python OBT assigns Q2 label to Q1 when both share a company-version key;
OBT keeps only one of two vintages; two report periods sharing knowledge time produce duplicate
feature keys; replaying an old SCD2 snapshot creates an inverted interval; a future price correction
turns a correct +10% historical return into -45%. Source anchors: `src/transforms/gold/`,
`src/transforms/features/pit.py`, `src/jobs/lakehouse_spark_lakehouse_job.py`.
These are repair targets, not evidence of completed repairs.

Three CSVs under `docs/Coursework Tracking (Public) - rubic*.csv` are scoring authority.
`docs/rubric-matrix-unified.csv` is the existing row-ID/ownership index. P3 reconciles it, never
rebuilds it by appending duplicate rows or fabricating points for session extensions. Old docs and
ADR claims must be reconciled with code; `docs/07_data_contracts.md` still contains legacy shapes.

## Phases

Phase IDs/files remain stable. Status is read from phase files and indexed by `ak plan reindex`.
The original effort figures are historical baselines, not promised duration under free quotas.

| Phase | Contract | Depends on |
|---|---|---|
| P0 | [Resource, compatibility and zero-spend gates](./phase-00-gates.md) | — |
| P1 | [Remaining naming cutover](./phase-01-naming-cutover.md) | P0 local gate |
| P2 | [Temporal model, grain and metadata](./phase-02-data-model.md) | P1 |
| P3 | [Rubric ownership, ADRs and contract reconciliation](./phase-03-contracts-rubric.md) | P1, P2 |
| P4 | [Data plane and Spark parity](./phase-04-data-plane.md) | P0, P2, P3 |
| P5 | [Streaming, real rolling features and Feast](./phase-05-cdc-streaming.md) | P4 |
| P6 | [Windowed platform, security and cloud evidence](./phase-06-platform.md) | P0, P3 |
| P7 | [ML pipeline, Kaggle experiments and conditional LoRA](./phase-07-ml-track.md) | P4, P5, P6 |
| P8 | [Evaluated RAG, LangGraph agents and free inference](./phase-08-llm-agent-track.md) | P0, P6; data integration gates P4/P5 |
| P9 | [Serving, UI and protected domain/HTTPS demo](./phase-09-serving-edge.md) | P4, P5, P6, P8 |
| P10 | [Per-artifact delivery and release gates](./phase-10-delivery.md) | P6, P7, P8, P9 |
| P11 | [Quality, functional eval and regression gates](./phase-11-quality-engineering.md) | P2; live checks require their producing phases |
| P12 | [Observability, incremental evidence and freeze](./phase-12-observability-evidence.md) | P10, P11 |

### Scheduling and dependency boundaries

P0 has a local inventory gate and independent live-resource gates. Local work may proceed with
cloud blocked. Phase dependencies describe integration/exit: P7 local notebooks/Kaggle preparation
may run before P6 live evidence; P8 baseline/eval scaffolding may run before live deployment.
P8 must integrate P4/P5 data before its end-to-end exit. P11 defines evaluation fixtures and metrics
early, then runs consumer checks after P7/P8/P9 exist. P10 receives P11's eval results as a release
subgate, not a reciprocal whole-phase dependency. P12 telemetry capture runs incrementally; its
final freeze is not a prerequisite to P10 canary baseline measurements.

No free-tier queue time or historical credit expiry is treated as a guaranteed deadline. Schedule
by completed ACs and resource windows. Missing cloud resources yield `blocked/unverified` evidence,
never a local test relabeled as cloud deployment or a silent lower-point submission.

## File ownership and shared mutations

- P1: residual renames only, serialized with all writers. Applied Supabase migration filenames and historical plans remain untouched by code naming cleanup.
- P2: `src/transforms/`, `src/metadata/`, `src/quality/`, `sql/`, `src/io/paths.py`; data contract design and DQ.
- P3: `docs/rubric-matrix-unified.csv`, `docs/platform/adr/`, `scripts/verify_*.py`, `scripts/_rubric_items.py`, canonical data dictionary reconciliation.
- P4: `src/lakehouse/`, collectors/generator, `src/jobs/`, data-plane deployment; mirror P2 contract in Spark jobs.
- P5: CDC/streaming, `src/ml/feast/`, `feature_repo/`, feature deployment; consumes P2/P4 outputs.
- P6: mesh, Vault/ESO, Terraform and Ansible; workload namespace edits serialized with their owning phase.
- P7: ML pipelines/registry/promotion, ML notebooks, Kaggle job packaging/artifacts, KFP/distributed training/model serving.
- P8: `src/llm/`, `src/agents/`, LLM notebooks, agent/inference/gateway deployment, Python dependency additions for LangChain/LangGraph.
- P9: API/MCP application handlers, `apps/web/`, Helm charts and NGINX routes; UI integration preserves existing public contracts.
- P10: CI workflows, release automation and rollout policy; no routine CI replacement.
- P11: quality/eval test harness and reviewed datasets, load/mutation/property tests, Docker optimization. Contract owners may propose regression tests; P11 owns final shared-test integration.
- P12: `src/observability/telemetry.py`, observability deployments, final docs/evidence and capture runner. P8/P10 consume agreed instrumentation interfaces; serialize edits here.

`pyproject.toml`, shared tests, docs and GitOps namespace fields are integration boundaries, not
independent parallel ownership. One owning phase integrates proposals; do not declare P7/P8
notebooks or P3/P12 docs automatically disjoint by directory alone.

## Cross-plan resolution

Unfinished predecessor plans listed in `blocks` contain overlapping v1/LLM-only/paid-capacity
contracts. They are historical inputs; any resumed work in their overlap must wait for and use this
revised contract. Their original execution records remain unchanged. This plan does not depend on
those predecessors, preventing cycles. Completed auth/documentation plans remain historical and
are not reopened. The unrelated skill-activation policy is not a dependency.

## Acceptance contract

- [ ] O-1: Architect -> verifies selected deployment inventory against actual resources -> required rubric capabilities have runnable components; image-only omissions are explained, not mandatory 83-component parity.
- [ ] O-2: Rubric auditor -> checks all source rows and owning-phase ACs -> 44 mini + 57 ML + 60 LLM, 300 points, zero missing owners/citations; final evidence is executed and attributable.
- [ ] O-3: Engineer -> completes residual naming and schema cutover -> callers/docs/tests agree; no no-op rename or parallel legacy agent path remains.
- [ ] O-4: Data pipeline -> reruns historical queries with future corrections present -> same eligible vintage/features/labels; no knowledge-time leakage.
- [ ] O-5: Evidence runner -> loads populated outputs and adversarial inputs -> fails on incorrect grain/FK/NULL-rate/temporal invariants rather than merely counting DDL declarations.
- [ ] O-6: Release operator -> promotes and rolls back a versioned release -> compatible model, data, prompt and dependency artifacts restored; state migrations have explicit recovery plans.
- [ ] EXT-AGENT: Analyst -> uses LangGraph-backed existing API/UI -> correct scoped MCP calls, bounded steps, citations, missing-data and provider-unavailable states; old implementation removed after parity.
- [ ] EXT-EVAL: Evaluator -> runs a human-reviewed fixed corpus -> per-case retrieval/answer/agent metrics with frozen revisions; deterministic safety/temporal cases have zero violations.
- [ ] EXT-COST: Operator -> inspects provider allowlist and resource-window ledger -> zero paid API routes and zero unapproved additional spend; depleted resources fail closed.
- [ ] EXT-KAGGLE: Experiment controller -> accepts a COMPLETE job and validates downloaded outputs -> manifest, hashes, per-case metrics and replay inputs available; no secret disclosure.
- [ ] EXT-FT: ML owner -> applies fine-tuning eligibility gate -> documented defer or paired narrow-task experiment; no trained-adapter/Groq compatibility assumed.

## Verification and handoff

Implementation uses the existing one-shot gate `.venv/bin/python scripts/run_lakehouse_quality_gates.py`;
run specific regressions first and the full gate before declaring a code change done. Deployment
ACs require actual runtime exercises, source-only tests cannot substitute. New proposed commands
in phase files must first be implemented by their named owner; never report them as already run.

Planning verification: parse frontmatter/dependency paths; check all 161 rubric IDs remain cited in
the owning phase; check links and shared contracts; review all phase files after edits. CLI format
validation is not a semantic review and not evidence that implementation ACs passed.

## Resource blockers and decision gates

- Cloud quota/free credit/account state unverified: P0/P6 live ACs blocked until a no-additional-spend window is demonstrated. Billing alerts alone are not a hard spend cap.
- Groq/Gemini account limits and model tool/stream support unverified: runtime capability smoke before pinning models. Free-tier terms may change.
- Kaggle access/GPU quota unverified: no hardware size assumption; local preflight and resumable jobs first.
- Domain delegation/certificate trust unavailable: P9 HTTPS AC remains open; self-signed/local-only proof not silently accepted.
- LangGraph pilot breaks API/security/state parity: do not cut over; fix adapter boundaries and re-run the same eval. No second permanent runtime.

Historical audit reports and `reports/gate-decisions.md` are dated observations, not authority to
spend or enforce the retired image topology. P0 records fresh facts separately before live work.
