---
phase: 8
title: "Phase 8: LLM and agent track — KServe 0.18, llm-d, agent registry, warm mode"
status: pending
priority: P1
effort: "8-12 days"
dependencies: ["phase-00-gates.md", "phase-06-platform.md"]
owns: ["platform/inference/", "platform/serving/llm-*", "platform/agents/", "platform/agentgateway/", "src/agents/", "src/llm/"]
---

# Phase 8: LLM and agent track — KServe 0.18, llm-d, agent registry, warm mode

## Overview

Upgrade KServe 0.14.1 → 0.18 (pre-upgrade export first — **the one documented non-revertible step**);
deploy the llm-d Gateway (`GatewayClass: istio`, `ClusterIP`); configure `HTTPRoute` group `llm-ab`
with 9:1 weights; re-establish the agent plane inside the mesh; and re-earn the 60 LLM rubric rows
after the evidence purge. **Resident cost: 6-12 vCPU during serving windows.**

All 60 LLM rows are currently `executed` — the implementations exist. The evidence purge (locked
decision #1a) means they must be **re-captured**, not re-designed; all 60 retain
`validation_command` and `behavioral_assertion`. **Capture the LLM rows first in P12** (plan R-5).

Five of those rows are the agent-registry chain, which the previous plan's phase files never
mentioned:

| Row | Requirement | Points |
|---|---|---|
| LLM 6 | Deploy a registry for agents | 2 |
| LLM 14 | Publish the data-fetch agent to that registry | 2 |
| LLM 20 | Publish the drift-detection agent | 2 |
| LLM 24 | Publish the coordinator agent | 2 |
| LLM 44 | UI for the agent registry (behind NGINX — routed in P9) | 2 |
| LLM 25 | **Warm-up / standby mode** for agents, to cut cost and startup latency | 2 |

## Requirements

- Functional:
  - KServe 0.18 `LLMInferenceService` CRD live (G3 branch A) or ADR-004 branch B recorded.
  - The llm-d Gateway is `ClusterIP`; cluster-wide `LoadBalancer` count stays exactly one.
  - 100 requests through `HTTPRoute` group `llm-ab` split ≈ 90:10 across isvc-a / isvc-b.
  - A **global model config** applies across agents (LLM 5) and an **agent registry** is deployed
    with all three agents published to it.
  - Each agent runs **multi-replica with autoscale** and inside the sandbox.
  - **Warm-up / standby mode** measurably reduces cold-start latency.
  - Both LLM notebooks execute (LLM 21: agent ↔ MCP for feature pull + drift; LLM 22: agent ↔ MCP
    for RAG data).
  - The RAG Airflow pipeline runs text → chunk → embed → vector store with governance (LLM 7-8).
  - A model-server **benchmark** reports the G5-selected branch metrics (LLM 4).
  - Coordinator trace spans coordinator → MCP → api-serving → kserve.
- Non-functional: exactly one external `LoadBalancer` cluster-wide; `phase2-llm` dissolved; no Envoy
  Gateway components introduced; sandbox egress still scoped to `agentgateway-system` after injection.

## Architecture

```
ns: kserve
  KServe operator 0.18 + Knative Serving + net-istio
  Gateway (GatewayClass: istio, type: ClusterIP)
  HTTPRoute group llm-ab ──► isvc-a (w=9)   llm-d LLMInferenceService
                         ──► isvc-b (w=1)   llm-d LLMInferenceService
  LeaderWorkerSet multi-node serving
  GIE endpoint-picker
  mTLS STRICT + AuthorizationPolicy

ns: agents
  Coordinator Agent (kagent CRD)  ─┐
  Feature Agent                    ├─ multi-replica + autoscale, warm/standby pool
  Drift Agent                     ─┘
  agent registry  ← all three published; UI routed through NGINX in P9
  global ModelConfig

agents-sandbox ──► agentgateway-system ──► (only) kserve + api-serving
```

### Rollback exception (plan O-6)

The KServe CRD schema change is **not** reversed by git revert. Rollback = restore-from-export using
the pre-upgrade `InferenceService` dump captured as an **entry** artifact of this phase. This is the
only documented exception to the universal git-revert + Argo-resync boundary.

## Related Code Files

- Modify: `financial-distress-gitops/platform/inference/` — bump the chart to KServe 0.18; delete
  the vendored 0.14.1
- Modify: `platform/inference/VERSIONS.md` — record 0.18 and the entry-artifact path
- Create: `platform/serving/gateway.yaml` (`GatewayClass: istio`, `ClusterIP`)
- Create: `platform/serving/httproute-llm-ab.yaml` (weights 9:1)
- Create: `platform/serving/lws.yaml`, `platform/serving/llm-isvc-a.yaml`, `llm-isvc-b.yaml`
- Create: `platform/agents/registry.yaml`, `platform/agents/model-config.yaml`,
  `platform/agents/warm-pool.yaml`
- Modify: `src/agents/registry.py`, `runtime.py`, `coordinator.py`, `feature_agent.py`,
  `drift_agent.py`
- Modify: `src/llm/benchmark.py`, `rag_pipeline.py`, `citation_guard.py`, `data_governance.py`,
  `embedding_registry.py`
- Create: `notebooks/agent-feature-drift-demo.ipynb`, `notebooks/agent-rag-demo.ipynb`
- Restore from archive: `platform/security/authorization-policies.yaml` (kserve scope)
- Create: `reports/kserve-014-pre-upgrade-objects.yaml` (entry artifact)

## Implementation Steps

1. **Pre-upgrade export — required entry artifact** (0.5 d) —
   `kubectl get inferenceservice -A -o yaml` into
   `reports/kserve-014-pre-upgrade-objects.yaml`. **No upgrade step may start before this file exists.**
2. **KServe 0.18** (1-2 d) — bump the Helm chart; apply via Argo CD; verify the
   `LLMInferenceService` CRD is live, or record ADR-004 branch B.
3. **Gateway** (1 d) — deploy with `GatewayClass: istio` and `type: ClusterIP`; verify the
   cluster-wide `LoadBalancer` count is unchanged from pre-P8.
4. **A/B routing** (2 d) — `HTTPRoute` group `llm-ab` weights 9:1; isvc-a and isvc-b; load-test with
   1000 requests and confirm the split holds within 5 %.
5. **LeaderWorkerSet + GIE** (1 d) — multi-node serving and the endpoint picker.
6. **mTLS STRICT + AuthorizationPolicy in `kserve`** (0.5 d).
7. **Agent registry chain** (2 d) — deploy the registry; publish the feature, drift and coordinator
   agents; expose the registry UI Service (NGINX routing lands in P9); apply the global
   `ModelConfig` so all three agents resolve one model configuration.
8. **Warm / standby mode** (1 d) — configure a warm pool or `minReplicas`-with-scale-to-standby;
   measure cold-start latency before and after; capture both numbers.
9. **Agents into the mesh + sandbox re-test** (1 d) — inject; re-run the negative test
   (sandbox → kserve direct refused; via agentgateway succeeds).
10. **Notebooks** (1 d) — agent ↔ MCP for feature pull and drift detection; agent ↔ MCP for RAG data.
11. **RAG pipeline + governance** (1 d) — Airflow DAG text → chunk → embed → pgvector, with license /
    PII / quarantine governance.
12. **Benchmark + end-to-end** (1 d) — run the G5-selected branch benchmark; dissolve `phase2-llm`;
    verify the Jaeger trace spans coordinator → MCP → api-serving → kserve.

## Success Criteria

- [ ] AC-P8-1: Argo CD → syncs KServe 0.18 `platform-inference` → `VERSIONS.md` records 0.18 and the
      pre-upgrade export exists in `reports/` as a P8 **entry** artifact
- [ ] AC-P8-2: Platform operator → describes the llm-d Gateway → `GatewayClass` is `istio`, Service
      type is `ClusterIP`, and `kubectl get svc -A --field-selector spec.type=LoadBalancer` returns
      exactly one row, the NGINX ingress controller
- [ ] AC-P8-3 **(LLM 56)**: `HTTPRoute` group `llm-ab` → receives 1000 requests → routes ≈ 900 to
      isvc-a and ≈ 100 to isvc-b, within 5 % of the 9:1 weights
- [ ] AC-P8-4 **(LLM 5)**: Operator → updates the global `ModelConfig` → all three agents resolve the
      new model configuration without per-agent edits
- [ ] AC-P8-5 **(LLM 6, 14, 20, 24)**: Operator → queries the agent registry → the feature, drift and
      coordinator agents are all listed with their published versions
- [ ] AC-P8-6 **(LLM 12, 18, 23)**: Operator → describes each agent Deployment → replicas > 1 and an
      autoscaler is attached; load raises replica count and it returns to baseline
- [ ] AC-P8-7 **(LLM 13, 19)**: Sandbox negative test after injection → egress from `agents-sandbox`
      directly to `kserve` is refused; through `agentgateway-system` it succeeds
- [ ] AC-P8-8 **(LLM 25)**: Operator → enables warm/standby mode → measured cold-start latency is
      lower than the cold baseline; both numbers are captured
- [ ] AC-P8-9 **(LLM 21)**: Data scientist → runs `notebooks/agent-feature-drift-demo.ipynb` → the
      agent pulls features from Feast through MCP and performs drift detection
- [ ] AC-P8-10 **(LLM 22)**: Data scientist → runs `notebooks/agent-rag-demo.ipynb` → the agent pulls
      RAG data through MCP
- [ ] AC-P8-11 **(LLM 7-8)**: Airflow → runs the RAG pipeline → text → chunk → embedding → pgvector
      completes; license, PII and quarantine governance decisions are recorded in `ml.rag_quarantine`
- [ ] AC-P8-12 **(LLM 4)**: Engineer → runs the model-server benchmark on the G5-selected branch →
      reports TTFT, tokens/s and KV-cache hit rate (branch A) or quantization / thread-pinning /
      semantic-cache hit rate (branch B); the write-up cites only the branch actually run
- [ ] AC-P8-13: Coordinator agent → answers an analyst prompt → HTTP 200 with feature and drift
      citations; Jaeger shows a trace spanning coordinator → MCP → api-serving → kserve
- [ ] AC-P8-14: Platform operator → lists namespaces → `phase2-llm` no longer exists
- [ ] AC-P8-15 **(LLM 2)**: Argo CD → syncs the LLM inference platform → the serving stack is
      `Synced/Healthy` and a prompt sent to the platform endpoint returns a completion; the deploy
      procedure is written down so a reader can reproduce it from the repo alone
- [ ] AC-P8-16 **(LLM 3)**: Engineer → registers a **custom** model server (not the tutorial default)
      → it serves a completion through the same gateway, and the write-up states what was customized
      (image, runtime args, weights source) and why
- [ ] AC-P8-17 **(LLM 55)**: Operator → runs the same agent behind two different `ModelConfig`
      variants → both variants receive traffic, and their token cost, latency and answer quality are
      compared side by side in the artifact; the comparison names which variant won and on what metric

## Risk Assessment

**Risk (rollback exception):** the KServe 0.18 CRD upgrade is conditionally irreversible. Signal: the
upgrade fails mid-way with the CRD schema inconsistent. Mitigation: AC-P8-1's export is a hard
prerequisite, enforced as a phase entry gate. Response: restore from the export YAML; never attempt a
Helm rollback without it.

**Risk:** the `net-istio` cutover breaks Knative `InferenceService` routing. Signal: revisions stop
routing after the old Kourier resources are removed. Mitigation: smoke-test the Istio
`GatewayClass` and a real revision before the deletion commits. Response: revert the atomic GitOps
cutover; never leave `net-istio` and `net-kourier` active together.

**Risk:** the 9:1 split does not hold under load. Signal: distribution deviates more than 5 %.
Mitigation: 1000-request load test rather than 100. Response: confirm the GIE endpoint-picker is
honouring `HTTPRoute` weights and not round-robin.

**Risk (R-5):** the purge loses the 100 banked LLM points. Signal: a P12 capture row cannot be
re-earned. Mitigation: all 60 rows retain `validation_command` and `behavioral_assertion`; capture
the LLM rows first in P12, before the ML rows. Response: restore the implementation from git history —
the code was never deleted, only the evidence.

**Risk:** warm mode holds replicas resident and pushes the always-on floor up. Signal: cost jumps
after AC-P8-8. Mitigation: standby, not warm-resident — scale to a minimal standby replica, and
schedule the warm pool only inside serving windows. Response: report the cost delta alongside the
latency delta; the rubric asks for cost optimisation *and* startup reduction, so both numbers belong
in the evidence.

**Risk:** the agent registry is treated as satisfied by the existing Next.js registry page. Signal:
AC-P8-5 is claimed without a registry service. Mitigation: LLM 6 grades the deployed registry and
LLM 44 separately grades its UI — they are two rows. Response: deploy the registry service; the UI
alone does not satisfy LLM 6.
