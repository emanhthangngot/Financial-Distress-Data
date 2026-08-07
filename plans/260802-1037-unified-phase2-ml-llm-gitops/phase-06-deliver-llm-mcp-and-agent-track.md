---
title: "Phase 6: Deliver LLM, MCP and agent track"
status: todo
estimate: "3.5 days (days 3-4 plus day 5, day 6 afternoon)"
---

# Phase 6: Deliver LLM, MCP and agent track

# Overview

Deliver the LLM track — the only track in the submission scope. Two FastAPI
services exposed as MCP tools, a KServe-served and benchmarked custom model
server behind an llm-d router, a global kagent `ModelConfig`, three agents in a
restricted sandbox with KEDA HTTP autoscaling, an agent registry with its UI,
the agent chat UI behind authentication and a rate limit, full observability,
and the verification gates.

Rewritten twice. The 2026-08-07 morning rewrite (7-day LLM-only scope) dropped
KServe `LLMInferenceService`, Knative, llm-d and Envoy AI Gateway because k3d on
a 16 GB rented VM made them a full day of CRD risk. The 2026-08-07 afternoon
rewrite **restores all four**: the evidence plane moved to GKE
(`phase-03-bootstrap-gitops-and-aws-evidence-platform.md`), which has ~43 GB
allocatable, so the reason for the cut is gone. Restoring them converts
canonical row 2 (2 pts) — which links a specific KServe/llm-d deployment guide —
from *at risk* to *satisfied as written*. See `## Scope Changes`.

## Rubric Coverage — all 60 LLM rows, 100 points

| Section | Pts | Phase | Day |
|---|---:|---|---|
| Routing & Gateway — metric viewer behind the gateway (2), domain + HTTPS for the Web API kéo dữ liệu (1) | 3 | P3 | 1 |
| IaC — Terraform (1), Ansible role (1) | 2 | P3 | 1, 6 |
| Repository Design — clean code, clean repo, design patterns | 2 | P3/P7 | 1, 5 |
| Security — centralize secret management | 1 | P3 | 1 |
| RAG — data pipeline (2), data governance (2) | 4 | P4 | 2 |
| Improve the Data Generator — simulate drift (1), label table (2), generator config (1) | 4 | P4 | 2 |
| CI/CD — RAG pipeline (2), Job 1 offline (2), Job 2 online (2) | 6 | P4 | 2 |
| Web API kéo dữ liệu user + chunk — FastAPI/pydantic (1), async (1), MCP tool on k8s with helm + rollingupdate + auto fallback (2), agent using it multi-replica + autoscale (2), agent in sandbox (1), publish agent to registry (2) | 9 | **P6** | 3, 4 |
| Web API real-time drift detection — same six-row shape | 9 | **P6** | 3, 4 |
| LLM inference platform — deploy platform + gateway (2), custom model (2), benchmark + optimize (2) | 6 | **P6** | 3, 4 |
| Global model config | 2 | **P6** | 3 |
| Agent registry | 2 | **P6** | 4 |
| Coordinator agent — coordinate 2 agents (2), publish to registry (2) | 4 | **P6** | 4 |
| Routing & Gateway — UI to test agent (2), UI for agent registry (2), basic auth **and rate limit** at the gateway for that UI (2), log viewer (2), trace viewer (2) | 10 | **P6** | 2, 4 |
| Observability — Prometheus + Grafana (1), token metrics + round-trip (2), agent/MCP-call/failure counts (2), logs (1), traces (1), Web API metrics (1) | 8 | **P6** | 2, 5 |
| CI/CD — agent kéo dữ liệu (2), agent drift detection (2), agent coordinator (2) | 6 | **P6** | 5 |
| Validation & Verification — equivalence/boundary (2), mutation with mutmut (2), property-based idempotency (2), Locust HTML (2), base row (1) | 9 | **P6** | 5 |
| Demonstrate understanding of Agents — 2 Jupyter notebooks | 4 | **P6** | 6 |
| Warm-up mode | 2 | **P6** | 6 |
| A/B testing — two LLM versions (1), A/B before replacing a model (1) | 2 | **P6** | 6 |
| Novel ideas — idea 1 (2), idea 2 (2) | 4 | **P6** | 6 |
| Documentation | 1 | P8 | 7 |
| **Total** | **100** | | |

Phase 3 buys 8, phase 4 buys 14, phase 8 buys 1, this phase buys 77.

## Honest Point Budget

A full 100/100 is reachable. Restoring the KServe/llm-d chain removed the single
highest-risk item from the previous budget (row 2). Expect **95-99/100**. At
risk and why:

| Canonical row | Pts | Risk | What makes it land |
|---|---:|---|---|
| Row 4 — *Benchmark model server and optimize* | 2 | Medium | The optimization must be non-trivial with a real before/after table (quantization, batching, or KV cache) |
| Row 26 — *Unit test coverage > 90%* | 1 | Medium | A hard gate, not a preference. Evidence must show the coverage figure **and** fixture/mock usage on the Web API tests |
| Row 46 — *Setup domain & enable HTTPS* | 1 | Low | Free DuckDNS subdomain + cert-manager ACME HTTP-01 on the GKE LoadBalancer, done in phase-03 day 1 — no longer tied to a forfeitable session |
| Row 47 — *Terraform* | 1 | Low | Terraform-against-GCP is now the day-1 main path, not a timeboxed side session; risk is only a `terraform apply` failure |

Row 2 (*Deploy a LLM inference platform theo hướng dẫn này*, 2 pts) moved off
this table: KServe `InferenceService` + Knative Serving + an llm-d router is the
literal stack the row's linked guide describes, so this is satisfied as written
rather than by substitution.

Rows 3 (custom model), 5 (global `ModelConfig` through agentgateway), 6 (agent
registry), 13 and 19 (sandbox) are **not** at risk: the plan keeps kagent,
agentgateway and agentregistry, and the canonical sandbox wording is
`giới hạn quyền thông qua Sandbox`, which the restricted-PSS namespace satisfies
on its own terms.

Say this out loud now rather than discovering it on day 7.

## Architecture

**Inference platform.** Knative Serving hosts the KServe **`InferenceService`**
for the custom model server (vLLM-CPU or llama.cpp, OpenAI-compatible shim,
Qwen2.5 0.5B-1.5B class — the rubric asks for a benchmarked custom server, not
GPU-class throughput). An **llm-d router** sits in front of it for
request-aware routing. This is the literal chain canonical row 2's guide
describes; phase-03 installs the Knative/KServe operators, this phase deploys
the `InferenceService` onto them.

**Model chain.** kagent `Agent` → kagent `ModelConfig` → agentgateway AI backend
→ the KServe `InferenceService` above. Negative tests block an agent from
calling the model server directly, bypassing agentgateway.

**Autoscale.** A KEDA HTTP `ScaledObject` drives request-based autoscaling for
the model server and both MCP-backed agents, in addition to the Kubernetes HPA
already used for the FastAPI services. Request-driven scaling is stronger
evidence for rows 12/18/23 (multi-replica + autoscale) than CPU-only HPA alone.

**Benchmark and optimization.** Baseline versus optimized settings, measuring
TTFT, inter-token latency, throughput, and memory. The optimization is a real
one — quantization, batch size, or KV-cache configuration — with a before/after
table.

**MCP boundary.** Both Web APIs are generic FastAPI services. The MCP server is
a thin wrapper that validates scoped tool requests, authorizes agent and tool
identity, enforces timeouts and budgets, and emits traces. Business logic never
lives in the MCP layer — phase-05's retrofit depends on this.

**Sandbox.** A dedicated `agents-sandbox` namespace, not a product install:

- `pod-security.kubernetes.io/enforce: restricted` on the namespace
- ServiceAccount with no RoleBinding and `automountServiceAccountToken: false`
- `securityContext`: `runAsNonRoot`, `readOnlyRootFilesystem`,
  `capabilities.drop: [ALL]`, `seccompProfile: RuntimeDefault`
- default-deny NetworkPolicy, egress allowed only to the MCP gateway and the
  model service
- CPU and memory limits

Evidence is the manifest plus three negative demonstrations from inside an agent
pod: `kubectl get secrets` → 403; `curl https://example.com` → blocked;
`touch /x` → read-only filesystem. Name it accurately in the evidence file
("namespace-scoped Kubernetes sandbox: restricted PSS, default-deny egress,
tokenless ServiceAccount"). Do not label it as the kagent Agent Sandbox product
if that product was not installed — phase-08's entire contract is that
"designed", "configured", "executed" and "passed" stay distinct.

**UIs.** Reuse `apps/web` (delivered in phase-02) for the agent chat route and
the agent registry route. Chat shows the agent and tool trace plus citations;
the registry shows version, status, replicas, model config, sandbox policy and
promotion history. Authentication **and a rate limit** on the chat UI are their
own scored row (canonical row 45, 2 pts) — an auth-only setup is incomplete.

**Observability.** Prometheus + Grafana for metrics, Loki + Grafana Explore for
logs (the log-viewer row says "ví dụ Kibana" — an example, not a requirement),
Jaeger all-in-one for traces, each exposed as its own gateway-reachable route
(canonical rows 40/41/42). Required metrics: input/output/total token counts
per request, total round-trip time per generation, per-agent call counts, per
MCP-tool call counts, failure counts per call, and Web API metrics.

## Design Contracts

- `RagRetrievalService`: resolves scoped vector queries with provenance and
  enforces access class.
- `EmbeddingRegistryService`: records model/vector compatibility and performs a
  zero-downtime embedding-version swap.
- `McpToolService`: validates scoped tool requests, authorizes agent and tool
  identity, enforces timeouts and budgets, emits traces.
- `AgentOrchestrationService`: coordinates specialist agents with bounded hops,
  citation checks, and a deterministic failure policy.
- `AgentReleaseService`: registers, warms, promotes and rolls back agent and
  model configurations through GitOps.

## Related Code Files

- Create: `src/llm/api/` (feature/RAG retrieval service), `src/llm/mcp/` (both MCP wrappers)
- Create: `src/llm/agents/` (feature analyst, drift analyst, coordinator)
- Create: `src/drift/api/` (real-time drift service) — shared with the deferred ML track
- Modify: `src/llm/contracts.py` (implement the stubs)
- Modify: `apps/web` (agent chat route, agent registry route, auth, rate limit)
- Create (GitOps): `charts/feature-mcp/`, `charts/drift-mcp/`,
  `platform/inference/model-server.yaml` (KServe `InferenceService`),
  `platform/inference/llm-d-router.yaml`, `platform/agents/global-model-config.yaml`,
  `platform/agents/agentregistry.yaml`, `platform/agents/agent-sandbox.yaml`,
  `platform/agents/warm-pool.yaml`, `platform/agents/keda-scaledobject.yaml`,
  `platform/llm/ab-testing.yaml`, `platform/observability/prometheus-values.yaml`,
  `platform/observability/loki-otel-values.yaml`
- Create: `notebooks/` (two agent-understanding notebooks)
- Create: `tests/phase2/requirements/test_llm_ac_01..20.py` (generated in phase-03, filled here)

## Implementation Steps

### Day 2 (shared with phase-04) — observability stack, gateway routes

1. Seed failing tool-contract, sandbox, authorization, registry, citation,
   warm-up, autoscale, A/B, idempotency and gateway-route tests.
2. Deploy Prometheus, Grafana, Loki and Jaeger through Argo. Expose **three**
   viewer routes through the gateway — Grafana (metrics), Loki via Grafana
   Explore (logs), and Jaeger (traces). Canonical rows 40, 41 and 42 score
   these separately at 2 points each; installation without a reachable route
   scores nothing.

### Day 3 — inference platform, model chain, FastAPI services

3. Deploy the KServe `InferenceService` for the model server onto the
   Knative/KServe operators phase-03 installed, and put the llm-d router in
   front of it. Create the agentgateway route to the router. Create the global
   kagent `ModelConfig` pointing at the agentgateway AI backend, and reference
   it from every agent. Add negative tests proving an agent cannot reach the
   model server directly.
4. Run the baseline benchmark: TTFT, inter-token latency, throughput, memory
   and cost, against the unoptimized `InferenceService`.
5. Build both FastAPI services: async, Pydantic-validated, `/healthz` and
   `/readyz`, structured errors. One parameterized Helm chart with per-service
   values. Prove `helm upgrade --install --atomic`, a rolling update, and
   automatic fallback on a bad revision.

### Day 4 — optimization, MCP, agents, registry, UIs

6. Apply the optimization (quantization, batch size, or KV-cache configuration)
   and re-run the benchmark. Record the before/after table — this is the row-4
   deliverable.
7. Apply the KEDA HTTP `ScaledObject` to the model server and both agents.
   Load-test past the request threshold and capture replica/latency evidence.
8. Deploy both MCP servers wrapping the day-3 FastAPI services, with service
   accounts, rate and timeout limits, and structured tool errors.
9. Deploy the feature analyst and drift analyst agents with multi-replica
   autoscaling, then the coordinator with bounded fan-out and hop limits. Apply
   the `agents-sandbox` namespace policy and capture the three negative
   demonstrations.
10. Deploy the agent registry and publish all three agents to it.
11. Wire the `apps/web` agent chat route (agent/tool trace plus citations) and
    the agent registry route. Apply **basic authentication and a rate limit** at
    the NGINX gateway for the chat UI — canonical row 45 names both, so an
    auth-only setup is incomplete.

### Day 5 — CI/CD, verification, notebooks lead-in

12. Add three GitHub Actions workflows — agent kéo dữ liệu, agent drift
    detection, agent coordinator — each building, signing, pushing an immutable
    digest and opening the GitOps digest PR.
13. Generate the Locust HTML report against the Web API kéo dữ liệu, recording
    p95 latency, throughput, error rate, concurrency and test parameters.
14. Verification gates: parametrized equivalence-partition and boundary-value
    tests; Hypothesis property tests for idempotency; `mutmut` scoped to two or
    three small pure modules; coverage >90% with fixture/mock proof on the Web
    API tests.

### Day 6 (afternoon, shared with phase-07/08) — warm-up, A/B, notebooks, novel ideas

15. Warm-up mode: minimum warm capacity during the evidence window, scale-down
    outside it. Measure cold versus warm startup and TTFT and record the cost
    difference plus the replica spread.
16. A/B test two model versions on the inference platform and two agent model
    configs. Dashboard TTFT, latency, tokens, failures and cost.
17. Write the two Jupyter notebooks demonstrating an agent interacting with both
    MCP servers to pull data from the feature store and for RAG.
18. Implement and prove the two novel ideas (below).
19. Fill the 60 assertions in `tests/phase2/requirements/test_llm_ac_01..20.py`
    so every row's exact `validation_command` selects an assertion for that row,
    not only the shared metadata contract test.

## Novel-Idea Proof

- **Embedding-version hot swap:** dual-read validation and an alias change
  produce no downtime and no mixed-vector query.
- **Citation/PII guard:** unsupported or sensitive output is blocked or
  rewritten, and the decision is linked to its OpenTelemetry trace and the
  evidence manifest.

## Test Gates

- Every row's exact `validation_command` exits 0 and selects at least one
  assertion.
- Equivalence-partition and boundary-value parametrized tests for input schema,
  missing or unknown ticker, timestamp edges and API limits.
- Hypothesis idempotency tests for repeated retrieval and tool invocation.
- Locust HTML with the recorded SLA fields.
- **Unit test coverage >90% — a scored row (canonical LLM CSV row 26, 1 pt),
  not a self-imposed bar.** Its declared proof is a screenshot showing Web API
  tests that use fixtures and mocks, so the evidence must show both the
  coverage figure and the fixture/mock usage.
- `mutmut` executed on a declared subset of modules, with its score recorded.
  Only the ">80% mutation score" threshold is retired — canonical row 28 asks
  that mutation testing be used, not that a score be reached.

## Success Criteria

- [ ] Reviewer -> inspects the `InferenceService` and llm-d router -> sees a versioned model and config, a repeatable benchmark, and a quantified before/after optimization.
- [ ] Load tester -> drives traffic past the KEDA threshold against the model server and both agents -> observes independent scale-out/scale-in with captured replica/latency evidence.
- [ ] Registered coordinator -> calls both specialist agents -> receives cited feature-store and drift results through the sandboxed MCP tools within its hop bound.
- [ ] Agent pod -> attempts `kubectl get secrets`, an external `curl`, and a filesystem write -> is denied on all three, with the manifest as corroborating evidence.
- [ ] Analyst -> opens the agent chat UI -> is challenged for authentication and observes a rate limit, then sees citations and agent/tool status; registry viewer -> opens the separate registry UI -> sees governed releases and replicas.
- [ ] Load tester -> compares cold and warm agent modes -> sees improved startup and TTFT with a documented cost difference.
- [ ] Platform observer -> opens Grafana -> finds token counts, round-trip time, per-agent and per-MCP-tool call counts, failure counts, and Web API metrics; opens the trace viewer and the log viewer through the gateway -> both are reachable.
- [ ] Load tester -> runs Locust against the Web API kéo dữ liệu -> receives an HTML report meeting the recorded SLA.
- [ ] Test runner -> executes all 20 LLM requirement files -> every one of the 60 node selections exits 0.

## Scope Changes

| Restored 2026-08-07 | Reason it was cut | Reason it is back |
|---|---|---|
| KServe `InferenceService`, Knative Serving, llm-d router | k3d on a 16 GB rented VM made CRD install a full-day risk | Evidence plane is now GKE with ~43 GB allocatable (phase-03); this is the literal stack canonical row 2's guide describes |
| KEDA HTTP `ScaledObject` | Not previously considered | Stronger request-driven autoscale evidence for rows 12/18/23 than CPU-only HPA |

| Still dropped | Substituted with | Rubric cost |
|---|---|---:|
| Qwen3-4B LoRA fine-tune | Small instruction-tuned model, CPU-served, with a real optimization benchmark | 0 (the row asks for a custom model server, not a fine-tune) |
| Envoy Gateway, Envoy AI Gateway | agentgateway | 0 — agentgateway is the gateway the agent rows name |
| Agent Sandbox product install | `agents-sandbox` restricted-PSS namespace with negative proofs | 0 |
| ECK / Kibana | Loki + Grafana Explore | 0 |
| Istio mTLS and authorization | NGINX Ingress edge, ClusterIP-only backends, default-deny NetworkPolicy | 0 |
| GPU host | CPU host | 0 — free-trial GPU quota is 0, and row 4 asks for benchmark + optimization, not throughput |
| ">90% coverage, >80% mutation score" gate | Coverage 90% stays (it's a scored row); only the mutation-score threshold is self-imposed and retired | 0 |

## Risk Assessment

- **Knative/KServe install eats time on day 3.** Mitigated by installing the
  operators in phase-03 (before this phase starts) and by keeping the fallback
  path documented: plain vLLM-CPU behind agentgateway, which is where this plan
  stood before the restore, costs ~2 points if it must be invoked.
- **60 subprocess validation commands are slow.** Mitigated by keeping the
  requirement tests import-light; a single heavy import multiplies across all
  60 and can blow the day-7 wall clock.
- **`mutmut` 3.x changed its CLI and cache format** relative to the 2.x
  documentation. Mitigated by scoping it to two or three small pure modules and
  trying it on day 5 with a timebox.
- **Agent chat UI authentication and rate limiting** touch `apps/web`, which is
  already delivered. Mitigated by adding a route guard and a rate-limit
  middleware rather than reworking the shell.
- **Days 3-4 are the heaviest in the plan** (~13h absorbed Tier-1 scope). If
  either slips, cut warm-up (row 25, day 6) and A/B (row 16, day 6) first —
  never the test suite or observability, which carry more points across more
  rows.
- Rollback: Git-revert the agent or model configuration commit; prior registered
  versions stay in the registry; no production alias is mutated without an audit
  event.
