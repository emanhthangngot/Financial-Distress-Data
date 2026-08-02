# Phase 2 Architecture — Two Planes, One Evidence Contract

## Overview

Phase 2 uses two planes:

- **Product plane (persistent, low cost):** Next.js on Vercel Hobby +
  Supabase Auth/Postgres on Free. Always available. Shows persisted reports
  and an honest evidence-plane state machine.
- **Evidence plane (disposable, bounded budget):** EKS in `ap-southeast-1`,
  6-hour default / 8-hour hard TTL, ≤ 3 sessions/month, ≤ USD 25/session,
  ≤ USD 10/month persistent. Provisioned and destroyed through GitOps.

Four traffic layers are normative: **F5 NGINX Ingress Controller OSS**
(`nginx/kubernetes-ingress`, public TLS edge), **Istio** (east-west
mTLS/authorization), **agentgateway** (MCP/A2A/AI-backend routing), and
**Envoy Gateway + Envoy AI Gateway** (KServe `LLMInferenceService`). The
retired community `kubernetes/ingress-nginx` project is forbidden.

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
| Evidence | F5 NGINX Ingress Controller OSS, cert-manager | gitops |
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
| Local control | Airflow `dags/phase2/phase2_drift_monitoring.py` thin wrapper | source |
| External bounded | Vast.ai CPU OpenAI/llm-d Locust benchmark client | source image → GitOps Ansible role |

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
Analyst --(1) prompt--> agent chat UI --(2) authenticated route--> agentgateway
agentgateway --(3) A2A route--> kagent coordinator Agent
kagent coordinator Agent --(4) delegate through agentgateway A2A route--> kagent specialist Agents
kagent specialist Agents --(5) MCP route through agentgateway--> MCP Feast/RAG tool --(6) retrieval--> Feast (RAG vectors)
kagent specialist Agents --(7) MCP route through agentgateway--> MCP drift tool --(8) query--> drift-api
kagent coordinator Agent --(9) resolve--> kagent ModelConfig --(10) upstream/base URL--> agentgateway AI backend
agentgateway AI backend --(11) forward--> Envoy AI Gateway --(12) route--> KServe LLMInferenceService/llm-d
KServe LLMInferenceService/llm-d --(13) generated answer--> kagent coordinator Agent
kagent coordinator Agent --(14) cited answer--> agent chat UI --(15) answer--> Analyst
```

The coordinator agent orchestrates the specialist agents (feature analyst,
drift analyst): it delegates sub-tasks and, once the specialists have gathered
evidence through the MCP tools, resolves the kagent-owned global `ModelConfig`
and drives generation through its agentgateway AI backend. Neither coordinator
nor specialist calls Envoy/KServe directly. Specialist A2A and MCP calls also
traverse declared agentgateway routes; tools read Feast/drift-api, never the
reverse.

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
Argo CD --(6) launch verification job--> evidence exporter
evidence exporter --(7) immutable bundle--> S3 evidence bucket
source evidence CI/bot --(8) fetch + verify bundle--> source evidence PR
```

No in-cluster principal receives source-repository write credentials. Evidence
returns through an immutable S3 bundle and a source-side bot/CI PR.

### Flow 7 — Observability

```
Service --(1) emit--> OpenTelemetry collector --(2) traces--> Jaeger
OpenTelemetry collector --(3) metrics--> Prometheus --(4) visualize--> Grafana
OpenTelemetry collector --(5) logs--> ECK/Kibana
Grafana --(6) dashboards--> feature/drift/LLM/agent A/B views
Airflow phase2 drift DAG --(7) pull--> Feast offline store
Airflow phase2 drift DAG --(8) join reference/proxy + compute--> Evidently report
Airflow phase2 drift DAG --(9) publish--> Prometheus Pushgateway --(10) scrape--> Prometheus/Grafana
Airflow phase2 drift DAG --(11a below threshold) persist skip--> ml_metadata
Airflow phase2 drift DAG --(11b above threshold) create run--> Kubeflow Pipelines API
Kubeflow Pipelines API --(12) run ID/status--> ml_metadata
```

The evidence run executes both branch 11a and 11b. A recommendation without an
actual Kubeflow API run ID does not satisfy the retraining requirement.

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
- Vast.ai CPU worker is mandatory for Ansible evidence, aggregate hard cap USD
  10. It runs bounded OpenAI-compatible load/TTFT benchmarks against the llm-d
  public test route and never joins the
  AWS GPU KServe/llm-d inference pool; AWS Spot remains primary for inference.

## Version Compatibility Gate

Before Phase 3 installation, record exact chart versions and image digests for
EKS/Kubernetes, F5 NGINX OSS, cert-manager, Istio, Knative, KServe 0.18,
Envoy Gateway/AI Gateway, llm-d/GIE, KFP/Trainer, Argo CD, kagent, kmcp,
agentgateway, agentregistry, Agent Sandbox, Feast, and MLflow. The starting
F5 NGINX OSS candidate is controller 5.5.4 / chart 2.6.4; it becomes normative
only after the compatibility spike passes render, install, smoke, upgrade, and
rollback checks.

## Phase 1 Non-Mutation

Phase 2 adapters live under `src/ml/`, `src/drift/`, `src/llm/`,
`src/agents/` and never alter Phase 1 collectors, Gold writers, DQ semantics,
or local evidence behavior. Phase 1 continues to run with identical outputs.
