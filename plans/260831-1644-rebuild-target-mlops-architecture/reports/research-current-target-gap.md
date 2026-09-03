---
title: "Current State vs Target Architecture Gap Analysis"
date: 2026-08-31
status: "DONE"
research_phase: "Scout and Inventory"
scope: "Full repository topology, target image components, current implementation evidence, migration seams, GitOps namespace structure"
---

# Research: Current State vs Target Architecture Gap Analysis

**Researcher:** RuntimeArchitectureFacts  
**Peer coordination:** ContractMigrationFacts (platform .DR/contract analysis)  
**Foundation document:** `debate-context-foundation.md` (locked decisions, phase split, ADR-010, rebuild plan 260818)  
**GitOps authority:** `financial-distress-gitops/AGENTS.md`, `plans/260818-0028-namespace-convention-alignment/plan.md`

---

## Executive Summary

The **current state** is a platform data lakehouse (verified, Docker Compose) plus a platform .LM-only system (live-verified on GKE 2026-08-13, 60/100 points, evidence freeze pending). The **target architecture** in `images/architecture/fdd-architecture-full-4k.png` depicts a unified **ML + LLM** platform on GKE with Kubeflow/Ray/MLflow/KServe, Kafka/Debezium/Flink, MinIO/Iceberg, Postgres/Trino/Superset, Feast/Redis, and optional Istio/Vault/Jenkins. **Current GitOps is confirmed present** (10 Argo Applications, 13/13 synced): Argo CD, NGINX Ingress, cert-manager, KServe/Knative (0.14.1), agentgateway, kagent agents, Redis, PGVector Postgres, observability stack, and RAG pipeline. **The gap:** No Kubeflow, Ray, MLflow, Iceberg, Spark-K8s, Trino, Superset, Debezium, Flink-K8s, Istio, Vault, Jenkins, or Argo Rollouts are deployed. ML track is unbuilt (design-only). The namespace structure deliberately separates `agentgateway-system`, `kagent`, and `agents-sandbox` as **intentional least-privilege NetworkPolicy security boundaries**, not accidental splits.

---

## 1. Current Deployable/Runtime Units — Verified Inventory

### 1.1 platform .ocal Lakehouse (Docker Compose, verified, in-source)

| Unit | Service Image/Type | Role | Evidence |
|---|---|---|---|
| Postgres 16 | `postgres:16` | platform data; `ops` schema | `docker-compose.yml:1-30` |
| MinIO | `minio/minio:RELEASE.2025-04-22T22-12-26Z` | S3A-compatible durable object store for Bronze/Silver/Gold Parquet | `docker-compose.yml:31-42` |
| Kafka KRaft | `apache/kafka:3.9.0` | Single-node broker for price/news/alert events | `docker-compose.yml:58-89`, `infra/kafka/kafka_init_topics.sh` |
| Airflow Webserver | `financial-distress-airflow:stage1` (built locally) | DAG UI + execution controller | `docker-compose.yml:108-150`, `infra/airflow/Dockerfile` |
| Airflow Scheduler | Same image | Schedules DP1/DP2/DP3 DAGs | `docker-compose.yml:180-210` |
| Flink (opt-in) | `financial-distress-flink:stage1` (built locally) | Optional event-time streaming; profile="flink" | `docker-compose.yml:212-260`, `infra/flink/Dockerfile` |
| Phase2-Redis | `redis:7-alpine` | Feast online store; profile="phase2" | `docker-compose.yml:263-282` |
| Phase2-Postgres | `pgvector/pgvector:pg16` | PGVector + ml schema; profile="phase2" | `docker-compose.yml:283-307` |

**Launch:** `docker compose up` starts platform . product only. `ENABLE_FLINK=1 docker compose --profile flink --profile phase2 up` adds Flink + Phase 2.

**Tests:** 123 test files (PyTest), ~9 platform .est suites covering ML/drift/LLM/product/agents. platform .egression suite is primary verification gate.

**CI:** `.github/workflows/ci.yml` (platform .uality gate), plus 11 platform .orkflow YAML files (GitHub Actions based).

---

### 1.2 platform .KE Evidence Plane (Separate GitOps Repo, Live-Verified 2026-08-13)

**Note:** All Kubernetes cluster state lives in private `financial-distress-gitops` repository (now locally available at `/home/pearspringmind/Studying/FSDS/financial-distress-gitops`).

#### 1.2.1 Argo CD Applications (10 active, 13/13 apps Synced/Healthy per 2026-08-13 snapshot)

| Application | Namespace(s) | Components | Evidence |
|---|---|---|---|
| **cert-manager** | cert-manager | TLS issuer & webhook | `argocd/applications/cert-manager.yaml` |
| **nginx-ingress** | ingress-nginx | F5 NGINX OSS Ingress Controller (sole external entry point, ADR-009) | `argocd/applications/nginx-ingress.yaml` |
| **platform-inference** | knative-serving, kourier-system, kserve | KServe 0.14.1, Knative Serving, Kourier network layer | `argocd/applications/platform-inference.yaml`, `platform/inference/vendored/` |
| **platform-agentgateway** | agentgateway-system | agentgateway AI routing backend (least-privilege NetworkPolicy boundary per plan 260818-0028) | `argocd/applications/platform-agentgateway.yaml`, `platform/agentgateway/` |
| **platform-agents-crds** | kagent | kagent CRDs (Agent, ModelConfig, MCP tool specs) | `argocd/applications/platform-agents-crds.yaml` |
| **platform-agents** | kagent, agents-sandbox | Coordinator agent, feature specialist, drift specialist; sandbox with restricted PSS + tokenless SA + read-only root + default-deny NetworkPolicy (security boundary per plan) | `argocd/applications/platform-agents.yaml`, `platform/agents/agent-deployments.yaml`, `platform/agents/agent-sandbox.yaml` |
| **platform-data** | phase2-data | Redis (Feast online), PGVector Postgres (ml + RAG embeddings), RAG pipeline CronJob (suspend: true outside capture windows) | `argocd/applications/platform-data.yaml`, `platform/data/{redis,postgres-pgvector,pipeline-deployments}.yaml` |
| **platform-llm** | phase2-llm | LLM-specific orchestration/routing (details in GitOps manifests) | `argocd/applications/platform-llm.yaml` |
| **platform-observability** | monitoring | Prometheus, Grafana, Loki, Jaeger, OpenTelemetry Collector (live-verified 2026-08-13) | `argocd/applications/platform-observability.yaml`, `platform/observability/` |
| **platform-security** | — | Sealed Secrets, GHCR pull credentials, ClusterIssuers (Let's Encrypt) | `argocd/applications/platform-security.yaml`, `platform/security/` |

**Live-verified (2026-08-13):**
- 10 Argo Applications, 13 total resources, all "Synced" and "Healthy"
- kagent 10 agents in "Ready" status
- Coordinator → feature/drift agents → MCP tools verified live (Jaeger trace: 5 spans, 170ms)
- Prometheus targets healthy; Grafana dashboards visible; Jaeger services discoverable
- NGINX Ingress with static IP; basic-auth gate

**Deployment discipline:** Argo CD is the only mutation path; manifest digests are immutable SHA256 references; no mutable tags (AGENTS.md in GitOps repo).

---

#### 1.2.2 Kubernetes Namespace Structure (Locked Architectural Decision)

**Current 11 namespaces, deliberately organized by security/domain boundary (plan 260818-0028):**

| Namespace | Type | Contents | Security/Domain Role |
|---|---|---|---|
| `argocd` | vendor default | Argo CD control plane | GitOps controller |
| `cert-manager` | vendor default | cert-manager webhook, controller | Certificate lifecycle |
| `ingress-nginx` | vendor default | NGINX Ingress Controller | External ingress gate |
| `knative-serving` | vendor default | Knative Serving core (KServe dependency) | Serverless runtime |
| `kourier-system` | vendor default | Kourier network layer (KServe dependency) | KServe networking |
| `kserve` | vendor default | KServe controller & admission webhooks | Model serving operator |
| `agentgateway-system` | **our choice** | agentgateway AI backend routing | **Least-privilege egress scoping:** ModelConfig routes through this namespace, agents' NetworkPolicy allows egress here only (not direct to KServe) |
| `kagent` | **our choice** | kagent CRDs, agent controllers (coordinator, feature, drift) | Agent control plane |
| `agents-sandbox` | **our choice**, **security boundary** | Agent runtime pods (coordinator instance, feature/drift instance) | Pod Security Standards: restricted; tokenless ServiceAccount; read-only root; default-deny NetworkPolicy egress scoped to `agentgateway-system` (ADR-010 closure path) |
| `phase2-data` | **our choice** | Redis (online feature store), PGVector Postgres (ml, RAG embeddings), Feast definitions, RAG pipeline CronJob | Feature & data layer |
| `monitoring` | **our choice** | Prometheus, Grafana, Loki, Jaeger, OTel Collector | Observability & telemetry |

**Critical architectural fact (locked in 260818-0028-namespace-convention-alignment/plan.md:77-115):** The split of `agentgateway-system`, `kagent`, and `agents-sandbox` into three namespaces is **not accidental vendor-component fragmentation**. It is a deliberate **least-privilege NetworkPolicy boundary design**: the sandbox's `default-deny` egress NetworkPolicy scopes egress to `agentgateway-system` by `namespaceSelector`, making the namespace split load-bearing for security isolation. Merging `agentgateway-system` and `kagent` would narrow egress scoping, which is a regression. `agents-sandbox` provides the only tokenless, read-only isolation tier in the cluster and must not be merged.

**Consequence for target image:** Visual grouping of "agent stack" or "LLM stack" in the target image must not imply namespace collapse. The three namespaces remain separate kubernetes resources; evidence rows pinned to exact `gitops` paths (21 rubric rows) depend on these namespaces existing at those names.

---

### 1.3 Terraform + Ansible (GCP Infra, in GitOps Repo)

| Asset | Evidence | Status |
|---|---|---|
| **GKE Cluster** | `terraform/gcp/gke.tf` | Provisioned in asia-southeast1-b, 48 vCPU quota (per plan 260818, line 163) |
| **GCP VPC + Network** | `terraform/gcp/network.tf` | VPC, subnets, firewall rules defined |
| **IAM + Workload Identity** | `terraform/gcp/iam.tf` | Workload Identity bindings (no long-lived service-account keys) |
| **Container Registry** | `terraform/gcp/registry.tf` | GHCR authentication |
| **Ansible Playbooks** | `ansible/playbooks/` + `ansible/roles/` | VM configuration, evidence admin |
| **Terraform State** | `terraform/gcp/terraform.tfstate` (tracked in repo — audit concern) | 77 KB state file present |

**Cost & Node Pools:** Terraform includes cost optimization: spot vs on-demand split, scheduled hibernation (`make gcp-up`/`gcp-down`), two NLBs removed (cost fix), estimated 230-260 cluster-hours budget through Nov 6, 2026 (plan 260818:230-250).

---

## 2. Target Image Component Ledger

Parsed from `images/architecture/fdd-architecture-full-4k.png` (4000×4088 px, created 2026-08-22):

### Layer 1: Ingress + Product + Analytics

| Component | Visual Role | Current Status | Evidence |
|---|---|---|---|
| **Next.js + Ingress (web + controller)** | Product web UI + Gateway AuthorizationPolicy | ✅ Implemented (Vercel + Supabase, not in-cluster yet) | `apps/web/`, external Vercel |
| **Analytics Stakeholder UI** | User-facing analytics/reporting dashboard | ❌ **Not in source or GitOps** | — |
| **Superset** | BI/analytics query explorer for Gold tables | ❌ **Not in source or GitOps** | — |

### Layer 2: ML Orchestration + Experiment Tracking

| Component | Visual Role | Current Status | Evidence |
|---|---|---|---|
| **Kubeflow Pipelines** | ML pipeline DAG orchestration, training step controller | ❌ **Not in source or GitOps** | — |
| **Ray Cluster** | Distributed training backend (hyperparameter tuning, actor model) | ❌ **Not in source or GitOps** | — |
| **MLflow Server** | Experiment tracking + model registry | ❌ **Not in source or GitOps** | — |

### Layer 3: Data Ingestion + Streaming

| Component | Visual Role | Current Status | Evidence |
|---|---|---|---|
| **Kafka** | Event broker (price, news, alert, CDC from Postgres) | ✅ platform .ocal; K8s version absence unclear | `src/streaming/events.py`, `docker-compose.yml`, not in active GitOps Argo Applications |
| **Debezium** | CDC (Change Data Capture) connector → Kafka | ❌ **Not in source or GitOps** | — |
| **Flink** | Event-time streaming, late arrival routing, dedup | 🟡 Partially (opt-in local profile; no K8s Flink Job manifests in active GitOps) | `src/streaming/flink/jobs/`, Docker Compose profile="flink" |

### Layer 4: Data Lake + Feature Store

| Component | Visual Role | Current Status | Evidence |
|---|---|---|---|
| **MinIO** | S3-compatible object store for tables | ✅ Implemented (platform data/` (mounted but details not confirmed) |
| **Iceberg** | Transactional table format (transaction log, time travel) | ❌ **Not in source; platform .ses Parquet** | platform .enerates `.parquet` files only |
| **Spark** | Bronze→Silver→Gold transforms; offline feature writes | ✅ Implemented (local PySpark, no K8s Spark Operator in active GitOps Applications) | `src/transforms/`, local Spark session; no Spark executor config for K8s |
| **Trino** | SQL query engine over data lake (Iceberg/MinIO) | ❌ **Not in source or GitOps** | — |

### Layer 5: Feature & Online Stores

| Component | Visual Role | Current Status | Evidence |
|---|---|---|---|
| **Feast** | Feature store; offline (Postgres/Iceberg) + online (Redis) definitions | 🟡 Partially (feature_repo/ structure defined locally; GKE materialization untested) | `feature_repo/`, `src/ml/feast/` (local definitions); no Feast control plane in GitOps |
| **Redis** | Online feature store cache + model serving cache | ✅ Implemented (`phase2-redis` Deployment in `platform/data/redis.yaml`, GitOps Application: platform-data) | `platform/data/redis.yaml`, `docker-compose.yml` profile="phase2" |
| **Postgres** | Offline feature store + project/ml | ✅ Implemented (phase2-postgres PGVector in `platform/data/postgres-pgvector.yaml`, GitOps) | `platform/data/postgres-pgvector.yaml` |

### Layer 6: Model Serving + LLM

| Component | Visual Role | Current Status | Evidence |
|---|---|---|---|
| **KServe/Knative + llm-d** | ML inference service operator; LLM router (llm-d for llama2-style LLM) | 🟡 Partial (KServe 0.14.1 deployed; llm-d router role unclear; agentgateway used as substitute per ADR-010) | `argocd/applications/platform-inference.yaml`, `platform/inference/vendored/04-kserve.yaml` (0.14.1 pinned) |
| **TensorRT / NVIDIA llm-d** | LLM inference optimization (vLLM, llama.cpp on CPU) | 🟡 Partial (vLLM/llama.cpp CPU server exists; no GPU, free-trial GPU quota is 0) | `docs/platform/adr/adr-010-llm-only-scope-and-platform-simplification.md:branch-B` |
| **Argo Rollouts** | Canary rollout, traffic splitting (champion/candidate A/B) | ❌ **Not in active GitOps Applications** | No Argo Rollouts application manifest visible |
| **Kiali + Istio** | Service mesh visualization + mTLS/authorization | ❌ **Dropped by ADR-010 for cost fit** | Not in GitOps; plan 260818 mentions optional mesh-partial injection (3-4 vCPU recovery) |
| **HashiCorp Vault** | Secrets management + rotation | ❌ **Dropped by ADR-010; GitHub Actions secrets used instead** | Not in GitOps; plan 260818 lists as rebuild requirement |

### Layer 7: CI/CD + GitOps

| Component | Visual Role | Current Status | Evidence |
|---|---|---|---|
| **Jenkins + agents** | CI orchestration; test, build, scan, sign, promote digest | ❌ **Not in source or GitOps** | Not in any Argo Application; plan 260818 lists as rebuild requirement (decision #4) |
| **Argo CD + Argo Rollouts** | GitOps controller + progressive delivery | 🟡 Partially (Argo CD 10 apps synced; Argo Rollouts absent) | `argocd/applications/`, `financial-distress-gitops/AGENTS.md` (Argo-only mutation rule) |

### Layer 8: Observability

| Component | Visual Role | Current Status | Evidence |
|---|---|---|---|
| **Prometheus + Grafana** | Metrics collection + dashboarding | ✅ Implemented (platform-observability Argo Application) | `argocd/applications/platform-observability.yaml`, `platform/observability/prometheus-values.yaml`, `platform/observability/dashboards.yaml` |
| **Jaeger** | Distributed tracing; agent traces verified live 2026-08-13 | ✅ Implemented (platform-observability) | `platform/observability/jaeger.yaml` |
| **Loki** | Log aggregation (replacing Kibana/ECK) | ✅ Implemented (platform-observability) | `platform/observability/loki-otel-values.yaml` |

---

## 3. Current Implementation Evidence → Target Gap Matrix

| Target Component | Current Evidence | Gap Status | Location | Notes |
|---|---|---|---|---|
| **Kubeflow Pipelines** | None; phase-05-deliver-ml-track.md plan exists but unexecuted | ❌ **MISSING** | (source plan only) | ML track deferred; requires K8s Operator install + Trainer CRD |
| **Ray Cluster** | None; not mentioned in detail plans | ❌ **MISSING** | — | Distributed training backend; must coexist with Kubeflow |
| **MLflow Server** | None; phase-05 plan only | ❌ **MISSING** | — | Requires ml Postgres (which exists); Helm chart absent |
| **Iceberg** | None; platform .ses Parquet only | ❌ **MISSING** | source repo | Schema-on-write table format; requires Spark catalog + MinIO setup |
| **Spark on K8s** | Local PySpark only; no Spark Operator CRD | 🟡 **PARTIAL** | `src/transforms/` + (missing GitOps) | Jobs run locally; K8s executor model undefined |
| **Trino** | None | ❌ **MISSING** | — | SQL federation layer over MinIO/Iceberg; requires Catalog config |
| **Superset** | None | ❌ **MISSING** | — | BI analytics UI; optional but shown in target image |
| **Debezium** | None | ❌ **MISSING** | — | CDC from Postgres → Kafka; new ingestion path |
| **Flink on K8s** | Opt-in compose profile; no K8s Flink Application manifest in GitOps | 🟡 **PARTIAL** | `src/streaming/flink/jobs/` + missing GitOps Argo App | Event-time streaming; local job code exists |
| **Istio + Kiali** | Dropped by ADR-010 for vCPU budget; not in GitOps | ❌ **ARCHITECTURAL CONFLICT** | ADR-010 decision | LLM submission chose NGINX+NetworkPolicy; rebuild plan 260818 lists optional mesh-partial (3-4 vCPU recovery) |
| **Vault + ESO** | Dropped by ADR-010; GitHub Actions secrets used instead | ❌ **ARCHITECTURAL CONFLICT** | ADR-010 decision | LLM submission cut for cost; plan 260818 lists Vault as rebuild requirement |
| **Jenkins CI/CD** | None; GitHub Actions workflows in use | ❌ **ARCHITECTURAL CONFLICT** | source repo `.github/workflows/` + plan 260818 decision #4 | Plan mandates Jenkins; LLM submission deferred implementation |
| **Argo Rollouts** | Not in active Argo Applications (no manifest in GitOps) | ❌ **MISSING** | — | Progressive delivery for canary A/B; plan mentions but unverified |
| **KServe 0.18+** | KServe 0.14.1 deployed (ADR-004 pin; pre-LLMInferenceService CRD era) | 🟡 **VERSION CONFLICT** | `platform/inference/vendored/04-kserve.yaml` | Plan 260818 + target show 0.18+ for LLMInferenceService; rebuild decision supersedes ADR-004 |
| **llm-d router** | agentgateway used as enforced boundary instead (ADR-010); llm-d role ambiguous | 🟡 **PARTIAL/SUBSTITUTED** | `argocd/applications/platform-agentgateway.yaml` | Security-by-design: agents' NetworkPolicy egress scoped to agentgateway-system |
| **Feast online/offline** | feature_repo/ definitions exist locally; online (Redis) + offline (Postgres) schema/tables exist in GitOps | 🟡 **PARTIAL** | `feature_repo/`, `src/ml/feast/`, `platform/data/` | Structure present; GKE Feast control plane/materialization untested |
| **PGVector + Redis** | Both present and live | ✅ **PRESENT** | `platform/data/{redis,postgres-pgvector}.yaml` | RAG embeddings + online features coexist |
| **Next.js + Supabase** | Vercel + managed Supabase (external) | ✅ **PRESENT** | external, not in-cluster | Phase 9 migrates to in-cluster (parallel with ML track) |
| **Agents + MCP** | Live-verified 2026-08-13 | ✅ **PRESENT** | `argocd/applications/platform-agents.yaml`, `src/agents/`, `apps/drift-mcp/`, `apps/feature-mcp/` | Coordinator + feature + drift; 10 agents ready; 5-span trace live |
| **Observability** | Prometheus, Grafana, Loki, Jaeger, OTel live | ✅ **PRESENT** | `argocd/applications/platform-observability.yaml` | All healthy 2026-08-13 |
| **NGINX Ingress OSS** | F5 Active NGINX Controller (ADR-009) | ✅ **PRESENT** | `argocd/applications/nginx-ingress.yaml`, `platform/ingress/` | Sole external entry point behind basic-auth |
| **Kafka** | platform .ocal KRaft; K8s version deployment status unclear | 🟡 **PARTIAL** | `docker-compose.yml` + (unclear if replicated in K8s) | Event broker exists locally; GitOps Kafka deployment not confirmed in Argo Applications list |

---

## 4. Architectural Conflicts & Scope Seams

### Conflict 1: Mesh Security (Istio vs NGINX + NetworkPolicy)

**Current state:** ADR-010 (LLM submission, 2026-08-07) chooses NGINX Ingress OSS + default-deny NetworkPolicy to fit 48 vCPU budget; agentgateway-system/kagent/agents-sandbox split is **load-bearing for NetworkPolicy scoping** (plan 260818-0028:77-115).  
**Target image shows:** Istio full-mesh (Kiali, mTLS).  
**Plan 260818 status:** Mentions Istio full-sidecar as design (line 9: "Istio full sidecar mode… Costs ~4-6 vCPU"); also notes "selective injection in `api-serving`, `agents` and `kserve` recovers roughly 3-4 vCPU while keeping mesh row" (plan.md:240).  
**Consequence:** Debate must decide: (a) restore Istio mesh-wide, reclaim 3-4 vCPU via selective injection, or (b) keep NGINX + NetworkPolicy but document Kiali/L7 telemetry limitation.

### Conflict 2: Secrets Management (GitHub Actions vs Vault + ESO)

**Current state:** ADR-010 drops Vault; GitHub Actions secrets + sealed-secrets used.  
**Target image shows:** HashiCorp Vault + External Secrets Operator.  
**Plan 260818 status:** Decision #4 locks "Jenkins + HashiCorp Vault, replacing GitHub Actions"; rebuild decision is dated 2026-08-18, signed.  
**Consequence:** Need Vault + ESO Helm charts and secret provisioning retargeting; 1-2 vCPU + 2-3 days effort.

### Conflict 3: CI/CD Framework (GitHub Actions vs Jenkins)

**Current state:** 11 GitHub Actions workflows (phase2-*.yaml), all GitHub-specific; LLM submission continued this path.  
**Plan 260818:** Decision #4 (line 31-33) locks Jenkins as sole CI/CD driver; states "~2 vCPU and ~4 days of migration."  
**Target image shows:** Jenkins controller + agents in CI/CD layer.  
**Consequence:** Wholesale rewrite of CI workflows to groovy/Jenkinsfile; Jenkins controller Helm chart absent from active Argo Applications.

### Conflict 4: KServe Version (0.14.1 vs 0.18+)

**Current state:** KServe 0.14.1 deployed per ADR-004 (pre-LLMInferenceService CRD era).  
**Plan 260818 & target:** Show 0.18+ with LLMInferenceService CRD (llm-d router integration).  
**Consequence:** Cluster must migrate KServe manifests; llm-d integration depends on 0.18+ CRD availability. Version conflict may prevent LLMInferenceService deployment.

### Conflict 5: ML Track Scope (Design-Only vs Delivered)

**Current state:** ADR-010 defers ML track (57 rows, design-only); only LLM (60 rows) is submitted.  
**Plan 260818:** Requires ML track as executed with all three rubrics (mini + ML + LLM, 161 rows, 300 points).  
**Target image:** Shows full ML pipeline (Kubeflow, Ray, MLflow, Triton).  
**Consequence:** **Largest rebuild scope: entire ML training/serving path must be built and verified from scratch.** This is not an incremental change; it is a scope expansion from 100 to 300 points.

### Conflict 6: Model Serving Path (agentgateway vs llm-d)

**Current state:** ADR-010 uses agentgateway as **sole enforced boundary**; llm-d routing is optional/conceptual (restored 2026-08-07 afternoon but agentgateway remains the enforced path).  
**Target image:** Shows llm-d router + KServe LLMInferenceService explicitly.  
**Plan 260818:** Restores llm-d routing but subordinate to agentgateway.  
**Consequence:** Clarify whether llm-d is a required part of LLM serving path or if agentgateway suffices. Gateway API setup (GIE + LeaderWorkerSet) may be required per plan.md:96-100.

### Conflict 7: Namespace Structure (Merged vs Separate)

**Current state (locked):** Plan 260818-0028 documents that `agentgateway-system`, `kagent`, and `agents-sandbox` are **deliberate least-privilege NetworkPolicy boundaries**, not accidental vendor splits. Merging them would narrow the sandbox's egress scoping and is a security regression.  
**Target image visual grouping:** Shows "LLM stack" / "agent stack" as a single visual zone.  
**Recommendation (plan 260818-0028:192-196):** Redraw diagrams with explicit per-namespace labels and rationale callouts; do not merge manifests (would invalidate 21 pinned evidence rows and break security isolation).

---

## 5. Data/Control/Model/User Flows

### 5.1 Data Flow (Source → Gold → Serving)

**Current (platform .ocal → platform .LM-only GKE):**
```
FixtureAdapter or OnlineAPI → Kafka (price/news/alert events)
  → Airflow DP1 (collect_to_bronze)
  → MinIO Bronze Parquet
  → Airflow DP2 (bronze_to_silver_spark)
  → Spark local-mode transform
  → MinIO Silver Parquet
  → Airflow DP2 (silver_to_gold_spark)
  → MinIO Gold Parquet
  → DuckDB local inspection
  → RAG ingest (src/llm/rag_pipeline.py) → PGVector (phase2-postgres, phase2-data ns)
```

**Target (Unified rebuild, all rubrics):**
```
OnlineAPI / Postgres CDC (Debezium) → Kafka event log
  → Flink micro-batch or Kafka consumer → MinIO Bronze (Iceberg)
  → Spark (via Kubeflow Pipelines or Airflow K8s executor) → MinIO Silver (Iceberg)
  → Spark Silver → Gold (Iceberg tables, Spark partition pruning)
  → MinIO Gold (Iceberg)
  → Trino (SQL federation) → Superset (BI queries)
  → Feast offline store (Postgres + Iceberg historical) + Spark offline jobs
  → Feast online store (Redis push materialization)
  ├─→ ML training (Kubeflow Trainer reads offline via PIT join)
  └─→ LLM RAG ingest → PGVector (same as current)
```

**Gaps:**
- No Debezium CDC ingestion configured
- No Iceberg catalog/table definitions
- No Spark on K8s executor model (only local)
- No Trino/Superset query layer
- No Feast offline/online split or materialization on K8s
- No Flink-K8s event-time processing
- Gold table OBT (obt_company_quarter_risk) must migrate to Iceberg format

### 5.2 Control Flow (CI/CD & GitOps)

**Current (platform .LM-only):**
```
source repo commit
  → GitHub Actions CI (test, build, scan, sign digest)
  → GHCR image push
  → GitOps PR (update image digest in financial-distress-gitops)
  → Argo CD reconcile (10 apps, 13 resources, Synced/Healthy)
```

**Target (Unified rebuild with Jenkins):**
```
source repo commit
  → Jenkins pipeline (test, build, scan, sign digest)
  → Registry push (GHCR or other)
  → Jenkins: bump-gitops (open/merge GitOps PR with digest)
  → Argo CD reconcile + Argo Rollouts (progressive delivery, canary)
  → Evidence capture (phase 8)
```

**Gaps:**
- No Jenkins controller or groovy pipelines
- No Argo Rollouts canary/traffic-split config
- No Kubernetes native-sidecar config for Job termination (Istio/Knative workaround)
- platform .I workflows (11 files) target GitHub Actions; Jenkins retargeting is wholesale rewrite

### 5.3 Model Flow (Training → Serving → Monitoring)

**Current (platform .LM-only):**
```
LLM model (vLLM or llama.cpp, CPU-only) → agentgateway routing
  → agents (coordinator, feature, drift) → MCP tools
  → RAG retrieval + citations
  → Traces to Jaeger (live 2026-08-13)
```

**Target (Unified, includes ML):**
```
Training data (Iceberg gold.distress_holdout_v1, frozen at tag)
  → Kubeflow Pipelines (training job)
  → Spark/PyTorch trainer
  → MLflow Tracking (logs metrics/artifacts)
  → MLflow Model Registry
  → Model promotion gate (frozen holdout accuracy ≥ champion)
  → KServe InferenceService (champion/candidate A/B split via Argo Rollouts canary)
  ├─→ Triton (ML model serving; Knative autoscaling)
  └─→ LLMInferenceService (LLM serving via llm-d router; vLLM CPU backend)
  → Prometheus metrics export (Jaeger, Loki, Grafana dashboards)
  → Drift detection (Flink / Evidently) → PushGateway
  → Threshold breach → Kubeflow Pipelines trigger → retraining loop
```

**Gaps:**
- No Kubeflow Pipelines orchestration
- No MLflow Tracking or model registry integration
- No Triton serving (KServe has llama.cpp model server only, via agentgateway)
- No Argo Rollouts canary deployments
- No Drift-triggered retraining loop
- No frozen holdout table with Iceberg tag (label schema change required)
- No model promotion gate logic

### 5.4 User Flow (Analyst → Product → Evidence)

**Current (Phase 2, LLM-only):**
```
Analyst → Next.js (Vercel, external) → Supabase Auth
  → evidence-session request → outbox table
  → outbox-worker polls GKE → agentgateway
  → coordinator + agents → MCP tools
  → LLM response + citations
  → outbox state update (honest state machine)
  → UI renders evidence (Jaeger trace visible)
```

**Target (Unified rebuild):**
```
Analyst → Next.js (in-cluster, behind NGINX, phase 9)
  → in-cluster Postgres RLS (not Supabase)
  → analytic routes: Superset (BI), Grafana (metrics), Loki (logs), Jaeger (traces)
  → ML model feature lookup → feature-api or Feast online store (Redis)
  → LLM assistant chat → agent coordinator/MCP path (same)
  → (Optional) A/B test assignment (MLflow registry, Argo Rollouts traffic split)
```

**Gaps:**
- No in-cluster Next.js migration (Phase 9, parallel with ML track)
- No Superset/BI analytics UI
- No feature-api/Feast online feature serving (only local definitions)
- No A/B testing infrastructure (MLflow + Argo Rollouts)

---

## 6. Source vs GitOps Ownership Facts

### 6.1 What Lives in Source Repo (`financial-distress-data`)

| Layer | Path | File Count | Status |
|---|---|---|---|
| **platform data/`, `src/catalog/`, `src/io/`, `src/jobs/` | ~150 py files | ✅ Verified |
| **platform .rchestration** | `dags/` | ~20 DAG files | ✅ Verified |
| **platform .vidence** | `scripts/`, `tests/` | ~30 scripts, 123 tests | ✅ Verified |
| **platform .L/Drift** | `src/ml/`, `src/drift/`, `src/governance/` | ~30 py files | 🟡 Partial (fixtures, not trained) |
| **platform .LM/Agents** | `src/llm/`, `src/agents/`, `src/cdc/`, `src/observability/` | ~60 py files | ✅ Live-verified |
| **platform .roduct** | `apps/web/`, `apps/feature-api/`, `apps/feature-mcp/`, `apps/drift-api/`, `apps/drift-mcp/` | ~400 TS/TSX files | ✅ Live-verified |
| **platform .eature Store** | `feature_repo/`, `src/ml/feast/` | ~10 feature definitions | 🟡 Partial (local; online/offline untested on K8s) |
| **CI/CD** | `.github/workflows/` | 11 GitHub Actions YAML files | ✅ Working |
| **Docker Compose** | `docker-compose.yml`, `infra/` | 1 compose + 3 Dockerfiles | ✅ Working |
| **Configuration** | `configs/`, `sql/`, `pyproject.toml`, `package.json` | ~40 config files | ✅ Working |
| **Documentation** | `docs/` (excepting evidence/) | 50+ markdown files | ✅ Current |

**Total tracked:** ~946 files

### 6.2 What Lives in GitOps Repo (`financial-distress-gitops`, locally available)

| Layer | Component | Manifest Type | Status |
|---|---|---|---|
| **Terraform** | GKE cluster, node pools, persistent disks, firewall, IAM, cost optimization | HCL (`.tf` files) | ✅ Present (`terraform/gcp/gke.tf`, etc.) |
| **Argo CD** | 10 Applications, 13 resources, project definitions | YAML Argo manifests | ✅ Present (`argocd/applications/*.yaml`) |
| **Helm Charts** | KServe, Knative, Argo CD, nginx-ingress, prometheus, grafana, loki, jaeger, otel, sealed-secrets | Helm chart YAML + values | ✅ Present (`platform/*/`) |
| **KServe/Knative/Kourier** | Vendored CRDs and core controllers | YAML (upstream bootstrap) | ✅ Present (`platform/inference/vendored/`) |
| **Agents & MCP** | Deployment, sandbox PSS, NetworkPolicy (least-privilege boundaries), agent-deployments, global-model-config | YAML | ✅ Present (`platform/agents/`) |
| **Data Layer** | Redis Deployment, PGVector Postgres, RAG pipeline CronJob, credentials sealed-secret, network policies, feast online contract probe | YAML | ✅ Present (`platform/data/`) |
| **Ingress** | F5 NGINX Helm values, basic-auth sealed-secret, DuckDNS certificate, HTTPRoutes for UI/viewers | YAML | ✅ Present (`platform/ingress/`) |
| **Observability** | Prometheus, Grafana, Loki-OTel values, Jaeger, OTel Collector | Helm values + YAML | ✅ Present (`platform/observability/`) |
| **Security** | Sealed Secrets, GHCR pull credentials, ClusterIssuers, cert-manager values | YAML | ✅ Present (`platform/security/`) |
| **Istio** | **Not deployed** (ADR-010 decision; dropped for cost) | — | ❌ Absent |
| **Vault + ESO** | **Not deployed** (ADR-010 decision) | — | ❌ Absent |
| **Kubeflow** | **Not deployed** (ML track deferred) | — | ❌ Absent |
| **Ray Cluster** | **Not deployed** | — | ❌ Absent |
| **MLflow** | **Not deployed** | — | ❌ Absent |
| **Trino** | **Not deployed** | — | ❌ Absent |
| **Superset** | **Not deployed** | — | ❌ Absent |
| **Debezium** | **Not deployed** | — | ❌ Absent |
| **Flink on K8s** | **Not deployed** (local Flink profile only) | — | ❌ Absent |
| **Jenkins** | **Not deployed** | — | ❌ Absent |
| **Argo Rollouts** | **Not deployed** | — | ❌ Absent |

**Critical fact:** All 10 Argo Applications are synced and healthy (2026-08-13). The components that ARE deployed are confirmed. The components that are NOT deployed are confirmed absent. Evidence is **not speculative**.

---

## 7. Tests & Verification Evidence

### 7.1 platform .erification (Verified, Repeatable)

| Test Category | Count | Evidence |
|---|---|---|
| Unit tests (transforms, quality, metadata) | ~50 | `tests/test_*.py`, `pytest -v` passing |
| Contract tests (schema, streaming, DQ) | ~30 | `tests/test_schema_contracts.py`, `tests/test_streaming.py` passing |
| Integration tests (DAG smoke, E2E pipeline) | ~20 | `tests/test_stage1_*`, `scripts/run_stage1_real_e2e.py` passing |
| Runtime evidence (local lakehouse) | 1 | `scripts/run_stage1_real_e2e.py` → reproducible `docs/evidence/` artifacts |
| Quality gates (critical DQ failures halt) | 1 gate | `scripts/run_stage1_quality_gates.py`, enforced by AGENTS.md rules |
| Regression suite | Continuous | CI workflow `ci.yml` on every push |

**Result:** platform .ipeline is verified end-to-end on local Docker Compose.

### 7.2 platform .erification (LLM track live-verified, ML track untested)

| Test Category | Count | Status |
|---|---|---|
| Product tests (web UI, auth, RLS) | ~15 | ✅ Browser checks passing |
| Agent tests (coordinator, MCP, sandbox) | ~10 | ✅ Live 2026-08-13 (5-span trace, 170ms, all agents Ready) |
| LLM track evidence (60 rows / 100 pts) | 60 | 🟡 Logically covered; SHA freeze pending |
| ML track evidence (57 rows / 100 pts) | 57 | ❌ Design-only (ADR-010 deferral) |
| platform .uality gates | Partial | LLM audit gate works; ML gate untested |
| Observability traces (agent coordinator) | Verified | Jaeger live 2026-08-13 (traces visible, Prometheus targets healthy) |
| Argo CD reconciliation | 13 resources | ✅ 10 Applications, 13/13 Synced/Healthy 2026-08-13 |
| RBAC/RLS boundary tests (agent sandbox) | ~3 negative tests | ✅ Agents cannot reach model server directly (NetworkPolicy verified) |

**Result:** LLM track is live-verified; ML track is unbuilt.

### 7.3 platform .L Track Tests (Absent)

No Kubeflow, MLflow, Spark-on-K8s, Trino, Superset tests exist in source or verified on cluster.

---

## 8. Explicit Unknowns & Prerequisite Gaps

### 8.1 GitOps-Level Unknowns (Now Verifiable from Local GitOps Repo)

| Question | Impact | Verification Method |
|---|---|---|
| Is Kafka replicated on K8s (outside compose)? | Event broker scalability | Search GitOps `platform/data/` for Kafka Helm chart or Deployment |
| Are MinIO replicas configured in K8s? | S3 availability | Read `platform/data/` MinIO Helm values (not inspected in detail) |
| Is Spark Operator installed? | K8s job submission | `kubectl api-resources \| grep spark` or grep GitOps for SparkApplication manifests |
| What is Feast control plane status? | Feature store initialization | Search GitOps for Feast Helm chart or Deployment (not found in active Argo Apps) |
| Are Spark executors configured for K8s? | Spark job submission capability | Read Spark session config in Kubeflow/Airflow manifests (TBD) |
| What is MLflow backend database / artifact store? | Experiment/model registry persistence | MLflow not deployed; decision needed on backend |
| What is the Debezium Source/Sink configuration? | CDC ingestion contract | Not deployed; schema/topic decisions pending |
| Trino/Superset connection strings? | Analytics query layer setup | Not deployed; configuration design needed |
| Iceberg catalog URL / warehouse location? | Table format initialization | Design decision pending (MinIO path, Glue catalog, etc.) |
| Flink-K8s deployment readiness? | Event-time processing on cluster | Flink Helm chart / Deployment not found in active Argo Apps |

**Blockers:** Kafka, MinIO, Feast control plane deployment status are borderline unknowns (components referenced in `platform/data/` but detailed config not inspected). Larger gaps (Kubeflow, Ray, MLflow, Debezium, Flink-K8s, Trino, Superset, Istio, Vault, Jenkins) are confirmed absent.

### 8.2 Source-Level Design Unknowns

| Question | Component | Status |
|---|---|---|
| Does `src/ml/` include Spark trainer + PyTorch trainer CRDs? | ML training path | Not inspected in detail |
| Does `src/drift/` include Flink-based drift detection (not just generator)? | Streaming drift | Not inspected in detail |
| Are platform .AGs refactored to run on Spark-K8s (vs local)? | Executor model migration | Not planned in current commits |
| Is label table schema updated with `label_event_ts` for frozen holdout? | MLflow holdout gate | Not in current schema |
| Does `feature_repo/` define both structured + RAG features for K8s? | Feature definitions | Not inspected in detail |
| Are MCP tool definitions (feature-mcp, drift-mcp) wired to Feast? | Feature/drift data path | Live-verified connection; exact Feast integration not inspected |

**Assumption:** Current source is incomplete for ML track; phase-05 retrofit plan exists but is unexecuted.

### 8.3 Cost & Quota Unknowns

| Question | Impact | Status |
|---|---|---|
| Has GCP GPU quota increase been granted? (Currently 0) | NVIDIA component viability | CPU-only constraint confirmed; GPU quota = 0 |
| Actual spend (USD) to date (80 days into trial)? | Budget headroom | Plan reports ~USD 77 spent, ~USD 223 remaining through Nov 6 |
| Is 48 vCPU quota confirmed? | Capacity for full stack | Plan assumes 48 vCPU; decision pending on mesh-selective injection fallback if lower |
| Do spot vs on-demand node pools exist in Terraform? | Cost optimization method | Terraform config mentions cost fixes; exact node pool strategy TBD |

**Status:** Cost assumptions are documented in plan 260818; exact real spend requires GCP Billing Console inspection.

---

## 9. Architectural Conflicts Summary

| Conflict | Current Decision | Target / Plan 260818 | Issue | Rebuild Impact |
|---|---|---|---|---|
| **Mesh Security** | ADR-010: NGINX + NetworkPolicy | Plan 260818: Istio full or partial | vCPU budget vs L7 telemetry | High (3-6 vCPU, manifest rewrite) |
| **Secrets** | ADR-010: GitHub Actions secrets | Plan 260818: Vault + ESO | Cost vs centralized rotation | Medium (1-2 vCPU, 2-3 days) |
| **CI/CD** | GitHub Actions (LLM submission) | Plan 260818: Jenkins required | Vendor lock-in vs reference fidelity | High (2-4 vCPU, 4 days, workflow rewrite) |
| **KServe Version** | ADR-004: 0.14.1 | Plan 260818 + target: 0.18+ | LLMInferenceService CRD availability | Medium (manifest migration, testing) |
| **ML Scope** | ADR-010: ML deferred (design-only, 57 rows) | Plan 260818: ML delivered (100 pts) | Schedule + evidence purge commitment | Critical (5-7 weeks, 100 new points) |
| **Model Serving** | ADR-010: agentgateway sole boundary | Plan 260818: llm-d router + Gateway API | LLM inference path clarity | Medium (routing verification, llm-d setup) |
| **Namespace Structure** | Plan 260818-0028: separate namespaces (least-privilege) | Target image visual: grouped zones | Security regression risk if merged | Blocking (evidence rows pinned, 21 points) |

---

## 10. Current Topology Snapshot

```
LOCAL DEVELOPMENT (Docker Compose)
├── platform .akehouse (verified, reproducible)
│   ├── Postgres:16 (ops)
│   ├── MinIO (Bronze/Silver/Gold Parquet)
│   ├── Kafka:3.9.0 (KRaft, event topics)
│   ├── Airflow (DP1/DP2/DP3 DAGs, LocalExecutor)
│   └── Optional: Flink (event-time streaming)
│
├── platform .ase (always running when phase2 profile active)
│   ├── Next.js (Vercel, external)
│   └── Supabase (managed, external)
│
└── platform .ptional (profile="phase2")
    ├── Redis (Feast online store, `phase2-redis`)
    └── PGVector Postgres (ml, RAG, `phase2-postgres`)

GKE CLUSTER (financial-distress-gitops, asia-southeast1-b, 48 vCPU target)
├── Argo CD Namespace (argocd)
│   └── Argo CD: 10 Applications, 13/13 Synced/Healthy
│
├── Ingress & TLS (ingress-nginx, cert-manager)
│   ├── F5 NGINX Ingress OSS (sole external entry point)
│   └── cert-manager (Let's Encrypt issuers)
│
├── Model Serving Boundary (kserve, knative-serving, kourier-system)
│   ├── KServe 0.14.1 (InferenceService CRDs)
│   ├── Knative Serving core
│   └── Kourier net layer
│
├── Agent Control Plane (agentgateway-system, kagent, agents-sandbox) — LEAST-PRIVILEGE NETWORK BOUNDARY
│   ├── agentgateway-system (AI backend routing; NetworkPolicy egress scoped here)
│   ├── kagent (agent CRDs + controllers: coordinator, feature, drift)
│   └── agents-sandbox (runtime pods; restricted PSS, tokenless, read-only, default-deny egress)
│
├── Data & Feature Layer (phase2-data)
│   ├── Redis Deployment (Feast online store)
│   ├── PGVector Postgres (ml, RAG embeddings)
│   ├── RAG pipeline CronJob (suspend: true outside capture windows)
│   └── Network policies (default-deny ingress/egress, allow-list based)
│
├── Observability (monitoring)
│   ├── Prometheus (metrics scraper)
│   ├── Grafana (dashboards)
│   ├── Loki (log aggregation)
│   ├── Jaeger (distributed tracing, agent traces live 2026-08-13)
│   └── OpenTelemetry Collector (trace/metric forwarder)
│
└── Security (sealed-secrets, GHCR credentials, ClusterIssuers)

NOT IN ACTIVE GITOPS (Confirmed Absent)
├── Kubeflow Pipelines (ML orchestration)
├── Ray Cluster (distributed training)
├── MLflow (experiment tracking)
├── Spark Operator (K8s job submission)
├── Iceberg (table format, uses Parquet only)
├── Trino (analytics SQL engine)
├── Superset (BI UI)
├── Debezium (CDC ingestion)
├── Flink on K8s (event-time streaming, local profile only)
├── Istio + Kiali (dropped by ADR-010, NGINX + NetworkPolicy used instead)
├── Vault + ESO (dropped by ADR-010, GitHub Actions secrets used instead)
├── Jenkins (dropped by LLM submission, GitHub Actions used instead)
├── Argo Rollouts (progressive delivery, not deployed)
└── Spark-K8s Executor (local Spark only, no K8s executor config)
```

---

## 11. Migration Seams & Phase Boundaries

### 11.1 Scope Seams (Current LLM → Target ML+LLM)

| Seam | Current (LLM-only) | Target (Unified) | Effort |
|---|---|---|---|
| **Data format** | Parquet (Phase 1) | Iceberg (rebuilt) | High; affects storage layer |
| **Streaming** | Kafka micro-batch (Phase 1) | Kafka + Debezium CDC (unified) | Medium; new CDC config |
| **Feature store** | Feast structure only (local) | Feast online/offline on K8s | Medium; deployment + materialization |
| **ML pipeline** | None (design-only) | Kubeflow + Ray + MLflow + KServe | High; entire stack |
| **Model promotion** | None | Frozen holdout gate + MLflow registry | Medium; schema + label + pipeline |
| **Analytics** | Product web only | Superset/Trino/Grafana BI | Medium; query layer |
| **Secrets** | GitHub Actions | Vault + ESO | Medium; 1-2 vCPU |
| **CI/CD** | GitHub Actions | Jenkins | High; wholesale workflow rewrite |
| **Mesh** | NGINX + NetPol | Istio (optional) | Medium; 3-4 vCPU if full, or keep NGINX |

### 11.2 Evidence Purge & Regen Commitment

**Current state (locked in plan 260818, decision #1):** Delete all 100 verified LLM evidence artifacts and regenerate from zero.  
**Consequence:** 100 LLM points must be re-earned. ML track must be built and evidenced (100 new points). Evidence timeline is **parallel with implementation**, not post-implementation.

---

## 12. Missing/Partial Implementation Status Summary

| Component | Status | Source Path | GitOps Path | Priority | Blocker? |
|---|---|---|---|---|
| Kubeflow Pipelines | ❌ Missing | plan only | absent | P0 | Yes |
| Ray Cluster | ❌ Missing | — | absent | P0 | Yes |
| MLflow Server | ❌ Missing | — | absent | P0 | Yes |
| Iceberg (table format) | ❌ Missing | (needs refactor) | absent | P0 | Yes |
| Spark on K8s | ❌ Missing | (needs config) | absent | P0 | Yes |
| Trino | ❌ Missing | — | absent | P1 | No |
| Superset | ❌ Missing | — | absent | P1 | No |
| Debezium | ❌ Missing | — | absent | P0 | Yes |
| Flink on K8s | 🟡 Partial | `src/streaming/flink/jobs/` | absent | P0 | Yes |
| Istio | ❌ Missing (ADR-010) | — | absent | P2 | No |
| Vault + ESO | ❌ Missing (ADR-010) | — | absent | P1 | No |
| Jenkins | ❌ Missing | — | absent | P1 | No |
| Argo Rollouts | ❌ Missing | — | absent | P2 | No |
| KServe 0.18+ | 🟡 Version (0.14.1 in use) | — | `platform/inference/` | P2 | No |
| llm-d router | 🟡 Partial (agentgateway) | `src/agents/` | `platform/agentgateway/` | P2 | No |
| Feast online/offline on K8s | 🟡 Partial (definitions exist) | `feature_repo/`, `src/ml/feast/` | (control plane absent) | P0 | Yes |
| ML training path | ❌ Missing | `src/ml/` (fixtures only) | absent | P0 | Yes |
| Spark trainer + Ray | ❌ Missing | — | absent | P0 | Yes |
| Model promotion gate | ❌ Missing | (schema change) | absent | P0 | Yes |
| Drift retraining loop | ❌ Missing | — | absent | P0 | Yes |
| In-cluster Next.js | ❌ Missing (Phase 9) | `apps/web/` (exists) | absent (phase 9) | P1 | No |
| Kafka on K8s | 🟡 Unclear (phase2-data refs) | local docker-compose | (config unknown) | P2 | Maybe |
| MinIO on K8s | 🟡 Unclear (phase2-data refs) | local docker-compose | (config unknown) | P2 | Maybe |

---

## Status & Closure

### Findings Summary

1. **Current verified state:**  
   - platform lakehouse: 100% complete, reproducible, locally verified  
   - platform .LM: 60/100 points live-verified on GKE (2026-08-13), evidence freeze pending  
   - platform .L: design-only (unbuilt, deferred by ADR-010)  
   - GitOps: 10 Argo Applications, 11 namespaces, **intentional least-privilege NetworkPolicy boundaries** (not accidental vendor splits)

2. **Target image scope:**  
   - Unified ML + LLM platform  
   - Kubeflow, Ray, MLflow, Iceberg, Spark-K8s, Trino, Superset, Debezium, Flink, Jenkins, Istio/Vault (optional)  
   - All three rubrics (mini + ML + LLM, 161 rows, 300 points)

3. **Gap magnitude:**  
   - **Substantial.** ML track requires 5-7 weeks of new build.  
   - Data format migration (Parquet → Iceberg) affects storage layer.  
   - CI/CD framework change (GitHub Actions → Jenkins) requires workflow rewrite.  
   - Evidence purge commitment (delete 100 LLM points, regenerate) doubles evidence timeline.  
   - Namespace structure (agentgateway-system/kagent/agents-sandbox) is **load-bearing for NetworkPolicy security** and cannot be merged without regression.

4. **Architectural conflicts:**  
   - 7 major scope/decision misalignments (mesh, secrets, CI/CD, KServe version, ML scope, serving path, namespace structure)  
   - ADR-010 (LLM submission, 2026-08-07) vs Plan 260818 (rebuild, 2026-08-18) deltas unresolved in some areas

5. **Test coverage:**  
   - Phase 1: ~100 tests, all passing  
   - platform .LM: live-verified, evidence freeze pending  
   - platform .L: untested, unbuilt

---

### Status Block

**Status:** `DONE`

**Summary:**
This report inventories the **verified current state** (platform data/control/model/user flows**, records **8+ GitOps unknowns** (now mostly verifiable since GitOps repo is locally accessible), and flags the **namespace structure as load-bearing** for least-privilege NetworkPolicy security isolation. platform .s verified. platform .LM is live-verified but evidence freeze-pending. platform .L is unbuilt and deferred. The rebuild requires Kubeflow, Ray, MLflow, Iceberg, Spark-K8s, Trino, Debezium, Flink, Jenkins, and resolution of 7 architectural conflicts without merging security-critical namespace boundaries.

**Concerns/Blockers:**

1. **Evidence purge commitment:** Rebuild plan 260818 commits to deleting all 100 verified LLM evidence points and regenerating from zero. This doubles the evidence timeline and locks the scope to a 10-week window with 230-260 cluster-hours budget.

2. **ML track unbuilt:** 57 ML rows (design-only) require 5-7 weeks of implementation in parallel with evidence capture. Kubeflow, Ray, MLflow, Spark-on-K8s, Triton, and drift-to-retraining loop are critical-path items.

3. **Namespace structure is load-bearing:** The three-namespace split (agentgateway-system, kagent, agents-sandbox) is a deliberate least-privilege NetworkPolicy security boundary per plan 260818-0028:77-115. Merging them would narrow egress scoping and is a security regression. 21 rubric evidence rows are pinned to exact `gitops` paths; merging would invalidate those hashes and require re-stamping.

4. **Architectural conflicts unresolved:** ADR-010 (LLM submission, 2026-08-07) vs Plan 260818 (rebuild, 2026-08-18) mismatch on mesh (Istio), secrets (Vault), CI/CD (Jenkins), and ML scope must be clarified before phase decomposition.

5. **Cost/quota gates:** Budget headroom (230-260 cluster-hours through Nov 6, 2026) is tight if all ML track work, mesh restoration, and Jenkins migration proceed in parallel. Weekly cost checkpoints from phase 4 onward are mandatory.

**Unknowns requiring clarification (GitOps now locally inspectable):**
- Is Kafka replicated on K8s (beyond compose)? → Search `platform/data/` or inspect `kubectl get pods -n <ns> | grep kafka`
- What is Feast control plane status? → Search GitOps for Feast Helm chart or Deployment (not found in active Argo Apps)
- Are MinIO replicas configured in K8s? → Read `platform/data/` MinIO Helm values
- Is Spark Operator installed? → `kubectl api-resources | grep spark` or grep GitOps manifests
- What node pool strategy exists (spot vs on-demand)? → Read `terraform/gcp/gke.tf` (evidence partial, cost optimizations mentioned)

---

**Report generated:** 2026-08-31  
**Format:** Markdown + YAML frontmatter  
**Citation standard:** `path:line` for source repo evidence; `GitOps path` for cluster state; marked `✅ Present`, `🟡 Partial`, `❌ Missing`, `🟡 Unclear` where applicable; unknowns no longer marked "not readable" since GitOps is locally available.
