---
title: "Phase 6: Deliver LLM, MCP and agent track"
status: todo
estimate: "10-15 days"
---

# Phase 6: Deliver LLM, MCP and agent track

## Overview

Deliver the full 100-point LLM track with a custom Qwen3-4B LoRA model, KServe `LLMInferenceService`, llm-d integration, agentgateway, governed MCP tools, three agents, sandbox/registry, warm-up mode, A/B tests and separate chat/registry UIs.

## Requirements

- [ ] Custom model server, reproducible benchmark, at least one measured optimization and before/after results.
- [ ] One global model configuration routes agents through agentgateway to the Envoy AI Gateway/KServe LLM plane.
- [ ] MCP tools: Feast feature/RAG retrieval and real-time drift; async FastAPI/Pydantic, health checks, Helm atomic rollout/fallback.
- [ ] Agents: feature analyst, drift analyst and coordinator; multi-replica, autoscaled, sandboxed, registered and governed.
- [ ] Warm-up mode with startup/TTFT/cost benchmark and an explicit HA worker-pool configuration.
- [ ] Unit quality, Locust HTML, A/B tests, telemetry, CI/CD and evidence match each LLM rubric requirement.

## Gateway Boundaries

- NGINX terminates public TLS and exposes only approved UIs/APIs.
- Istio enforces east-west mTLS and authorization.
- agentgateway owns MCP/A2A protocol routing, agent identity and global model configuration.
- Envoy Gateway + Envoy AI Gateway own `LLMInferenceService` traffic and llm-d/KServe integration. They are prerequisites managed by GitOps, not automatically created by an LLMInferenceService object.

## Design Contracts

- `RagIngestionService`: fetches trusted documents, parses/chunks/deduplicates, enforces metadata/licensing and writes Feast/PGVector versions.
- `EmbeddingRegistryService`: records model/vector compatibility and performs zero-downtime embedding-version hot swap.
- `McpToolService`: validates scoped tool requests, authorizes agent/tool identity, enforces timeouts/budgets and emits traces.
- `AgentOrchestrationService`: coordinates specialist agents with bounded hops, citation checks and deterministic failure policy.
- `AgentReleaseService`: registers, canaries, warms, promotes and rolls back agent/model configurations through GitOps.

## Implementation Steps

1. Seed failing tool-contract, sandbox, authorization, registry, citation, PII, warm-up, autoscale, A/B, idempotency and gateway-route tests.
2. Fine-tune Qwen3-4B with LoRA only when the rubric/domain evaluation justifies it; version adapter, base model, prompt template, dataset and license metadata.
3. Deploy KServe 0.18 `LLMInferenceService` using its pinned compatible llm-d integration. Benchmark baseline and optimized settings for TTFT, inter-token latency, throughput, memory and cost.
4. Apply the global model configuration at agentgateway and prove agents reach the custom model only through the declared gateway chain.
5. Implement Feast/RAG and drift MCP servers; deploy with Helm atomic rolling updates, service accounts, Istio policies, rate/timeout limits and structured tool errors.
6. Build notebooks demonstrating agent interaction with both MCP servers before production packaging.
7. Deploy feature analyst and drift analyst, then a coordinator with bounded fan-out/hops; configure multi-replica autoscaling and Agent Sandbox restrictions; publish all to agentregistry.
8. Implement warm-up pools with minimum warm capacity during evidence windows and scale-down outside them. Measure cold vs warm startup/TTFT/cost; document replica/zone spread and disruption budget for HA proof.
9. Implement separate agent chat and registry UI routes. Chat shows agent/tool trace and citations; registry shows version, status, replicas, model config, sandbox policy and promotion history.
10. A/B test two LLM versions on the inference platform and two agent model configs; dashboard quality proxies, TTFT, latency, tokens, failure/safety and cost.
11. Generate Locust HTML for the feature/RAG MCP-facing Web API and record the same SLA fields used by the ML feature API.
12. Optional last-stage compute: configure a Vast.ai CPU worker through Ansible roles only when a vetted offer fits the aggregate USD 10 hard cap; AWS Spot remains primary.

## Novel-Idea Proof

- Embedding-version hot swap: dual-read validation and alias change produce no downtime or mixed-vector query.
- Citation/PII guard: unsupported or sensitive output is blocked/rewritten and the decision is linked to its OpenTelemetry trace and evidence manifest.

## Success Criteria

- [ ] Reviewer -> inspects the custom model deployment -> sees versioned model/config, repeatable benchmark and quantified optimization.
- [ ] Registered coordinator -> calls both specialist agents -> receives cited Feast/RAG and drift results through sandboxed MCP tools with bounded orchestration.
- [ ] Load tester -> compares cold and warm agent modes -> sees improved startup/TTFT, documented cost, and multi-replica HA behavior.
- [ ] Analyst -> uses agent chat -> sees citations and tool/agent status; registry viewer -> uses a separate UI -> sees governed releases and replicas.
- [ ] Platform observer -> compares A/B variants -> sees LLM and agent dashboards with tokens, TTFT, round-trip, tool/agent calls, failures and PII catches.
- [ ] Test runner -> executes changed-code gates -> reports >90% coverage and >80% mutation score plus equivalence, boundary, property and Locust proof.

## Risks and Rollback

- Risk: GPU availability/cost prevents repeatable evidence. Mitigation: small custom model, hard session TTL, preflight capacity, saved benchmark artifacts and CPU fallback only within cap.
- Rollback: Git-revert agent/model configuration and preserve prior registered versions; never mutate a production alias without an audit event.
