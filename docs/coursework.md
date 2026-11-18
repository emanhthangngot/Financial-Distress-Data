# Financial Distress Data + AI Engineering — Platform Coursework

## 1. Purpose

This document records the accepted platform coursework scope. It supersedes
the early vision draft that treated Kubernetes and LLM work as optional
extensions; the LLM deployment is part of the coursework rubric.

For current setup, use the [operator runbook](operator-runbook.md).
The GKE and GitOps references below describe the coursework submission,
not a default deployment target for this source checkout.

The local lakehouse is the foundation; its contracts are linked here rather
than duplicated. The coursework adds a persistent product plane and a
disposable GKE evidence plane without changing the lakehouse contract.

> **Submission scope — 2026-08-13
> ([ADR-010](./platform/adr/adr-010-llm-only-scope-and-platform-simplification.md)).**
> The coursework accepts delivery of one of the two tracks. This submission
> delivers the **LLM track: 60 rows / 100 points**. The 57 ML rows remain in
> `docs/platform/rubric-matrix.csv` and in the acceptance catalog as a deferred,
> post-deadline retrofit ([ML-track plan](../plans/260802-1037-unified-phase2-ml-llm-gitops/phase-05-deliver-ml-track.md));
> they are not claimed as delivered. The recorded GKE checks and the
> submission freeze rules are separate; see [historical evidence](operator-runbook.md#historical-phase-2-evidence).

## 2. Normative Documents

| Document | Role |
|---|---|
| `docs/mini_coursework.md` | Local lakehouse technical spec |
| `docs/01_data_generator.md` | Data generator contract |
| `docs/architecture/data-model.md` | Lakehouse schema design contract |
| `docs/platform/requirements.md` | Platform requirements |
| `docs/platform/acceptance-criteria.md` | Resolvable WHO -> ACTION -> RESULT acceptance catalog |
| `docs/platform/rubric-matrix.csv` | Machine-readable 200-point evidence contract |
| `docs/platform/rubric-matrix.md` | Human-readable rubric matrix |
| `docs/platform/architecture.md` | Two-plane coursework architecture |
| `docs/platform/low-level-design.md` | Platform class contracts |
| `docs/platform/evidence-contract.md` | Evidence format and linter contract |
| `docs/platform/product.md` | Product UI contract and the three approved visual reference IDs |
| `docs/platform/security/rbac.md` | Product route/action RBAC and server/RLS security boundary |
| [Architecture decisions](platform/adr/) | The coursework-specific scope decision is ADR-010 |
| [Execution plan](../plans/260802-1037-unified-phase2-ml-llm-gitops/plan.md) | Coursework implementation phases |

## 3. One-Sentence Summary

The coursework pairs a **persistent product plane** with a **disposable
evidence plane**. See the [coursework architecture](platform/architecture.md)
for the captured topology and the rationale for the two-plane split.

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
  [ML-track plan](../plans/260802-1037-unified-phase2-ml-llm-gitops/phase-05-deliver-ml-track.md).
  The 57 ML rows stay in the rubric matrix as `design_only` rather than being
  deleted.

### Out of scope

- AWS Glue/Athena/EMR/MSK/SageMaker as the primary pipeline; the system uses
  Kubernetes, Terraform, Helm, Argo CD and agentgateway.
- Istio, Envoy Gateway/AI Gateway, ECK/Kibana, Vault, Kustomize, and the
  ML-only KServe/Knative/MLflow training or retraining path remain deferred or
  dropped per ADR-010. The submitted LLM serving path does use the restored
  KServe/Knative CPU model server through agentgateway.
- Changes to the local lakehouse pipeline semantics.
- Anything not in the rubric matrix.

## 5. Design Constraints

- Evidence plane budget: GCP free-trial credit only, with node pools and the
  evidence VM hibernated outside capture windows and a target under USD 100 of
  the available credit. The teardown command is run at the end of every
  capture session.
- The evidence plane is disposable: no long-lived cloud credential, private
  key, real `.env`, or production Supabase credential is
  placed on it, and any token there is short-lived and revoked at session end.
- Local-first development remains. GCP was selected for the coursework
  evidence plane, not as a prerequisite or default for the source checkout.
- One resource has one owner. Helm is the only render tool, so this holds by
  construction (ADR-007 as superseded by ADR-010).

## 6. Lakehouse boundary

The platform consumes lakehouse Gold outputs without changing the lakehouse
contracts. See [repository ownership](architecture/repository-map.md) for
source boundaries and [the evidence contract](platform/evidence-contract.md)
for the separate coursework evidence locations.

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

## 7.2 Historical verification and submission state

The [dated verification snapshot](platform/architecture.md#6-verification-and-residuals)
records the GKE and product checks and remaining gaps. It is not a claim of
current runtime health or proof of a submission freeze. See the [submission
reviewer index](submission/README.md) for the submission checklist.

## 7.3 Coursework delivery model

The historical coursework run promoted signed images through reviewed
GitOps PRs and Argo CD, as recorded in the [CI/CD narrative](<submission/rubric-final-coursework-(final-llm)/ci_cd.md>).
For the current source-only workflow, use the [external deployment handoff](operator-runbook.md#external-deployment-handoff).

## 8. Evidence Contract

See the [evidence contract](platform/evidence-contract.md) for the required
metadata and evidence locations. The [historical audit route](operator-runbook.md#historical-phase-2-evidence)
identifies the CLI and why the checkouts must match the capture. Do not
regenerate canonical receipts to validate a different checkout.

## 9. Exit Criteria

- The submitted LLM rows have machine-checked evidence and the final strict
  two-repository linter (`--require-executed --run-validations --track LLM`)
  passes without `--accept-design-only`; the 57 ML rows remain visibly
  `design_only`. Runtime verification is not a substitute for the strict audit.
- The lakehouse regression suite passes without changing the mini-coursework
  contract.
- The coursework evidence plane meets the cost envelope.
- The two LLM novel ideas have evidence; ML novel ideas remain with the
  deferred ML track.
