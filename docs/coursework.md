# Financial Distress Data + AI Engineering — the platform Coursework (Accepted Source of Truth)

## 1. Purpose

This document is the **accepted the platform source of truth** for the Financial
Distress Data + AI Engineering coursework. It supersedes the earlier vision
draft that described Kubernetes, AWS, and LLM as "optional future
extensions." the platform is explicit, planned, and rubric-scored.

the platform remains the verified local lakehouse foundation; its contracts are
linked, not duplicated, here. the platform builds an AI system on top of it with a
disposable GKE evidence plane and a persistent product plane.

> **Submission scope — 2026-08-13
> ([ADR-010](./platform/adr/adr-010-llm-only-scope-and-platform-simplification.md)).**
> The coursework accepts delivery of one of the two tracks. This submission
> delivers the **LLM track: 60 rows / 100 points**. The 57 ML rows remain in
> `docs/platform/rubric-matrix.csv` and in the acceptance catalog as a deferred,
> post-deadline retrofit (`plans/260802-1037-unified-platform-ml-llm-gitops/phase-05-deliver-ml-track.md`);
> they are not claimed as delivered. Evidence runs on the cost-bounded GKE
> cluster owned by the private `financial-distress-gitops` repository. The
> runtime is live-verified and the 60 rows are logically covered; the final
> submission freeze remains pending until the post-commit source/GitOps SHA
> restamp and strict two-repository audit pass.

## 2. Normative Documents

| Document | Role |
|---|---|
| `docs/mini_coursework.md` | the platform technical spec and source of truth (unchanged) |
| `docs/01_data_generator.md` | the platform data generator contract |
| `docs/architecture/data-model.md` | the platform schema design contract |
| `docs/platform/requirements.md` | the platform top-level requirements |
| `docs/platform/acceptance-criteria.md` | Resolvable WHO -> ACTION -> RESULT acceptance catalog |
| `docs/platform/rubric-matrix.csv` | Machine-readable 200-point evidence contract |
| `docs/platform/rubric-matrix.md` | Human-readable rubric matrix |
| `docs/platform/architecture.md` | the platform two-plane architecture |
| `docs/platform/low-level-design.md` | the platform class contracts |
| `docs/platform/evidence-contract.md` | Evidence format and linter contract |
| `docs/platform/product.md` | Product UI contract and the three approved visual reference IDs |
| `docs/platform/security/rbac.md` | Product route/action RBAC and server/RLS security boundary |
| `docs/platform/adr/adr-001..010-*.md` | the platform architecture decision records; ADR-010 supersedes 001/003/004/007, amends 005, defers 006 |
| `plans/260802-1037-unified-platform-ml-llm-gitops/` | the platform execution plan (phase-01..08) |

## 3. One-Sentence Summary

the platform delivers a two-plane AI system: a **persistent product plane**
(Next.js + Supabase Auth/Postgres) and a **disposable evidence plane** (GKE,
F5 NGINX, Argo CD, agentgateway, a KServe/Knative CPU model server, agents,
MCP tools, Feast/PGVector and the observability stack), orchestrated by GitOps
through a separate private repository. This submission targets the 100-point
LLM track; the ML track remains a documented retrofit. Live runtime checks have
passed; final evidence freeze is pending SHA convergence.

## 4. Scope

### In scope (explicit)

- **Product plane:** Next.js web app, Supabase Auth/Postgres RLS, evidence-
  session worker, honest plane state machine (ADR-008), and the approved
  analyst/chat/registry UI surfaces (`UI-APPROVED-01..03`).
- **LLM track (100 pts, submitted):** RAG ingestion with governance metadata,
  embedding versioning with hot-swap (novel idea), a custom CPU-served model
  behind agentgateway with a benchmarked optimization, one global kagent
  `ModelConfig` (ADR-001 as amended by ADR-010), two MCP tools (feature/RAG
  retrieval and real-time drift), two specialist agents plus a coordinator in a
  restricted sandbox namespace, an agent registry with its UI, an authenticated
  agent chat UI, warm-up mode, A/B testing, and a citation/PII guard with
  trace-linked decisions.
- **Feature/data foundation:** Feast structured and RAG stores (ADR-005 as
  amended), point-in-time-correct offline definitions, both stream-feature
  jobs, the label table, and configured drift scenarios.
- **Platform:** cost-bounded GKE evidence cluster, one source monorepo plus a
  separate private GitOps control repo (ADR-002), Helm as the only render tool,
  active
  F5 NGINX Ingress Controller OSS rather than the retired community
  ingress-nginx project (ADR-009), observability
  (Prometheus/Grafana/Loki/OpenTelemetry/Jaeger), and one timeboxed GCP session
  for Terraform, TLS and cost evidence.
- **Novel ideas:** two for the LLM track, recorded before implementation, each
  with a proof path (see `docs/platform/novel-ideas.md`).

### Deferred (not claimed in this submission)

- **ML track (100 pts):** feature store training reads, point-in-time training
  splits, Kubeflow Pipelines/Trainer, MLflow experiment tracking and the
  promotion contract (ADR-006), KServe ML inference, Knative Eventing drift.
  Backlog and retrofit contract:
  `plans/260802-1037-unified-platform-ml-llm-gitops/phase-05-deliver-ml-track.md`.
  The 57 ML rows stay in the rubric matrix as `design_only` rather than being
  deleted.

### Out of scope

- AWS Glue/Athena/EMR/MSK/SageMaker as the primary pipeline; the system uses
  Kubernetes, Terraform, Helm, Argo CD and agentgateway.
- Istio, Envoy Gateway/AI Gateway, ECK/Kibana, Vault, Kustomize, and the
  ML-only KServe/Knative/MLflow training or retraining path remain deferred or
  dropped per ADR-010. The submitted LLM serving path does use the restored
  KServe/Knative CPU model server through agentgateway.
- Changes to the platform pipeline semantics; the platform continues to run with
  identical outputs.
- Anything not in the rubric matrix.

## 5. Design Constraints

- Evidence plane budget: GCP free-trial credit only, with node pools and the
  evidence VM hibernated outside capture windows and a target under USD 100 of
  the available credit. The teardown command is run at the end of every
  capture session.
- The evidence plane is disposable: no long-lived cloud credential, private
  key, real `.env`, or production Supabase credential is
  placed on it, and any token there is short-lived and revoked at session end.
- Local-first development remains; GCP is an explicit, deliberate deployment
  target owned by the GitOps repo, not a the platform mutation.
- One resource has one owner. Helm is the only render tool, so this holds by
  construction (ADR-007 as superseded by ADR-010).

## 6. the platform Relationship

- the platform is the verified foundation: Airflow, Kafka, PySpark, MinIO,
  PostgreSQL, DuckDB, DBeaver, and Bronze/Silver/Gold evidence.
- the platform reads Gold tables/features and writes the platform evidence under
  `docs/platform/evidence/{ml,llm}/`, never mutating `docs/evidence/`.
- the platform code lives under `src/ml/`, `src/drift/`, `src/llm/`,
  `src/agents/`, and `apps/`; thin the platform orchestration wrappers may live in
  `dags/platform/` and import all business logic from those roots.

## 7.1 Mandatory Closure Paths (LLM track)

- Agents reference one global kagent `ModelConfig`; its upstream/base URL points
  to an agentgateway AI backend, which routes model traffic to the
  OpenAI-compatible CPU model server. MCP and A2A calls also traverse declared
  agentgateway routes. A negative test proves an agent cannot reach the model
  server directly.
- Every backend is `ClusterIP` behind a default-deny NetworkPolicy, with NGINX
  Ingress OSS as the only externally reachable object. Proof is a refused direct
  call plus a successful routed call over HTTPS.
- Agents run in the `agents-sandbox` namespace under restricted Pod Security
  Standards with a tokenless ServiceAccount, a read-only root filesystem and an
  egress allow-list. Proof is three negative demonstrations from inside an agent
  pod.
- Ansible is mandatory, not a stretch item: a role-based playbook configures the
  disposable evidence VM used to administer the GKE evidence plane, proves
  health, and reports `changed=0` on a second run.
- The ML drift-to-retraining closure path (Airflow -> Feast offline ->
  Evidently -> Pushgateway -> threshold -> Kubeflow Pipelines API run) is
  deferred with the ML track and is not claimed in this submission.

## 7.2 Current implementation and submission state

The complete product/evidence path is implemented and has been live-verified
on the GKE evidence plane as of 2026-08-13:

- 13/13 Argo CD applications are `Synced` and `Healthy`.
- kagent CRDs are established and 10 agents report `Ready`.
- The feature/drift MCP path, agentgateway model route, and
  KServe/Knative CPU model server respond through the declared boundaries.
- The coordinator round-trip returns HTTP 200 with feature and drift
  citations; Prometheus targets are healthy and Jaeger services are visible.
- The product plane has authenticated analyst/report, registry, chat, and
  evidence-session surfaces covered by product/browser checks.

This is a runtime verification snapshot, not the final submission seal. The
canonical the platform evidence package represents 60/60 LLM rows and 100/100
logical points, but source and GitOps SHA stamps must be regenerated after the
latest commits and the strict two-repository audit must pass without an
acceptance cut before submission.

## 7. Implementation Model

```text
the platform code -> source CI (test/build/scan/sign) -> immutable image digest
  -> GitOps repo PR (desired digest) -> Argo CD reconcile -> evidence plane
Product plane <-> Supabase <-> evidence-session worker <-> outbox <-> GKE cluster
```

Full step-by-step execution is in
`plans/260802-1037-unified-platform-ml-llm-gitops/plan.md` (phase-01..08).

## 8. Evidence Contract

Every rubric point must be proven by evidence under
`docs/platform/evidence/{ml,llm}/` recording rubric_id, timestamps, source SHA,
GitOps SHA, versions, reproduction steps, and redaction status
(`docs/platform/evidence-contract.md`). The linter
(`scripts/audit_phase2_evidence.py`) enforces canonical 57+60 source coverage
at specification time and, with `--require-executed --run-validations
--gitops-root ...`, gates both repositories at phase-08.

## 9. Exit Criteria

- The submitted LLM rows have machine-checked evidence and the final strict
  two-repository linter (`--require-executed --run-validations --track LLM`)
  passes without `--accept-design-only`; the 57 ML rows remain visibly
  `design_only`. At this documentation refresh, this freeze criterion is
  still pending SHA restamping.
- the platform regression suite stays green; `docs/mini_coursework.md` semantics
  unchanged.
- Two-plane architecture runs within the cost envelope.
- Four novel ideas (2 ML, 2 LLM) are implemented and evidenced.
