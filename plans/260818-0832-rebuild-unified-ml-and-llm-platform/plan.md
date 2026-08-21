---
title: "Rebuild Unified ML And LLM Platform"
description: "Rebuild the coursework platform against the two reference MLOps architectures, delivering all three rubrics — mini-coursework (44 rows), ML (57 rows) and LLM (60 rows), 100 points each — on one GKE cluster, with every evidence artifact regenerated from zero under a single phase-free evidence tree."
status: pending
priority: P1
effort: "10 weeks; hard stop 2026-11-06 (GCP free-trial credit expiry)"
branch: dev
tags: [coursework, ml, llm, mlops, kubernetes, gitops, gcp, rebuild]
blockedBy: []
blocks: []
created: 2026-08-18
---

# Rebuild Unified ML And LLM Platform

## Overview

The existing project reached 100/100 on the LLM track but is structurally unsound
for a full submission: the ML track's 57 rows are all `design_only` and its GitOps
scaffolding sits in `financial-distress-gitops/archive/ml-track/`; the data plane
generates 16 rows / 780 KB, which cannot substantiate the Spark-skew, Spark-UI and
lakehouse-compaction rows the mini-coursework rubric demands; and the evidence tree
is split across `docs/evidence/` (Phase 1) and `docs/phase2/evidence/` (Phase 2),
a division the coursework itself never asks for.

This plan rebuilds the platform against the two reference architectures
(`images/architecture/reference-recsys-mlops-overview.png` and the Feature-Store /
Next-Best-Action reference), delivers **both** tracks, and regenerates **every**
evidence artifact from zero under one unified, phase-free tree.

### Decisions locked with the user on 2026-08-18

| # | Decision | Consequence |
|---|----------|-------------|
| 1 | Additive retrofit of code and platform; **delete all existing evidence and regenerate** | The 100 LLM points already executed must be re-earned. No evidence artifact survives. |
| 1b | Scope is **all three rubrics**: mini-coursework + ML + LLM, 161 rows / 300 points | The old matrix covered only ML+LLM (117 rows) because mini-coursework was Phase 1. With the phase split gone and the data plane rebuilt on Iceberg at 10-50M rows, the mini evidence would be invalidated anyway — Spark skew, compaction and DataHub lineage all have to be recaptured. |
| 2 | Evidence is **no longer split by phase** | One tree, one matrix, 161 rows, keyed by rubric section. |
| 3 | GCP quota target **48 vCPU**, locked as the planning baseline | Submit on day 1 — approval takes 1-3 days. 48 is the requirement, not a stretch goal: at 32 the mesh-wide sidecar decision does not fit and the architecture has to change. |
| 4 | **Jenkins + HashiCorp Vault**, replacing GitHub Actions + sealed-secrets | Exact reference fidelity; ~2 vCPU and ~4 days of migration. |
| 5 | **Kubeflow Pipelines + Ray + MLflow + KServe/Triton** for the ML track | Matches the rubric wording verbatim ("Kubeflow pipeline", "distributed training", "Model Registry qua MLFlow", "Inference Engine ví dụ KServe"). |
| 6 | **MinIO + Iceberg + Spark + Trino + Superset** for the lakehouse | Spark is non-substitutable — the rubric requires Spark UI screenshots. Iceberg over DuckLake because Spark cannot write DuckLake natively. |
| 7 | **Feast + Redis online + Postgres offline + Debezium → Kafka → Flink** | Matches reference 1's dataflow namespace exactly. |
| 8 | Scale the generator to **10-50M rows / 5-20 GB** | Makes skew, small-file and compaction evidence real rather than asserted. |
| 9 | **Istio full sidecar mode**, mesh-wide, for service-to-service authorization | Maximum reference fidelity and the richest evidence — Kiali renders the whole platform's service graph and L7 telemetry comes free. Costs ~4-6 vCPU and 4-8 GB across 40-60 pods, and makes native-sidecar configuration mandatory for every Job-producing workload. See the capacity note below. |
| 10 | **Two repos retained**: app monorepo + GitOps control repo | Preserves least-privilege GitOps; only the evidence tree is restructured. |
| 11 | Novel ideas: DuckLake-vs-Iceberg benchmark, point-in-time leakage guard, LLM semantic cache + speculative decoding | Three ideas cover the four novel-idea rows (2 per track). |
| 12 | Timeline ~10 weeks, no hard external deadline | Bounded only by credit expiry on 2026-11-06. |
| 13 | **KServe pinned to 0.18+, LLM served through llm-d** via `LLMInferenceService`, vLLM CPU backend | The old project pinned KServe `v0.14.1`, which predates the `LLMInferenceService` CRD that llm-d integrates with — a version constraint, not an architecture decision. Rebuilding removes it. Affects the ML track too: Triton serving migrates to the same 0.18+ install. Carries a dependency the earlier draft missed: llmisvc is a **Gateway API** resource (Gateway API + GIE + LeaderWorkerSet + a gateway provider), not a Knative one — see the routing section below. |
| 14 | **Frozen holdout `gold.distress_holdout_v1`, pinned by an Iceberg tag, is the sole promotion gate**; model promotion runs as a second Jenkins lane sharing `bump-gitops` | Added 2026-08-19. Online A/B has no ground truth, so the offline comparison is the only check on model quality — and it is worthless unless champion and candidate are scored on identical data. A rolling evaluation window fails silently: the pipeline stays green and promotes anyway. Costs a `label_event_ts` column on the label table (phase 2), one embargo window of training data, and a hard equality assert in phase 7. |

### GPU constraint

`GPUS_ALL_REGIONS` is **0** and GCP blocks GPU quota increases on free-trial
accounts, so the whole platform is CPU-only. This bounds what llm-d can be claimed
to deliver: disaggregated prefill/decode is a GPU-oriented feature and will not
produce a meaningful measurement here, so it is not a deliverable. **KV-cache aware
routing is**, and it is measurable on CPU — repeated multi-turn requests sharing a
prefix route to the pod already holding that cache, cutting TTFT. That routing
on/off comparison is the evidence for the "benchmark model server and optimize the
platform" row, alongside quantization. Any claim in the final write-up must stay
inside what CPU can demonstrate.

**The CPU backend is a fork, not a risk to monitor.** vLLM's own documentation says
it is not intended for CPU inference and has not been optimized for it, and llm-d
and `LLMInferenceService` are GPU-oriented throughout their docs. Phase 4 step 11
therefore decides between two architectures, and each has its own evidence story
written before the benchmark runs, not after:

| Branch | Serving path | LLM optimization evidence |
|---|---|---|
| **A — vLLM CPU usable** | `LLMInferenceService` on llm-d, Gateway API router | KV-cache-aware routing on/off TTFT comparison **plus** quantization |
| **B — vLLM CPU unusable** | llama.cpp OpenAI-compatible server behind a plain `InferenceService` with a custom `ServingRuntime` | Quantization (GGUF q4 vs q8), batch-size and thread-pinning sweeps, and a prompt/prefix **semantic cache** hit-rate comparison at the gateway |

Branch B is not a drop-in backend swap, and the earlier draft was wrong to describe
it as one: there is no shipped llama.cpp `ServingRuntime` for KServe (the proposal
is open as kserve issue #5334), and dropping llm-d drops KV-cache-aware routing with
it. Branch B keeps the same rubric row by moving its evidence to the semantic cache
— which phase 8 builds as a novel idea anyway — so the row is covered either way.
What must not happen is claiming branch A's routing evidence while running branch B.

### Capacity budget at 48 vCPU

The full stack does **not** fit resident at 48 vCPU. This is a design constraint, not
a warning to keep in mind — component residency has to be scheduled.

| Group | Idle vCPU | Resident when |
|---|---:|---|
| Istio (istiod + mesh-wide sidecars) + Kiali | 5-6 | Always — sidecars scale with pod count |
| Core platform: Argo CD, Argo Rollouts, Vault, ESO, cert-manager, NGINX | 2-3 | Always |
| Gateway API stack for llm-d: GIE endpoint-picker + LeaderWorkerSet controller (gateway provider is Istio, already counted above) | 1-2 | Always — the llmisvc router depends on it |
| Observability: Prometheus, Grafana, Loki, Jaeger, OTel Collector, PushGateway | 3-4 | Always |
| Stores: MinIO, Postgres, Redis | 2-3 | Always |
| Serving: KServe/Knative, Triton, vLLM, agents, MCP, gateway, registry | 6-12 | Serving + LLM windows |
| Kafka + Connect/Debezium + Flink | 5-7 | Streaming window |
| Airflow | 2-3 | Pipeline windows |
| Kubeflow Pipelines standalone | 3-4 | Training window |
| DataHub (GMS + frontend + single-node Elasticsearch; Kafka and Postgres reused) | 2-3 | Governance/lineage window |
| Trino (+ Superset) | 2-4 | Analytic window |
| Jenkins controller (agents ephemeral) | 1-2 | CI windows |
| **Idle total if everything resident** | **35-53** | — |
| Burst: Spark job, Ray workers, Locust | +6-12 | Their own windows only |

**Always-on floor is roughly 12-16 vCPU**, leaving ~32 for scheduled work. That is
comfortable for any two or three groups at once and impossible for all of them. So:

- Spark, Ray and Kubeflow scale to zero outside the training/processing windows — already committed in phase 5.
- **DataHub, Trino, Superset, Flink and Jenkins do the same.** None needs to be resident outside its own window. This is the discipline the earlier draft left implicit and it is now load-bearing.
- Phase 8's single-window capture is the one time much of this runs together, and it runs in dependency order so a mid-window failure loses only the tail.

If Google grants less than 48, the mesh-wide sidecar decision is the first thing to
revisit — selective injection in `api-serving`, `agents` and `kserve` recovers
roughly 3-4 vCPU while keeping the mesh row, the Kiali graph of the request path and
the A/B mechanisms. Decide at phase 4 step 1, before provisioning. Note that
`kserve` cannot be dropped from the injected set under that fallback: Istio is the
Gateway API provider for llm-d's router.

Mesh-wide injection also makes one configuration detail load-bearing rather than
optional: Istio sidecars historically prevent Kubernetes Jobs from ever reaching
`Completed`, because Envoy keeps running after the job container exits. That breaks
Kubeflow pipeline steps, Ray jobs, Spark driver/executors and Airflow's
`KubernetesPodOperator` — roughly half the ML track. Kubernetes 1.33 made native
sidecars stable and the cluster runs GKE 1.35.6, so the fix is available; it is not
automatic. Every Job-producing workload must be verified to terminate, and that
verification is a phase-4 gate, not something to discover mid-pipeline in phase 5.

### Cost reality — measured 2026-08-18

The billing account is denominated in **VND**, not USD. Of the USD 300 trial credit,
**~2,000,000 VND (~USD 77) is already spent**, leaving **~USD 223** against an expiry
of 2026-11-06 — **80 days**. Figures below are estimates from public list prices and
must be reconciled against the Console; the conclusions are robust to the error bars,
the exact numbers are not.

**Where the money was actually going.** Idle spend — billed even with every node
scaled to zero — was ~USD 62/month, and compute was not the problem:

| Item | USD/month | Share |
|---|---:|---:|
| 3 network load balancers @ ~USD 0.025/hr | 54 | **87%** |
| 60 GB persistent disk (30 GB orphaned PVCs, 30 GB on a stopped VM) | 8 | 13% |

Two of the three load balancers should never have existed, and deleting them fixes a
rubric violation as well as the bill:

| Forwarding rule | Backing service | Verdict |
|---|---|---|
| `34.21.242.110` | `ingress-nginx` | **Keep** — the real gateway, holds the static IP |
| `35.240.138.190` | `kourier-system/kourier` | **Remove** — this plan replaces Kourier with `net-istio`; it should have been ClusterIP behind NGINX regardless |
| `136.85.22.129` | `agentgateway-system/agentgateway-proxy` | **Remove** — an external LB of its own directly contradicts the rubric row "các service cần được hide đằng sau gateway" |

Both are removed by changing the Kubernetes `Service` type to `ClusterIP` in the
GitOps manifests, not by deleting the forwarding rule — GKE recreates a rule deleted
underneath a `LoadBalancer` Service.

**Storage is not worth optimizing here.** The 30 GB of orphaned PVCs costs ~USD 3.5
per month; reclaiming it saves ~USD 9 across the whole project. Correspondingly,
moving data processing onto the cluster to "use up" that disk would be a net loss:
it spends compute at ~USD 1.6/hour to avoid a few dollars of storage. Phase 2 keeps
its local-first approach — develop against a 100K-row sample locally, run full
volume on the cluster only inside a dedicated evidence window.

**Budget after the fixes:**

| Scenario | Idle, full period | Compute budget | Hours at 48 vCPU |
|---|---:|---:|---:|
| Unchanged | 161 | 62 | ~35 |
| Two LBs removed | 68 | 155 | ~88 |
| **Two LBs removed + spot burst pool** | **68** | **155** | **~230-260** |

35 hours does not survive phase 4 alone. **Node pools are therefore split by
preemption tolerance**: a small on-demand pool (~12 vCPU) holds Postgres, MinIO, the
Istio control plane, Argo CD and observability — anything where a mid-write eviction
hurts — and a larger spot pool (~36 vCPU) carries Spark, Ray, Kubeflow, Trino,
DataHub and serving, all of which are restartable. Spot pricing is 60-70% below
on-demand and preemption of a batch job costs a re-run, not an artifact.

### Accepted risk

Deleting executed evidence forfeits 100 verified LLM points until they are
re-earned. Combined with the ML track and a 10-50M-row data plane, total cluster
hours rise roughly 2.5x against the previous plan. Even after the cost fixes above,
the budget is ~230-260 cluster-hours for roughly eight weeks of work — about 30
hours a week, with no slack for a multi-day debugging detour. Istio mesh-wide
sidecars, the Vault migration and the Jenkins cutover are each capable of consuming
that slack. The cost ledger is a weekly checkpoint from phase 4 onward, not a
phase-8 formality.

### Supersedes

These plans are superseded on adoption. They stay on disk as history; none of
them is an execution authority once this plan starts.

| Plan | Why superseded |
|---|---|
| `260802-1037-unified-phase2-ml-llm-gitops` | Owned the phase split, the two-track deferral and the old evidence contract — all three are removed here |
| `260809-2039-complete-phase2-llm-submission` | Sequenced LLM-only execution against evidence that is being purged |
| `260811-1627-close-llm-rubric-to-100` | Closed rows whose evidence no longer survives |
| `260812-1320-close-last-4-llm-points` | Same |
| `260813-1846-production-hardening-overlay` | Its SHA-stamping and repo-layout work is replaced by the phase-1 contract rebuild |
| `260806-2234-architecture-hygiene-before-phase-3` | Never executed; its layout concerns are absorbed into phases 1 and 4 |

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Score all 161 rubric rows (mini 100 + ML 100 + LLM 100) with executed, re-generated evidence | P0 |
| 2 | Restructure evidence into one phase-free tree with a single 161-row matrix and one auditor | P0 |
| 3 | Rebuild the data plane so Spark, lakehouse and drift evidence rests on real data volume | P0 |
| 4 | Match the reference architectures component-for-component where a rubric row depends on it | P0 |
| 5 | Keep GitOps the sole cluster deployment path, with Jenkins as the sole CI/CD driver | P1 |
| 6 | Stay inside the free-trial credit and the approved vCPU quota | P1 |

## Non-goals

- Preserving any existing evidence artifact, SHA stamp or frozen revision.
- Merging the two repositories.
- Expanding the product surface beyond what already exists — only three UI rows (6 points) are scored, and phase 9 migrates the app rather than growing it.
- Replacing Spark with Polars/Daft/DuckDB (breaks the Spark-UI rubric rows).
- Adopting DuckLake as the primary table format (it is a benchmark subject only).
- Retaining GitHub Actions beyond the Jenkins cutover.

## Phases

| # | Phase | Estimate | Status |
|---|-------|----------|--------|
| 1 | [Lock the unified contract and purge evidence](./phase-01-start.md) | 1 week | Pending |
| 2 | [Rebuild the data plane on Iceberg and Spark](./phase-02-rebuild-data-plane-on-iceberg-and-spark.md) | 1.5 weeks | Pending |
| 3 | [Rebuild streaming and the feature store](./phase-03-rebuild-streaming-and-feature-store.md) | 1 week | Pending |
| 4 | [Provision the platform foundation on GKE](./phase-04-provision-platform-foundation-on-gke.md) | 1.5 weeks | Pending |
| 5 | [Deliver the ML track](./phase-05-deliver-ml-track.md) | 2 weeks | Pending |
| 6 | [Deliver the LLM and agent track](./phase-06-deliver-llm-agent-track.md) | 1.5 weeks | Pending |
| 7 | [Migrate CI/CD to Jenkins and close verification](./phase-07-migrate-ci-cd-to-jenkins-and-close-verification.md) | 1 week | Pending |
| 9 | [Migrate the web plane into the cluster](./phase-09-migrate-web-plane-into-the-cluster.md) | 1 week | Pending |
| 8 | [Capture evidence, novel ideas and freeze](./phase-08-capture-evidence-novel-ideas-and-freeze.md) | 1.5 weeks | Pending |

Phase 9 is numbered last but **scheduled in parallel with phases 5-6**, since it
depends only on the platform from phase 4. Phase 8 remains the final phase.

### Critical path and sequencing rationale

Phase 1 goes first because the auditor and the matrix define what "done" means for
every later row; rebuilding evidence against an unrevised contract wastes the work.
Phase 4 (cluster) runs in parallel with phases 2-3 from the moment the quota
increase lands — the data plane is developed locally against MinIO and only
promoted to the cluster once the platform exists. The ML track precedes the LLM
track because ML is the unbuilt half and carries the schedule variance; the LLM
track is a re-execution of code that already worked, so it is low-variance work
deliberately placed after the risky half.

If the schedule slips, cut in this order: Superset (no rubric row depends on it),
the third novel idea, then A/B progressive rollout depth. Never cut the test suite
or observability — they carry more points across more rows than any single feature.

## Target architecture

```
GKE cluster (48 vCPU, asia-southeast1-b)
│
├─ ns: dataflow      MinIO ─ Iceberg ─ Spark ─┐   Debezium → Kafka → Flink
│                                              └─ Feast (Redis online / Postgres offline)
├─ ns: analytic      Trino → Superset
├─ ns: governance    DataHub, Airflow
├─ ns: kubeflow      Kubeflow Pipelines, Ray cluster
├─ ns: tracking      MLflow (Postgres metadata + MinIO artifacts)
│                    promotion gated on gold.distress_holdout_v1 @ tag holdout-v1
├─ ns: rollouts      Argo Rollouts (progressive delivery for the API/web Deployments)
├─ ns: kserve        KServe 0.18+: Triton champion / candidate (ML, canaryTrafficPercent),
│                    LLMInferenceService on llm-d, vLLM CPU backend (LLM),
│                    Gateway API + GIE + LeaderWorkerSet; GatewayClass: istio,
│                    Gateway is ClusterIP behind the single NGINX Ingress
├─ ns: api-serving   feature-api, drift-api, MCP servers (KEDA-autoscaled)
├─ ns: agents        kagent agents, agent registry, agentgateway, sandbox
├─ ns: observability Prometheus, Grafana, Loki, Jaeger, PushGateway, OTel Collector
├─ ns: ci            Jenkins controller + agents
├─ ns: security      Vault, External Secrets Operator
├─ ns: istio-system  Istio (sidecar injection mesh-wide) + Kiali
└─ ns: ingress       NGINX Ingress, cert-manager
```

Control plane: Argo CD reconciling `financial-distress-gitops`; Terraform for GKE +
GCE VM; Ansible for VM configuration.

**The web plane moves into the cluster** (phase 9). Vercel and Supabase are both
removed: the Next.js app becomes an ordinary Helm-deployed workload behind NGINX,
authenticating against in-cluster PostgreSQL, built by Jenkins, reconciled by Argo
CD, enrolled in the mesh and traced by OpenTelemetry. The agent chat UI and agent
registry UI are routes inside it rather than separate surfaces. This is what makes
"everything runs on Kubernetes" true of the deployment diagram, and it puts the app
inside every mechanism the coursework grades.

## Routing, domain and TLS

The Routing & Gateway block is the largest point cluster after CI/CD — **24 points**
across both tracks — and all of it hangs on one ingress and one working domain:

| Requirement | ML | LLM |
|---|---:|---:|
| Grafana behind the gateway | 2 | 2 |
| Log viewer behind the gateway | 2 | 2 |
| Trace viewer behind the gateway | 2 | 2 |
| Feature API / agent-test UI behind the gateway | 2 | 2 |
| Agent registry UI behind the gateway | — | 2 |
| Basic auth + rate limit | 2 | 2 |
| Domain + HTTPS | 1 | 1 |
| **Total** | **11** | **13** |

**One NGINX Ingress, one load balancer, one wildcard certificate, subdomain-based
routing** on a registered domain (replacing `distresslens.duckdns.org`). Every
service reaches the outside world through it; nothing else gets a `LoadBalancer`
Service. This is the same constraint that removes the two redundant load balancers
in phase 4 — it is one architecture serving both the bill and the rubric.

```
*.<domain>  ──▶ NGINX Ingress (single LB, wildcard TLS)
  <domain>          web app (product + /agents/chat + /agents/registry)
  api.<domain>      feature API      ← the "domain & HTTPS" row targets this service
  drift.<domain>    drift API
  grafana. logs. jaeger. kiali.      observability viewers
  argocd. jenkins. airflow. mlflow. datahub. superset.   platform consoles
```

**Register the domain wherever it is cheapest, but host DNS on Cloudflare.** A
wildcard certificate requires an ACME **DNS-01** challenge, and DNS-01 requires
cert-manager to hold a solver for the DNS provider. Most budget registrars — `.id.vn`
included — ship no cert-manager solver, so a wildcard would simply never issue, and
that failure surfaces only after every Ingress host has already been rewritten.
Cloudflare's DNS is free, cert-manager has a first-class Cloudflare solver, and
nameservers can point there regardless of registrar. The Cloudflare API token goes
into Vault like every other credential.

## Serving-loop and diagram review (2026-08-21)

A walkthrough of the architecture diagram against both rubrics surfaced four
gaps that the phase files do not yet name, plus one labelling rule. All four are
small additions to work already planned; none changes a locked decision.

**1. Drift must also read serving traffic, not only the offline store.** Phase 5
computes PSI from offline features against a reference window. That detects data
drift in the warehouse but never sees what the models actually received. Add a
serving-side log: Triton, the LLM inference service and `feature-api` emit one
record per request to a Kafka `inference_log` topic — request id, timestamp,
model version, feature version, feature payload, prediction, latency — sunk into
`gold.inference_log` on Iceberg. The drift DAG compares that table against the
holdout reference, and joins it to `gold.labels` on `label_event_ts` for
performance drift once outcomes land. Without it the A/B dashboard and the drift
gate describe two different populations.

**2. Progressive delivery uses three mechanisms, not one — and the constraint is
one *load balancer*, not one routing API.** The earlier draft of this section said
Argo Rollouts would drive both tracks through `trafficRouting.nginx`. That is not
implementable, for two independent reasons found on 2026-08-21:

- **Argo Rollouts cannot own a KServe workload.** Rollouts drives pods through a
  `Rollout`, or a `workloadRef` to a workload that provides a Pod template
  (documented as Deployment). A serverless-mode `InferenceService` is a Knative
  Service whose Deployment belongs to the Knative controller, so there is nothing
  for Rollouts to take ownership of. KServe's own canary is `canaryTrafficPercent`,
  and its documentation states canary is supported **only** in serverless mode —
  `RawDeployment` cannot do it either.
- **`LLMInferenceService` is a Gateway API resource, not a Knative one.** Its
  documented dependencies are Gateway API, the Gateway API Inference Extension
  (GIE), a gateway provider and LeaderWorkerSet; it creates `Gateway` and
  `HTTPRoute` objects itself, and Knative is not involved. Forbidding Gateway API
  forbids llm-d.

So each surface uses the mechanism that actually fits it:

| Surface | Mechanism | Why |
|---|---|---|
| `feature-api`, `drift-api`, `prediction-api`, web | **Argo Rollouts** canary + `AnalysisTemplate`, `trafficRouting.nginx` (stable Ingress + canary Ingress carrying `nginx.ingress.kubernetes.io/canary-weight`) | Real Deployments, so Rollouts can own them. This is where the progressive-delivery and automatic-rollback rows are earned. |
| Triton champion / candidate (ML) | **KServe `canaryTrafficPercent`**, serverless mode, stepped 10 → 25 → 50 by the promotion pipeline, with the same Prometheus queries the `AnalysisTemplate` uses run as an explicit pipeline gate | The only canary KServe supports for an `InferenceService`. |
| LLM A/B pair | **`LLMInferenceService` router weights** (Gateway API `HTTPRoute`) | The CRD's own routing layer; nothing else can split traffic between llm-d-backed variants. |

The single-edge constraint survives intact, restated precisely: **exactly one
`LoadBalancer` Service exists cluster-wide** — the NGINX Ingress holding the static
IP, the wildcard certificate, basic auth and rate limiting. The Gateway API
`Gateway` that llmisvc requires is a `ClusterIP` behind it, and **Istio is its
provider** (`GatewayClass: istio`) rather than a second Envoy Gateway install,
since Istio is already mesh-wide. TLS, auth and rate limiting stay in one place.

Because Rollouts mutates the canary annotation in place, the Argo CD Application
must carry `ignoreDifferences` for it, or every weight step is reverted on the next
sync. The same applies to `canaryTrafficPercent` on the `InferenceService` and to
the `HTTPRoute` weights, whichever component last wrote them.

**3. Debezium needs a schema registry.** Phase 3 consumes Debezium envelopes in
Flink. Without a registry the envelope schema is implicit, and a source DDL
change breaks the Flink job at runtime with no contract to fail against. Deploy a
Kafka schema registry alongside Connect and register the CDC subjects.

**4. The agent path needs a guardrail hop.** Coordinator → agent gateway → model
carries user text straight to the model and returns model text straight to the
UI. Insert one guardrail component on both legs: PII redaction and prompt
injection filtering inbound, citation and PII checks outbound. This is also the
honest place to enforce the "agents may not bypass the gateway" negative test.

**5. Diagram labels are evidence.** The deployment diagram is graded from a
screenshot, so a logo alone scores nothing. Every component carries the text a
reviewer needs: metric names on the telemetry path (tokens in/out/total, calls
per agent, calls per MCP tool, req/s, failures), `TTL` on each feature view,
replica counts and `--atomic` on Helm-deployed services, `basic auth + rate
limit` and the hidden-service list on NGINX, `mTLS STRICT + AuthorizationPolicy`
on the mesh boundary, and the secret path on Vault. Components that map to no
rubric row are decoration and come off the diagram.

## Architecture constraint: layering and design patterns

The "Clean Code + clean repo + demonstrate the use of Design Pattern" row is worth
2 points in each of ML and LLM, but its real cost is that it cannot be retrofitted.
A 5000-line `main.py` cannot be documented into a layered design at capture time, so
this is a **build-time constraint on phases 5-7**, not a phase-8 writing task.

Every service written in this plan follows the same layering, dependencies pointing
one direction only:

```
API layer          FastAPI routers, Pydantic request/response models — no business logic
  ↓
Service layer      use cases, orchestration, policy — no I/O, no framework imports
  ↓
Repository layer   Feast, Iceberg, MLflow, Redis, Postgres access behind interfaces
  ↓
Backing stores
```

Patterns are chosen where they remove real coupling, never for decoration:

| Pattern | Where it earns its place |
|---|---|
| Repository | Feature reads behind `FeatureRepository`, so Feast can be faked in tests without a live store |
| Strategy | Drift statistic selection (PSI, KS, chi-square) chosen at runtime from config |
| Factory | Agent construction from registry metadata, so a new agent needs no new wiring code |
| Adapter | `ModelRuntime` interface with Triton, vLLM and llama.cpp adapters — see below |
| Dependency injection | FastAPI dependencies supply repositories and runtimes, making every layer testable in isolation |

The **`ModelRuntime` interface is the load-bearing one** and this plan has a concrete
reason for it, not a textbook one:

```
InferenceService (service layer)
        │  depends on the interface, never on a vendor
        ▼
  ModelRuntime  ─── predict() / generate() / health()
     ╱     │     ╲
 Triton   vLLM   llama.cpp
  (ML)    (LLM)   (fallback)
```

Phase 4 step 9 may have to swap the LLM backend from vLLM to llama.cpp if CPU
throughput proves unusable. Behind this interface that swap touches one adapter.
Without it, the swap reaches into the agents, the gateway wiring and the tests —
which is exactly the failure the rubric row is testing for. The pattern pays for
itself here regardless of the 4 points.

## Evidence contract (rebuilt)

- One matrix: `docs/rubric-matrix.csv`, 161 rows (mini 44, ML 57, LLM 60), generated from the three rubric CSVs.
- One tree: `docs/evidence/<rubric-section>/<rubric_id>.md` — no `phase1`/`phase2` prefix anywhere.
- One auditor: `scripts/audit_rubric_evidence.py`, replacing the phase-split pair.
- Every row carries an executable `validation_command` and a named artifact path.
- No row may be marked executed without an artifact regenerated during this plan.

## Success Criteria

- [ ] `scripts/audit_rubric_evidence.py --strict --require-executed --run-validations` passes over all 161 rows with zero design-only rows and zero cuts
- [ ] Each rubric scores 100/100 on its own scale: mini-coursework, ML, LLM
- [ ] No file under `docs/evidence/` predates this plan's start
- [ ] No path in the repository contains a `phase1`/`phase2` evidence prefix
- [ ] Spark UI screenshots show a genuine skewed stage on ≥10M rows, with a before/after fix
- [ ] Jenkins is the only CI/CD driver; no GitHub Actions workflow deploys anything
- [ ] Vault is the only secret source; no sealed-secret remains in the GitOps repo
- [ ] Total GCP spend stays inside the free-trial credit, reconciled in the cost ledger
- [ ] Deployment diagram in README matches the running cluster component-for-component
- [ ] No model version reaches the GitOps repo without passing the holdout gate; a snapshot mismatch fails the pipeline with a non-zero exit

<!-- slug: rebuild-unified-ml-and-llm-platform -->
