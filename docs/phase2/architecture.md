# Phase 2 Architecture — Two Planes, One Evidence Contract

## Overview

Phase 2 uses two planes:

- **Product plane (persistent, low cost):** Next.js on Vercel Hobby +
  Supabase Auth/Postgres on Free. Always available. Shows persisted reports
  and an honest evidence-plane state machine.
- **Evidence plane (disposable, bounded budget):** EKS in `ap-southeast-1`,
  6-hour default / 8-hour hard TTL, ≤ 3 sessions/month, ≤ USD 25/session,
  ≤ USD 10/month persistent. Provisioned and destroyed through GitOps.

Four traffic layers are normative: **NGINX** (public TLS edge), **Istio**
(east-west mTLS/authorization), **agentgateway** (MCP/A2A/agent model routing),
and **Envoy Gateway + Envoy AI Gateway** (KServe `LLMInferenceService`).

Two repositories: source (`Financial-Distress-Data`) owns code/tests/schemas/
Dockerfiles/evidence; GitOps (`financial-distress-gitops`) owns Terraform/
Ansible/Helm/Kustomize/Argo CD/policies.

## Deployable Units

| Plane | Deployable unit | Owner repo |
|---|---|---|
| Product | Next.js web app (`apps/web`) | source |
| Product | Admin UI (session provisioning/teardown control) | source |
| Product | Supabase (Auth + Postgres RLS) | source (migrations) |
| Product | Evidence-session worker (outbox consumer) | source |
| Evidence | EventBridge Scheduler (hard-TTL teardown trigger) | gitops |
| Evidence | CodeBuild (teardown/inventory/cost jobs) | gitops |
| Evidence | Promotion bot (source CI job; opens GitOps PRs) | source |
| Evidence | EKS cluster + node groups (Spot) | gitops |
| Evidence | Terraform modules (S3, ECR, RDS+PGVector, Valkey, Route 53, ACM) | gitops |
| Evidence | Argo CD (projects, ApplicationSets, sync waves) | gitops |
| Evidence | NGINX Ingress, cert-manager | gitops |
| Evidence | Istio service mesh | gitops |
| Evidence | Knative Serving/Eventing | gitops |
| Evidence | KServe 0.18 (`InferenceService` + `LLMInferenceService`) | gitops |
| Evidence | Kubeflow Pipelines + Kubeflow Trainer | gitops |
| Evidence | MLflow (owned Helm chart, RDS backend, S3 artifacts) | gitops |
| Evidence | Feast (offline store S3; online store Valkey / PGVector) | gitops |
| Evidence | feature-api, drift-api (FastAPI) | source → gitops image |
| Evidence | MCP servers (Feast/RAG + drift) | source → gitops image |
| Evidence | Agents (feature analyst, drift analyst, coordinator) | source → gitops image |
| Evidence | Prometheus/Grafana, ECK/Kibana, OpenTelemetry/Jaeger | gitops |
| Evidence | Vault (or equivalent secret manager) | gitops |

## Numbered Data Flows

Every node below is a deployable unit from the table above, an actor
(Analyst/Operator), or a durable artifact/process produced by one (an
immutable image digest in ECR, a GitOps PR, an outbox). Classes such as
`TrainingDataService` are implementation contracts inside a deployable unit,
never nodes themselves. Every edge is numbered in execution order.

### Flow 1 — Analyst (product plane, EKS off)

```
Analyst --(1) request--> Next.js web app --(2) RLS query--> Supabase
Supabase --(3) persisted report--> Next.js web app
Next.js web app --(4) state query--> Supabase (evidence-plane state = OFF)
Next.js web app --(5) "live AI unavailable" notice--> Analyst
```

Deployable units: Next.js web app, Supabase. The state machine is a capability
of Next.js + Supabase, not a separate server.

### Flow 2 — Training (ML)

```
Feast --(1) snapshot pull (offline store)--> Kubeflow Pipelines
Kubeflow Pipelines --(2) start job--> Kubeflow Trainer
Kubeflow Trainer --(3) distributed XGBoost run--> MLflow
MLflow --(4) register model + data versions--> MLflow (model registry)
MLflow --(5) promotion candidate--> GitOps repo PR (immutable model URI + image digest)
GitOps repo PR --(6) merge--> Argo CD --(7) sync desired state--> KServe
```

The `TrainingDataService`/`PointInTimeSplitService`/`ModelPromotionService`
contracts live inside the Kubeflow Pipelines and GitOps repo deployable units.

### Flow 3 — Inference (ML)

```
Analyst --(1) request--> NGINX --(2) TLS termination (public cert)--> Istio
Istio --(3) mTLS authorize--> feature-api --(4) feature lookup--> Feast (online store)
feature-api --(5) scored request--> KServe InferenceService --(6) prediction--> feature-api
feature-api --(7) result--> Analyst
```

KEDA/HPA autoscale the feature-api and KServe as deployable units; they are
not separate flow nodes.

### Flow 4 — Agent + RAG (LLM)

```
Analyst --(1) prompt--> agent chat UI --(2) route--> agentgateway
agentgateway --(3) route + global model config--> coordinator agent
coordinator agent --(4) delegate--> specialist agents (feature analyst, drift analyst)
specialist agents --(5) MCP tool call--> MCP Feast/RAG tool --(6) retrieval--> Feast (RAG vectors)
specialist agents --(7) MCP tool call--> MCP drift tool --(8) drift query--> drift-api
coordinator agent --(9) generation request--> Envoy AI Gateway --(10) request--> KServe LLMInferenceService (custom Qwen3-4B)
KServe LLMInferenceService --(11) generated answer--> coordinator agent
coordinator agent --(12) cited answer--> agent chat UI --(13) answer--> Analyst
```

The coordinator agent orchestrates the specialist agents (feature analyst,
drift analyst): it delegates sub-tasks and, once the specialists have gathered
evidence through the MCP tools, drives model generation through Envoy AI
Gateway. Specialist agents call the MCP tools, and the MCP tools read Feast
and drift-api — never the reverse: a tool never invokes an agent, and the
model never calls the coordinator.

### Flow 5 — Platform operator

```
Operator --(1) provision request--> admin UI --(2) enqueue--> outbox (durable artifact)
outbox --(3) action--> evidence-session worker --(4) Terraform modules plan/apply--> EKS
evidence-session worker --(5) create--> EventBridge Scheduler --(6) schedule--> CodeBuild (teardown, hard TTL 8h)
```

Cost preflight and budget guard run inside the evidence-session worker before
step 4.

### Flow 6 — CI/GitOps

```
Source CI --(1) test/build/scan/sign--> immutable image digest
Source CI --(2) push image--> ECR (immutable digest stored)
promotion bot --(3) open GitOps PR (bump image digest)--> GitOps repo
GitOps repo --(4) merge PR--> Argo CD --(5) reconcile + rollout--> evidence plane
Argo CD --(6) verification evidence--> source repo (docs/phase2/evidence)
```

### Flow 7 — Observability

```
Service --(1) emit--> OpenTelemetry collector --(2) traces--> Jaeger
OpenTelemetry collector --(3) metrics--> Prometheus --(4) visualize--> Grafana
OpenTelemetry collector --(5) logs--> ECK/Kibana
Grafana --(6) dashboards--> feature/drift/LLM/agent A/B views
```

### Flow 8 — Teardown

```
EventBridge Scheduler --(1) fire (hard TTL)--> CodeBuild --(2) destroy job--> Terraform modules
Terraform modules --(3) destroy--> EKS (resources released)
CodeBuild --(4) inventory + cost report--> evidence-session worker --(5) state OFF--> Supabase
```

## Cost Envelope

- Provisioning blocked when projected spend > USD 85 minus USD 15 reserve.
- Default TTL 6 hours; hard TTL 8 hours; ≤ 3 sessions/month.
- Target ≤ USD 25/session and ≤ USD 10/month persistent resources.
- Vast.ai CPU optional, aggregate hard cap USD 10; AWS Spot primary.

## Phase 1 Non-Mutation

Phase 2 adapters live under `src/ml/`, `src/drift/`, `src/llm/`,
`src/agents/` and never alter Phase 1 collectors, Gold writers, DQ semantics,
or local evidence behavior. Phase 1 continues to run with identical outputs.
