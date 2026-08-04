# Financial Distress Data + AI Engineering — Phase 2 Coursework (Accepted Source of Truth)

## 1. Purpose

This document is the **accepted Phase 2 source of truth** for the Financial
Distress Data + AI Engineering coursework. It supersedes the earlier vision
draft that described Kubernetes, AWS, and LLM as "optional future
extensions." Phase 2 is explicit, planned, and rubric-scored.

Phase 1 remains the verified local lakehouse foundation; its contracts are
linked, not duplicated, here. Phase 2 builds an AI system on top of it with an
ephemeral Kubernetes evidence plane and a persistent product plane, targeting
all 100 ML rubric points and all 100 LLM rubric points.

## 2. Normative Documents

| Document | Role |
|---|---|
| `docs/mini_coursework.md` | Phase 1 technical spec and source of truth (unchanged) |
| `docs/01_data_generator.md` | Phase 1 data generator contract |
| `docs/02_schema_design.md` | Phase 1 schema design contract |
| `docs/phase2/requirements.md` | Phase 2 top-level requirements |
| `docs/phase2/acceptance-criteria.md` | Resolvable WHO -> ACTION -> RESULT acceptance catalog |
| `docs/phase2/rubric-matrix.csv` | Machine-readable 200-point evidence contract |
| `docs/phase2/rubric-matrix.md` | Human-readable rubric matrix |
| `docs/phase2/architecture.md` | Phase 2 two-plane architecture |
| `docs/phase2/low-level-design.md` | Phase 2 class contracts |
| `docs/phase2/evidence-contract.md` | Evidence format and linter contract |
| `docs/phase2/product.md` | Product UI contract and the three approved visual reference IDs |
| `docs/phase2/security/rbac.md` | Product route/action RBAC and server/RLS security boundary |
| `docs/phase2/adr/adr-001..009-*.md` | Phase 2 architecture decision records |
| `plans/260802-1037-unified-phase2-ml-llm-gitops/` | Phase 2 execution plan (phase-01..08) |

## 3. One-Sentence Summary

Phase 2 delivers a two-plane AI system: a **persistent product plane**
(Next.js on Vercel Hobby + Supabase Auth/Postgres) and a **disposable evidence
plane** (EKS + KServe 0.18 + Kubeflow + Feast + MLflow + agents in
`ap-southeast-1`), orchestrated by GitOps through a separate repository, that
proves all 100 ML + 100 LLM rubric points within a strict cost envelope.

## 4. Scope

### In scope (explicit)

- **Product plane:** Next.js web app, Supabase Auth/Postgres RLS, evidence-
  session worker, honest plane state machine (ADR-008), and the approved
  analyst/chat/registry UI surfaces (`UI-APPROVED-01..03`).
- **ML track (100 pts):** feature store (Feast structured), point-in-time
  correctness, training pipelines (Kubeflow Pipelines/Trainer), MLflow
  experiment tracking and promotion contract (ADR-006), KServe inference,
  data/drift quality (Feast + Evidently/Drift).
- **LLM track (100 pts):** RAG ingestion, embedding versioning with hot-swap
  (novel idea), custom Qwen3-4B served via KServe `LLMInferenceService`,
  Envoy AI Gateway + agentgateway (ADR-001), MCP tools (Feast feature +
  RAG retrieval), agent orchestration, citation/PII guard with trace-linked
  decisions.
- **Platform:** ephemeral EKS (ADR-003), KServe 0.18 pin (ADR-004), one source
  monorepo plus a separate GitOps control repo (ADR-002), Helm/Kustomize
  ownership (ADR-007), active F5 NGINX Ingress Controller OSS rather than the
  retired community ingress-nginx project (ADR-009), Feast structured + RAG
  stores (ADR-005), observability (Prometheus/ECK/OpenTelemetry/Jaeger).
- **Novel ideas:** four recorded before implementation, two per track, each
  with a proof path (see `docs/phase2/novel-ideas.md`).

### Out of scope

- AWS Glue/Athena/EMR/MSK/SageMaker as the primary pipeline; the system uses
  EKS, Terraform, Helm/Kustomize, Argo CD, KServe, and Kubeflow.
- Changes to Phase 1 pipeline semantics; Phase 1 continues to run with
  identical outputs.
- Anything not in the rubric matrix.

## 5. Design Constraints

- Evidence plane budget: ≤ USD 25/session, ≤ USD 10/month persistent, hard TTL
  8 hours, ≤ 3 sessions/month, provisioning blocked above USD 85 − USD 15
  reserve (see `docs/phase2/architecture.md`, ADR-003).
- Local-first development remains; AWS is an explicit, deliberate deployment
  target owned by the GitOps repo, not a Phase 1 mutation.
- One resource has one owner (Helm/Kustomize/Argo CD/KServe) — ADR-004/007.

## 6. Phase 1 Relationship

- Phase 1 is the verified foundation: Airflow, Kafka, PySpark, MinIO,
  PostgreSQL, DuckDB, DBeaver, and Bronze/Silver/Gold evidence.
- Phase 2 reads Gold tables/features and writes Phase 2 evidence under
  `docs/phase2/evidence/{ml,llm}/`, never mutating `docs/evidence/`.
- Phase 2 code lives under `src/ml/`, `src/drift/`, `src/llm/`,
  `src/agents/`, and `apps/`; thin Phase 2 orchestration wrappers may live in
  `dags/phase2/` and import all business logic from those roots.

## 7.1 Mandatory 100/100 Closure Paths

- ML drift monitoring is an executed Airflow chain: Feast offline pull ->
  reference/proxy comparison -> Evidently metrics -> Prometheus Pushgateway ->
  Grafana -> threshold gate -> Kubeflow Pipelines API run. Both below-threshold
  skip and above-threshold retrain cases are evidenced with the KFP run ID.
- Agents reference a kagent `ModelConfig`; its upstream/base URL points to an
  agentgateway AI backend, which routes model traffic to Envoy AI Gateway and
  finally KServe `LLMInferenceService`/llm-d. MCP and A2A calls also traverse
  declared agentgateway routes.
- Ansible is mandatory, not a stretch item: a role-based playbook configures a
  bounded Vast.ai CPU evidence worker, deploys an OpenAI-compatible Locust/
  benchmark client against the llm-d endpoint, proves health and an idempotent
  second run, and stays under an aggregate USD 10 hard cap. It is isolated from
  the AWS GPU inference pool.

## 7. Implementation Model

```text
Phase 2 code -> source CI (test/build/scan/sign) -> immutable image digest
  -> GitOps repo PR (desired digest) -> Argo CD reconcile -> evidence plane
Product plane <-> Supabase <-> evidence-session worker <-> outbox <-> EKS
```

Full step-by-step execution is in
`plans/260802-1037-unified-phase2-ml-llm-gitops/plan.md` (phase-01..08).

## 8. Evidence Contract

Every rubric point must be proven by evidence under
`docs/phase2/evidence/{ml,llm}/` recording rubric_id, timestamps, source SHA,
GitOps SHA, versions, reproduction steps, and redaction status
(`docs/phase2/evidence-contract.md`). The linter
(`scripts/audit_phase2_evidence.py`) enforces canonical 57+60 source coverage
at specification time and, with `--require-executed --run-validations
--gitops-root ...`, gates both repositories at phase-08.

## 9. Exit Criteria

- All 100 ML + 100 LLM rubric points have machine-checked evidence (linter
  `--require-executed` passes, phase-08).
- Phase 1 regression suite stays green; `docs/mini_coursework.md` semantics
  unchanged.
- Two-plane architecture runs within the cost envelope.
- Four novel ideas (2 ML, 2 LLM) are implemented and evidenced.
