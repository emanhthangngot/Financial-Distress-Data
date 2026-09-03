# the platform Architecture — Product and Evidence Planes

## 1. Current decision and status

the platform is an additive AI/product layer over the verified the platform local-first
lakehouse. The accepted coursework submission is the LLM track: 60 rubric rows
and 100 points. The ML track remains a documented, post-deadline retrofit and
is not claimed as delivered.

| Area | Current state |
|---|---|
| Product plane | Implemented: Next.js, Supabase Auth/Postgres/RLS, analyst/report/registry/chat/evidence-session surfaces |
| Evidence plane | Live-verified on Terraform-provisioned GKE Standard in `asia-southeast1-b` |
| Delivery | Source CI -> immutable image digest -> private GitOps PR -> Argo CD reconcile |
| LLM runtime | agentgateway -> KServe/Knative CPU OpenAI-compatible model server |
| LLM evidence | 60/60 rows and 100/100 logical coverage captured; final freeze pending |
| Submission freeze | Pending source/GitOps SHA restamp and final strict two-repository audit |
| ML runtime | Deferred; rows remain `design_only` |

ADR-010 is the current platform decision. It supersedes earlier AWS/EKS,
Istio, Envoy Gateway/AI Gateway, ECK/Kibana, Vault, and Kustomize proposals
for this submission. It does not remove KServe/Knative from the submitted LLM
serving path: the CPU model server is still reached through agentgateway.

## 2. Repository ownership

The project has one source repository and one deployment repository:

| Repository | Owns | Does not own |
|---|---|---|
| `Financial-Distress-Data` | the platform code/contracts, the platform Python/TypeScript code, product migrations, tests, canonical evidence, runbooks | Live cluster desired state and cloud bootstrap |
| `financial-distress-gitops` | Terraform/GKE bootstrap, Helm values/charts, Argo applications, policies, image digests, ingress, agents, model serving, observability | Application business logic and canonical coursework evidence |

The GitOps repository is private because its working tree contains operational
state that is not suitable for this public source tree. A scrubbed read-only
mirror is a final submission packaging step, not a reason to copy state into
this repository.

## 3. Product plane

The product plane is persistent and intentionally independent of GKE uptime:

- Next.js App Router renders the authenticated analyst, reports, agent
  registry, agent chat, and evidence-session surfaces.
- Supabase Auth provides identity; Postgres and RLS persist user-scoped
  reports, AI usage/audit records, and evidence-session/outbox state.
- The UI displays an explicit evidence-plane state machine. A stopped or
  hibernated GKE cluster is not represented as a successful run.
- The product calls only declared routed interfaces. It does not embed model
  credentials or bypass the evidence-plane security boundary.

Product checks are run from the source repository:

```bash
pnpm --dir apps/web test
pnpm --dir apps/web typecheck
pnpm --dir apps/web lint
pnpm --dir apps/web e2e:live
pnpm --dir apps/web e2e:assistant
```

## 4. Evidence plane

The evidence plane is disposable, cost-bounded, and reconciled from the
separate GitOps repository. The current live topology is:

| Layer | Deployables | Contract |
|---|---|---|
| Bootstrap | Terraform, GKE Standard zonal cluster, Argo CD | Reproducible cluster and desired-state bootstrap |
| Edge | cert-manager, F5 NGINX Ingress OSS | TLS and only external entry point |
| Control | kagent CRDs, `ModelConfig`, coordinator/specialist Agents | Typed agent ownership and model routing |
| Tools | feature-MCP, drift-MCP, feature/RAG API, drift API | Governed retrieval and drift operations |
| Serving | agentgateway, KServe/Knative CPU model server | OpenAI-compatible chat/inference path |
| State | Redis, PostgreSQL/PGVector, MinIO, Feast definitions | Online/offline feature and RAG state |
| Observability | OpenTelemetry, Jaeger, Prometheus, Grafana, Loki | Trace, metric, dashboard, and log evidence |

Every internal service is `ClusterIP` behind NetworkPolicy. Agents run in the
restricted `agents-sandbox` namespace with tokenless ServiceAccounts,
read-only roots, and a limited egress policy.

## 5. Eight numbered flows

### Flow 1 — Analyst request

```text
browser -> Next.js product -> Supabase Auth/Postgres/RLS
                         -> evidence-session state/outbox when live execution is requested
```

The product persists the request and renders the real plane state. It does not
claim a successful live answer before the evidence plane returns one.

### Flow 2 — the platform data foundation

```text
collectors -> Kafka -> Airflow/Spark -> MinIO Bronze/Silver/Gold
                         -> PostgreSQL metadata/DQ -> DuckDB/DBeaver evidence
```

Flink is opt-in for event-time streaming and is not part of the default Docker
startup. the platform consumes the Gold/feature contracts without changing them.

### Flow 3 — RAG ingestion and governance

```text
approved sources -> normalize/hash/chunk -> versioned embeddings
                -> PGVector/MinIO/Feast metadata -> governed retrieval tools
```

Each chunk carries source, license/access class, parser/embedding version, and
lineage metadata required by the evidence contract.

### Flow 4 — Live agent and RAG round-trip

```text
Next.js -> NGINX -> coordinator Agent
                    -> feature Agent -> feature-MCP -> Feast/PGVector/Redis
                    -> drift Agent -> drift-MCP -> drift API
                    -> ModelConfig -> agentgateway -> KServe/Knative model server
coordinator -> citation/PII guard -> Next.js report/chat response
```

Agents use the declared MCP/A2A/model routes. A negative proof prevents a
specialist from bypassing the model boundary and calling the model server
directly.

### Flow 5 — Evidence-session state

```text
product action -> Supabase session/outbox -> worker -> GKE status/verification
              <- persisted honest state, citations, trace IDs, and report data
```

This is the durable hand-off between the persistent product plane and the
disposable evidence plane.

### Flow 6 — CI and GitOps promotion

```text
source commit -> test/build/scan/sign -> immutable image digest
             -> GitOps pull request -> Argo CD -> GKE workloads
```

Only the merged GitOps desired revision is reconciled. Runtime evidence records
both source and GitOps SHAs so a reviewer can reproduce the exact pair.

### Flow 7 — Observability

```text
agents/tools/model -> OpenTelemetry -> Jaeger traces
                  -> Prometheus metrics -> Grafana dashboards
                  -> Loki redaction-safe logs
```

Trace IDs connect coordinator decisions, specialist calls, MCP calls, token and
latency metrics, and the resulting citation evidence.

### Flow 8 — Teardown and freeze

```text
capture complete -> make gcp-down / hibernate -> preserve approved artifacts
                 -> restamp source+GitOps SHAs -> strict two-repo audit -> submit
```

The cluster is not treated as a permanent production environment. Cost and
credential boundaries are part of the acceptance contract.

## 6. Verification and residuals

The live verification snapshot on **2026-08-13** recorded:

- 13/13 Argo CD applications `Synced` and `Healthy`;
- established kagent CRDs and 10 `Ready` agents;
- accepted/reconciled Grafana MCP registration;
- model warm-up and coordinator HTTP 200 with feature and drift citations;
- healthy Prometheus targets and discoverable Jaeger services.

The repository evidence package represents 60/60 LLM rows and 100/100 logical
points. The final submission freeze is still pending because the latest source
and GitOps commits must be restamped into the evidence rows and the strict
two-repository audit must pass without acceptance cuts. A private GHCR image is
also a known operational residual for cold-node startup; the package-read
credential must be supplied through sealed out-of-band deployment state.

## 7. the platform non-mutation rule

the platform code is additive under `src/ml/`, `src/drift/`, `src/llm/`,
`src/agents/`, `apps/`, `packages/`, `supabase/`, and `dags/platform/`. Existing
the platform DAG IDs, task chains, Bronze append-only semantics, Silver/Gold
partition behavior, and `ops` contracts remain unchanged.

## 8. Source references

- [Accepted coursework](../coursework.md)
- [System-wide architecture](../system-architecture.md)
- [ADR-010](adr/adr-010-llm-only-scope-and-platform-simplification.md)
- [the platform requirements](requirements.md)
- [Evidence contract](evidence-contract.md)
- [Submission reviewer index](../submission/README.md)
