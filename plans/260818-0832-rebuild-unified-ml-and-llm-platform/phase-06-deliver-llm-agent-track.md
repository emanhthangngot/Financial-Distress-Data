---
title: "Phase 6: Deliver The LLM And Agent Track"
status: todo
priority: P1
effort: "1.5 weeks"
dependencies: [3, 4, 5]
---

# Phase 6: Deliver The LLM And Agent Track

## Overview

Re-earn the 60 LLM rows on the rebuilt platform: LLM inference platform with a
custom model and a benchmarked optimization, agent gateway and global model config,
agent registry, the RAG pipeline, both MCP servers, three agents (feature, drift,
coordinator) with multi-replica and autoscaling, sandbox isolation, warm-up, the
chat and registry UIs, and the LLM/agent telemetry.

Most of this code already worked once. This phase is deliberately placed after the
ML track because it is re-execution rather than invention — low variance work that
should absorb slippage, not cause it.

## Requirements

Functional:
- [ ] LLM inference platform deployed on the branch phase 4 step 12 selected — **A**: KServe `LLMInferenceService` backed by llm-d on the vLLM CPU backend; **B**: llama.cpp OpenAI-compatible server behind a plain `InferenceService` with a custom `ServingRuntime`
- [ ] Model server benchmarked, then optimized, with a before/after result table covering quantization plus the branch's routing evidence — llm-d KV-cache aware routing on branch A, gateway semantic-cache hit rate on branch B
- [ ] A global model config applied, linking agents to the inference platform through the agent gateway
- [ ] Agent registry deployed, with all three agents published to it
- [ ] Airflow RAG pipeline: text → chunk → embed → store vectors in Feast, with DataHub lineage and governance checks
- [ ] Feature MCP server and drift MCP server, each async FastAPI + Pydantic + healthchecks, deployed by Helm with rolling update and `--atomic` rollback
- [ ] Three agents deployed multi-replica with autoscaling: feature agent, drift agent, coordinator agent
- [ ] Agents run sandboxed with restricted permissions
- [ ] A guardrail component sits on both legs of the agent-to-model path: PII redaction and prompt-injection filtering inbound, citation and PII checks outbound; the bypass attempt is covered by the negative test
- [ ] Warm-up configured, benchmarked, with an HA note on worker-pool replicas
- [ ] Two notebooks: agent ↔ MCP for feature retrieval + drift detection; agent ↔ MCP for RAG retrieval
- [ ] Chat UI and registry UI behind the gateway with authentication and rate limiting — **built in phase 9** as routes of the in-cluster web app; this phase owns the agent and registry APIs they call, not the frontend
- [ ] LLM telemetry: input/output/total tokens per request, round-trip time, TTFT, error frequencies, and derived cost per request
- [ ] Agent telemetry: calls per agent, calls per MCP tool, failures per tool call, task success/failure outcome per agent run, and cost per agent run
- [ ] **Agent A/B**: two agent variants differing in model, temperature and prompt version, compared on latency, token usage, error rate, tool-failure rate, task success rate and cost per task
- [ ] **LLM A/B**: two models behind the gateway at 50/50, compared on answer quality, latency, TTFT, throughput, token usage, cost and safety/refusal rate
- [ ] MCP servers and agents instrumented with **OpenTelemetry**, so one trace spans agent → MCP tool → Feast → LLM call
- [ ] **Cost** is a first-class metric, derived per request from token counts and a configured price-per-1K-token, exposed to Prometheus and shown per variant

Non-functional:
- [ ] Warm-up demonstrably reduces cold-start latency, measured before and after
- [ ] MCP servers deploy as MCP endpoints, not plain REST deployments

## Architecture

The LLM half sits alongside the ML half on the same cluster, sharing KServe/Knative,
the ingress, the mesh and the observability stack. The coordinator agent orchestrates
the feature agent and the drift agent; each agent reaches its tools through MCP
servers, which in turn read the same Feast stores the ML track uses. That shared
data path is the point of running both tracks on one platform rather than two.

RAG vectors live in Feast alongside the tabular features, so the "Web API pulls user
data and chunks" row is served by one store rather than two.

Telemetry is emitted by the gateway and by the agent runtime rather than
hand-instrumented per agent, so adding an agent does not mean adding metrics code.

## Related Code Files

- Create: `src/llm/rag/` (chunking, embedding), `dags/rag_ingest.py`, `apps/feature-mcp/`, `apps/drift-mcp/`, `src/agents/feature_agent.py`, `src/agents/drift_agent.py`, `src/agents/coordinator.py`, `notebooks/agent-mcp-feature-drift.ipynb`, `notebooks/agent-mcp-rag.ipynb`, `scripts/run_llm_benchmark.py`, `scripts/run_warmup_measurement.py`
- Modify: `src/observability/**` (LLM + agent metrics). The web frontend is phase 9's scope.
- Create in GitOps: `platform/llm/inference-service.yaml`, `platform/llm/model-config.yaml`, `platform/agentgateway/`, `platform/agents/registry.yaml`, `platform/agents/sandbox-namespace.yaml`, `charts/feature-mcp/`, `charts/drift-mcp/`, `platform/llm/ab-testing.yaml`
- Delete: `dags/phase2/phase2_rag_ingest.py`

## Implementation Steps

1. Deploy the LLM platform on the branch phase 4 step 12 recorded — do not re-open that decision here. Branch A: a KServe `LLMInferenceService` on the 0.18+ install, llm-d serving stack, small quantized model on the vLLM CPU backend, reached through its Gateway API `HTTPRoute`. Branch B: a llama.cpp OpenAI-compatible server behind a plain `InferenceService` with a custom `ServingRuntime`, reached through NGINX. Verify a completion end to end through the agent gateway either way — the gateway and `ModelConfig` wiring is identical, which is the point of the `ModelRuntime` adapter.
2. Benchmark in three passes, each a row in the same before/after table: (a) baseline — throughput, TTFT, p99, tokens/s; (b) after quantization; (c) the branch's routing/caching pass. On branch A that is llm-d KV-cache aware routing, driven by a multi-turn workload whose requests share a prefix so the routing has something to exploit; report cache hit rate alongside TTFT. On branch B it is the gateway semantic cache over the same prefix-sharing workload, reported the same way — hit rate against TTFT — so the row's evidence shape is unchanged even though the mechanism is not.
   Do **not** attempt disaggregated prefill/decode — the cluster has no GPU (`GPUS_ALL_REGIONS` = 0, unraisable on a trial account) and the feature yields no meaningful CPU measurement. Say so explicitly in the write-up rather than omitting it.
3. Apply the global model config so agents resolve their model through the gateway rather than by direct endpoint.
4. Deploy the agent registry; confirm it is reachable behind the gateway.
5. Build the RAG pipeline in Airflow: pull source text, chunk with a documented strategy, embed, write vectors into Feast. Emit DataHub lineage and run the governance checks.
6. Build both MCP servers as async FastAPI + Pydantic with healthchecks, exposing MCP tool endpoints — deployed as MCP servers, with the session/transport handling that requires, not as plain REST services.
7. Package each MCP server in a Helm chart with rolling update; demonstrate `--atomic` rollback on a deliberately bad image.
8. Build the three agents, deploy multi-replica with autoscaling, and publish each to the registry.
9. Create the sandbox namespace with restricted RBAC, NetworkPolicy and the mesh AuthorizationPolicy from phase 4; run the agents inside it and show a blocked out-of-scope action.
10. Configure warm-up; measure cold-start latency before and after; document the HA approach for worker-pool replicas.
11. Write both notebooks demonstrating agent ↔ MCP interaction for feature/drift and for RAG.
12. Expose the agent-invocation and registry-listing APIs the phase-9 UIs consume, and confirm the gateway's basic auth and rate limit apply to those routes. The UIs themselves are phase 9's deliverable — do not build a second frontend here.
13. Instrument LLM telemetry (tokens in/out/total, round-trip, TTFT, error frequency) and agent telemetry (calls per agent, calls per tool, failures per tool); build Grafana panels for both.
14. Configure the two A/B tests. The split mechanism differs by surface, but the **analysis definition is shared with phase 5** — the same Prometheus queries and the same promotion thresholds, so there is one gate contract rather than two hand-rolled ones.
    - **Split mechanism (branch A).** The LLM pair is split by the `LLMInferenceService` router's Gateway API `HTTPRoute` weights; Argo Rollouts cannot own an llmisvc-managed workload any more than it can own a Knative-backed `InferenceService`. The agent pair runs on ordinary Deployments, so it uses the phase-5 Rollouts + `trafficRouting.nginx` mechanism directly.
    - **Split mechanism (branch B).** If phase 4 step 12 selected llama.cpp, both LLM variants are plain `InferenceService`s and the split moves to the same NGINX canary-weight mechanism as the agent pair.
    - **Agent A/B** — variant A and variant B differ on three axes at once (model, temperature, prompt version), which is what makes the comparison a real production decision rather than a parameter sweep. Compare on: latency, token usage, error rate, tool-failure rate, **task success rate** against a fixed evaluation set, and **cost per task**. Task success and cost are the two that actually decide promotion; latency alone would let a cheap-but-wrong variant win.
    - **LLM A/B** — two models at 50/50 behind the gateway, compared on answer quality (scored against the same fixed question set), latency, TTFT, throughput, token usage, cost and safety/refusal rate. Record the trade-off explicitly: the faster model is rarely also the better and the cheaper one, and the write-up should name which axis was chosen and why.
    - Neither promotion is by feel. The `AnalysisTemplate` gate encodes the chosen threshold, so the decision is in Git and reversible.
15. Implement cost as a derived metric: a configured price per 1K input and output tokens, multiplied by the token counters already emitted, exported to Prometheus with the variant as a label. Without this, "cost" in both A/B tables is an estimate rather than a measurement.

## Success Criteria

- [ ] A completion returns through the gateway using the global model config, served by an `LLMInferenceService`
- [ ] Benchmark table has three rows (baseline / quantized / KV-cache routing) with throughput, TTFT, p99 and cache hit rate, each optimization named
- [ ] The write-up states the GPU constraint and which llm-d features it puts out of scope
- [ ] All three agents appear in the registry UI, each running ≥2 replicas
- [ ] RAG DAG completes; vectors are retrievable from Feast; DataHub lineage is unbroken
- [ ] Both MCP servers respond to MCP tool calls from an agent, not just to HTTP probes
- [ ] A bad MCP image rolls back automatically, captured from Helm/Argo output
- [ ] An out-of-scope action from a sandboxed agent is blocked, captured from logs
- [ ] Warm-up measurement shows a reduced cold-start latency, before and after
- [ ] Both notebooks execute and show agent ↔ MCP results
- [ ] Agent-invocation and registry APIs respond to the phase-9 UIs, with gateway auth and rate limiting enforced on those routes
- [ ] Grafana shows token counts, TTFT, round-trip time, per-agent and per-tool call counts and failures, plus derived cost per request and per agent run
- [ ] Agent A/B table reports all six dimensions per variant, including task success rate and cost per task
- [ ] LLM A/B table reports all seven dimensions per variant, with the chosen trade-off axis named
- [ ] Both A/B tests route traffic across variants — the agent pair through Argo Rollouts, the LLM pair through the llmisvc `HTTPRoute` weights (or NGINX canary weights on branch B) — with a comparison dashboard
- [ ] `python scripts/run_quality_gates.py` passes

## Risk Assessment

- **LLM serving needs memory the node pool may not have after ML workloads land.** Mitigation: use a small quantized model — the rubric grades platform mechanics, benchmarking and optimization, not model quality. Schedule the LLM benchmark in a window where Ray and Spark are scaled to zero.
- **llm-d on CPU may show a negligible KV-cache routing delta, leaving the optimization row thin.** Mitigation: design the benchmark workload for it — high prefix overlap, multi-turn, enough concurrency that routing decisions matter. Measure early in the phase, not during phase 8 capture. If the delta is genuinely negligible, report that as the finding and let quantization carry the row; do not tune the workload until the number flatters llm-d.
- **KServe 0.18+ is a large jump from the 0.14.1 the old project ran, and the CRD surface changed.** Mitigation: phase 4 installs and smoke-tests 0.18+ before either track depends on it, and the ML track's Triton serving migrates on the same install — one KServe version across both tracks, never two.
- **MCP deployment differs from ordinary REST deployment (session affinity, transport).** The rubric calls this out explicitly. Mitigation: verify a real MCP client session against the deployed server, not just a health probe — the success criterion is written that way deliberately.
- **Rebuilding what already worked invites shortcuts.** Mitigation: no evidence artifact may be copied from the pre-rebuild tag. The phase-1 purge and the auditor's regeneration check are what enforce this.
- **Sandbox restrictions can silently break legitimate agent calls.** Mitigation: capture both a permitted call succeeding and a forbidden call being blocked; one without the other proves nothing.
