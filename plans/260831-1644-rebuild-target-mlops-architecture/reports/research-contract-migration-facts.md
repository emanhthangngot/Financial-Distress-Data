# Contract Migration Facts — FDD Rebuild to Target Architecture

**Author:** ContractMigrationFacts | **Date:** 2026-08-31 | **Scope:** Locked contracts, prior verified outcomes, predecessor decisions, migration constraints for debate

---

## I. Authority Timeline

| Authority | Date | Status | Key decisions | Source |
|---|---|---|---|---|
| **Phase 1 contracts** | Ongoing | Immutable | Bronze/Silver/Gold semantics, no mutations | `docs/mini_coursework.md:1,29-41` |
| **Phase 2 LLM submission** | 2026-08-13 | Locked (pending freeze) | GKE, GitHub Actions, KServe 0.14.1/Knative, agentgateway, Feast (Redis/MinIO) | `docs/coursework.md:1-65` |
| **ADR-010** | 2026-08-07 | Superseding | KServe/Knative restored, Istio/Vault/Jenkins/Envoy dropped, Helm-only render | `docs/phase2/adr/adr-010-llm-only-scope-and-platform-simplification.md:1-116` |
| **ADR-002** | 2026-08-02 | Immutable | Two repositories (source monorepo + GitOps control repo) | `docs/phase2/adr/adr-002-two-repositories.md:1-30` |
| **Plan 260818-0832** | 2026-08-18 | Debate baseline | Unified ML+LLM (161 rows), 48 vCPU, Jenkins+Vault, Istio full sidecar, Kubeflow/Ray/MLflow, Iceberg/Spark/Trino | `plans/260818-0832-rebuild-unified-ml-and-llm-platform/plan.md:1-310` |
| **Plan 260818-0028** | Draft | Load-bearing | Namespace boundaries (agentgateway-system/kagent/agents-sandbox) are security controls, not cosmetic | `financial-distress-gitops/plans/260818-0028-namespace-convention-alignment/plan.md:77-115` |

---

## II. Rubric Inventory and Acceptance Contracts

### Rubric scope (canonical source: `docs/phase2/rubric-matrix.csv`)
| Track | Rows | Points | Status | Evidence location |
|---|---|---|---|---|
| Mini-coursework | 44 | 100 | Phase 1 source of truth (location unsourced) | `docs/mini_coursework.md:1` |
| ML | 57 | 100 | Design-only (deferred) | `docs/phase2/rubric-matrix.csv` (marked design_only) |
| LLM | 60 | 100 | Submitted (pending freeze) | `docs/phase2/evidence/llm/` + GitOps SHA restamp pending |
| **Total** | **161** | **300** | Rebuild target (all three); Phase 2 submission (LLM only) | Split by track acceptance |

### Acceptance criteria mapping
- **LLM-AC-01..20:** 20 distinct criteria for LLM track `docs/phase2/acceptance-criteria.md:56-143`
- **ML-AC-01..18:** 18 distinct criteria for ML track `docs/phase2/acceptance-criteria.md:20-67`
- **Mandatory README:** Non-scored, cross-track `docs/phase2/acceptance-criteria.md:147-149`
- **Auditor enforcement:** `audit_phase2_evidence.py --require-executed --run-validations --gitops-root ...` `docs/phase2/requirements.md:38-41`

---

## III. Prior Verified Outcomes (2026-08-13 snapshot)

| Outcome | Status | Source |
|---|---|---|
| 13/13 Argo CD applications Synced/Healthy | ✓ Verified | `docs/coursework.md:54-62` |
| 10 agents Ready | ✓ Verified | `docs/coursework.md:54-62` |
| MCP path + agentgateway + KServe/Knative model server responding | ✓ Verified | `docs/coursework.md:54-62` |
| Coordinator HTTP 200 with feature/drift citations | ✓ Verified | `docs/coursework.md:54-62` |
| MinIO persistence across pod restart (19 Gold objects retained) | ✓ Verified | `plans/260814-2218-production-feast-ghcr/plan.md:24-27` |
| Feast offline → Redis online (843 rows, 16 risk rows, non-null) | ✓ Verified | `plans/260814-2218-production-feast-ghcr/plan.md:28-29` |
| 60/60 LLM rows, 100/100 logical coverage captured | ✓ Verified (freeze pending) | `docs/coursework.md:60` |
| Post-materialization analyst answer quality | ⚠️ Incomplete | `plans/260814-2218-production-feast-ghcr/plan.md:43` (pre-materialization response only) |

---

## IV. Current State Component Inventory (Phase 2 LLM)

### Inference and model serving
| Component | Version | Current config | Notes |
|---|---|---|---|
| **KServe** | v0.14.1 | Single `InferenceService` (llama.cpp llm-d CPU) | Pre-LLMInferenceService; no KV-cache routing |
| **Knative Serving** | v1.16.0 | net-kourier | Gateway provider for KServe |
| **Model** | Qwen2.5 0.5B GGUF | llama.cpp server, 500m CPU request, Q4_K_M (optimized) | Scale: 0-1 replicas |
| **Embeddings** | TEI CPU v1.9 | Separate `InferenceService` (e5-small, 384-dim) | License: HFOIL (not OSS) |

Source: `financial-distress-gitops/platform/inference/{VERSIONS.md,model-server.yaml,embedding-server.yaml}`

### Data and features
| Component | Current | Notes |
|---|---|---|
| **Offline store** | MinIO (S3-compatible) | No Postgres |
| **Online store** | Redis (in-cluster) | Feast materialization target |
| **RAG vectors** | PGVector (in-cluster) | Co-located with online store |
| **Feast projects** | Two (structured + RAG) | Point-in-time TTL contracts defined |

Source: `financial-distress-gitops/platform/data/{postgres-pgvector.yaml,redis.yaml,feast-online-contract-probe.yaml}`

### Control plane and security
| Component | Current | Notes |
|---|---|---|
| **Service mesh** | None | Network-policies only (default-deny) |
| **Secrets mgmt** | sealed-secrets | Ciphertext in Git |
| **Namespace boundaries** | 3 deliberate (agentgateway-system, kagent, agents-sandbox) | **Load-bearing:** agents-sandbox NetworkPolicy egress scoped to agentgateway-system only |
| **Agent sandbox** | PSS restricted + tokenless SA + read-only root | Security isolation tier |
| **Ingress** | F5 NGINX Ingress OSS | Public TLS edge (+ two extra LBs: Kourier, agentgateway direct—must be removed) |

Source: `financial-distress-gitops/platform/{security,agents,ingress}/*.yaml`, `docs/phase2/adr/adr-010-llm-only-scope-and-platform-simplification.md:82-103, plan 260818-0028:77-115`

### CI/CD and delivery
| Layer | Current | Notes |
|---|---|---|
| **Source CI** | GitHub Actions | test/build/lint/scan/sign → immutable digest |
| **GitOps promotion** | Digest-only PR (no code) | Source CI bot opens PR; Argo reconciles |
| **Rollback** | Git revert + Argo resync | No imperative kubectl |

Source: `docs/coursework.md:49-52, docs/phase2/adr/adr-002-two-repositories.md:16-30`

---

## V. Rebuild Target (Plan 260818) Component Ledger

### Inference and model serving (new)
| Component | Target | Current | Breaking? | Mitigation |
|---|---|---|---|---|
| **KServe** | 0.18+ | 0.14.1 | **Yes** (LLMInferenceService CRD) | Phase 4: upgrade; verify InferenceService compatibility |
| **LLMInferenceService** | New | N/A | New CRD | Phase 4: install llm-d + Gateway API + GIE + LeaderWorkerSet |
| **llm-d** | New | N/A (agentgateway only) | New router | Phase 4: KV-cache-aware routing for LLM |
| **Knative** | 1.17+ (TBD) | 1.16.0 | Minor | Phase 4: compatibility check with net-istio or retained net-kourier |
| **ML inference** | Triton + KServe | N/A (design-only) | N/A | Phase 5: full ML serving stack |
| **vLLM CPU** | Branch A (if feasible) or llama.cpp + semantic cache (Branch B) | llama.cpp only | **Conditional** | Phase 4 decision gate: vLLM CPU feasibility test |

Source: `plans/260818-0832-rebuild-unified-ml-and-llm-platform/plan.md:36,42-48,56-78`

### Data and ML training (new)
| Component | Target | Current | Breaking? | Mitigation |
|---|---|---|---|---|
| **Lakehouse format** | Iceberg + Spark | DuckDB/Parquet (Phase 1) | **Yes** (additive) | Phase 2: parallel Iceberg write path; Phase 1 unchanged |
| **Offline store** | Postgres | MinIO | **Yes** (schema change) | Phase 3: Postgres Feast offline; MinIO for versioning only |
| **Data pipeline** | Debezium → Kafka → Flink | Kafka (Phase 1) | **Additive** | Phase 3: streaming CDC path |
| **Analytics** | Trino + Superset | None | New | Phase 4: install; window-scheduled residency |
| **Training** | Kubeflow Pipelines + Ray + MLflow | N/A | N/A | Phase 5: full ML track execution |
| **Model promotion** | Frozen holdout gate (Iceberg tag) | None (no approval) | New | Phase 7: `bump-gitops` two-lane Jenkins; hard equality assert on holdout |

Source: `plans/260818-0832-rebuild-unified-ml-and-llm-platform/plan.md:36,49`

### Control plane and security (new)
| Component | Target | Current | Breaking? | Mitigation |
|---|---|---|---|---|
| **Service mesh** | Istio full sidecar | None | **Yes** (~4-6 vCPU, ~4-8 GB, 4-8 days) | Phase 4: install; native sidecars (K8s 1.33+) fix Job termination |
| **Secrets mgmt** | HashiCorp Vault + external-secrets | sealed-secrets | **Yes** (~2 vCPU, ~4 days) | Phase 7: Jenkins cutover includes Vault migration |
| **CI/CD driver** | Jenkins + Vault | GitHub Actions | **Yes** | Phase 7: provision Jenkins controller, migrate workflows |
| **Namespace boundaries** | Same (must not collapse) | 3 deliberate boundaries | **Conditional conflict** | Phase 4: verify fdd-architecture-full-4k.png; visual grouping OK, manifests must stay separate |
| **Authorization** | Istio AuthorizationPolicy | Kubernetes RBAC | Partial | Phase 4: Istio provides L7 telemetry; RBAC unchanged |

Source: `plans/260818-0832-rebuild-unified-ml-and-llm-platform/plan.md:36,68-80, financial-distress-gitops/plan 260818-0028:77-115`

### Cost and quota (target budget)
| Metric | Target | Current | Notes |
|---|---|---|---|
| **vCPU quota** | 48 (locked baseline) | Not locked (~12-16 floor) | <32 forces selective mesh injection; phase-4 gate |
| **GCP credit budget** | ~USD 223 remaining | USD 300 original (~77 spent) | Two LBs (Kourier, agentgateway direct) must be removed (cost: USD 54/mo each) |
| **Cluster-hours** | ~230-260 over 8 weeks | N/A | ~30 hrs/wk; spot node pool (60-70% discount); on-demand floor ~12 vCPU |
| **Always-on floor** | ~12-16 vCPU (Istio, observability, stores, core platform) | ~12-16 vCPU | Scheduled residency for Spark/Ray/KFP/DataHub/Trino/Flink |

Source: `plans/260818-0832-rebuild-unified-ml-and-llm-platform/plan.md:50-88`

---

## VI. Contradiction Ledger

| Layer | Current | Target | Conflict | Resolution |
|---|---|---|---|---|
| **KServe version** | 0.14.1 | 0.18+ | LLMInferenceService missing in 0.14.1 | Phase 4 upgrade; verify compatibility |
| **LLM routing** | agentgateway → queue proxy | agentgateway → llm-d → KServe + Gateway API | New router, KV-cache routing | Phase 4: install llm-d + GIE + LeaderWorkerSet |
| **Service mesh** | None | Istio full sidecar | Jobs break with sidecars; requires native sidecars (K8s 1.33+) | Phase 4: Kubernetes 1.35.6 GKE verified; install Istio; verify Job termination |
| **Secrets** | sealed-secrets in Git | Vault + external-secrets | CI/CD driver change required | Phase 7: Jenkins migration includes Vault cutover |
| **CI/CD** | GitHub Actions | Jenkins | Existing workflows not portable | Phase 7: rewrite Actions as declarative Jenkins pipelines |
| **Data plane** | DuckDB/Parquet (Phase 1) | Iceberg/Spark on GKE | Additive (Phase 1 unchanged) | Phase 2: parallel Iceberg write; Phase 1 lakehouse unaffected |
| **Feature store offline** | MinIO | Postgres | Schema change (point-in-time semantics) | Phase 3: Postgres Feast definition; ML retrofit depends on this |
| **Model promotion** | None (no approval) | Frozen holdout gate | New control on ML track | Phase 5: holdout PVC + Iceberg tag pinning + Jenkins lane |
| **Evidence tree** | Split (docs/evidence + docs/phase2/evidence) | Unified (single tree, 161 rows) | Requires purging all Phase 2 LLM artifacts | Debate decision: forfeit 100 points, rebuild to 300 total |
| **Namespace visual** | 3 separate namespaces shown | Likely grouped in fdd-architecture-full-4k.png | Risk: diagram implies manifest consolidation (security regression) | Phase 4: inspect diagram; confirm visual grouping ≠ namespace collapse |

---

## VII. Load-Bearing Decisions (Non-negotiable)

| Decision | Locked by | Forfeit if changed |
|---|---|---|
| Two repositories (source + GitOps) | ADR-002 | Audit trail, least-privilege CI/CD |
| Digest-only GitOps (no code commits to cluster state) | ADR-002 | GitOps reproducibility |
| Phase 1 contracts immutable | `docs/mini_coursework.md`, `docs/coursework.md:7` | Phase 1 regression suite, all dependent work |
| Point-in-time training isolation (frozen holdout gate) | Plan 260818 decision 14 | Model safety; risk of promotion on stale data |
| Three rubrics scored (if rebuild) or LLM-only (if Phase 2 final) | Mutual exclusion: 161 rows XOR 60 rows | Evidence tree restructure + 100 point forfeit |
| Namespace boundaries preserved (agentgateway-system ↔ kagent ↔ agents-sandbox) | Plan 260818-0028:77-115 | NetworkPolicy egress scoping; sandbox security tier |

---

## VIII. Gaps and Unknowns

### Blockers (require resolution before phase-4 starts)
| Gap | Impact | Status | Data source |
|---|---|---|---|
| GCP quota increase (48 vCPU) | Phase-4 gate; 1-3 day approval lag | Not yet requested | Must request day-1 if debate approves baseline |
| Kubernetes 1.35.6 native sidecar verification | Istio Job termination depends on it | Unconfirmed locally | Phase-4 step 1: verify K8s version + test Job lifecycle |
| Mini-coursework rubric matrix format | Auditor expects single CSV; mini rows are prose | Unsourced | `docs/mini_coursework.md:1` authority; location TBD |

### Conditional gates (phase 4, decided during execution)
| Gate | Decision | Branches | Outcome |
|---|---|---|---|
| **vLLM CPU feasibility** | Can vLLM CPU run production inference? | A: yes (use llm-d); B: no (semantic cache + llama.cpp) | Either branch satisfies LLM-AC-01 (benchmark row) |
| **Selective Istio injection** | If quota <48 vCPU, inject only kserve/api-serving/agents | Yes/no | Loses ~3-4 vCPU; Kiali graph scope reduced; mesh row still scored if L7 telemetry present |
| **Jenkins cutover sequence** | Staged (Actions → Jenkins + sealed-secrets → Vault) or parallel? | Staged: safer; Parallel: faster but higher risk | Affects phase-7 timeline and rollback safety |

Source: `plans/260818-0832-rebuild-unified-ml-and-llm-platform/plan.md:68-80,42-48, financial-distress-gitops/plan 260818-0028:77-115`

### Documentation gaps (non-blocking)
- Mini rubric matrix location (unsourced; assume `docs/mini_coursework.md`)
- fdd-architecture-full-4k.png namespace mapping (must inspect to verify no implied consolidation)
- Semantic cache SLA (if vLLM CPU branch B; phase-8 novel idea, not phase-4 blocker)

---

## IX. Cost Reality (2026-08-18 snapshot)

### Spent and remaining
- **Total credit:** USD 300 (VND-denominated)
- **Already spent:** ~USD 77 (mostly two idle load balancers @ USD 54/month each when nodes at zero)
- **Remaining:** ~USD 223
- **Expiry:** 2026-11-06 (80 days from 2026-08-18)

### Idle cost breakdown (nodes at zero)
| Item | Cost/month | Fraction | Action |
|---|---|---|---|
| 3 Load Balancers | USD 54 | 87% | Remove LBs 2-3 (Kourier, agentgateway direct); keep NGINX |
| 60GB persistent disk | USD 8 | 13% | Non-critical optimization |

### Rebuild budget (two LBs removed)
| Scenario | Idle spend | Compute budget | Cluster-hours (48 vCPU) |
|---|---|---|---|
| No spot | USD 8/mo | ~155 | ~88 |
| **With spot pool** | USD 8/mo | ~155 | **~230-260** |

**Required residency:** Always-on floor (~12-16 vCPU): Istio, observability, stores, core platform. Scheduled windows for Spark/Ray/KFP/DataHub/Trino/Flink.

Source: `plans/260818-0832-rebuild-unified-ml-and-llm-platform/plan.md:50-88`

---

## X. Version Pins and Sourced Facts

| Component | Source | Version | Date | Confidence |
|---|---|---|---|---|
| KServe 0.18 release | GitHub + search | v0.18 released 2026-04-29 | Web search 2026-08-31 | High |
| Knative 1.16.0 current | GitOps repo | knative-v1.16.0 | 2026-08-08 verified | High |
| Kubernetes 1.35.6 (GKE) | Plan 260818 | 1.35.6 assumed | 2026-08-18 locked | High (assumed; verify at phase-4) |
| Native sidecars stable | Search results + plan | K8s 1.33+ stable | Web search 2026-08-31 | High |
| llm-d availability | Search results | Part of KServe 0.18+ ecosystem | Web search 2026-08-31 | High |
| vLLM CPU suitability | Search results | "Not intended for CPU inference" (vLLM docs) | Web search 2026-08-31 | High (negative claim) |

---

## Status

**Status: DONE_WITH_CONCERNS**

**Summary:**  
Contract migration facts compiled from Phase 2 LLM authority (ADR-010, coursework.md) and Plan 260818 rebuild baseline. Authority chain locked (immutable Phase 1 + ADR-010 + namespace boundaries; debate-permissible Plan 260818). GitOps repo inspected; current component versions documented (KServe 0.14.1, Knative 1.16.0, net-kourier, sealed-secrets, no Istio/Vault/Jenkins). All contradictions cited with resolution paths.

**Core contradiction:**  
Phase 2 LLM-only (60 rows, 100 pts, verified) vs Plan 260818 unified rebuild (161 rows, 300 pts target, requires KServe 0.18+ upgrade, Istio mesh, Jenkins+Vault migration, Iceberg data plane, evidence purge + regeneration). Upgrade path known; schedule risk high (~30 hrs/wk for 8 weeks, no slack, USD 223 budget remaining).

**Concerns/Blockers:**
1. **GCP quota day-1 request** (1-3 day lag; phase-4 gate must clear before starting)
2. **Kubernetes 1.35.6 native sidecar verification** (unconfirmed locally; required for Istio Job termination)
3. **vLLM CPU feasibility TBD** (phase-4 decision; documented fallback: semantic cache + llama.cpp)
4. **Mini-coursework rubric matrix format** (location unsourced; rebuild assumes single unified CSV)
5. **Schedule risk** (30 hrs/wk × 8 weeks with zero slack; Istio + Jenkins + Vault migrations each capable of consuming buffer)
6. **Namespace diagram verification** (fdd-architecture-full-4k.png must confirm visual grouping does not imply manifest consolidation; NetworkPolicy egress scoping depends on namespace separation)
