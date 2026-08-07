# ADR-001: Two Gateways — agentgateway and Envoy AI Gateway

- Status: **Superseded in part by [ADR-010](./adr-010-llm-only-scope-and-platform-simplification.md) (2026-08-07)**
- Date: 2026-08-02
- Deciders: Phase 2 architecture review
- Related: `docs/phase2/architecture.md`, `plans/260802-1037-unified-phase2-ml-llm-gitops/plan.md`

> **Superseded:** Envoy Gateway and Envoy AI Gateway are dropped. The chain is
> now `kagent Agent -> kagent ModelConfig -> agentgateway AI backend -> an
> OpenAI-compatible CPU model server`. What survives: agentgateway remains the
> only path agents use to reach models or tools, enforced by negative tests.

## Context

The LLM track needs both agent/MCP protocol routing and LLM inference traffic
routing. A single gateway cannot own both control surfaces cleanly.

## Decision

- **kagent** owns the `Agent` and `ModelConfig` custom resources. Each Agent
  references one global `ModelConfig`; that config points its upstream/base URL
  to an **agentgateway AI backend**. agentgateway owns MCP/A2A protocol routes,
  agent identity, and forwarding into the inference chain. It is the only path
  agents use to reach models or tools.
- **Envoy Gateway + Envoy AI Gateway** own `LLMInferenceService` traffic and
  the llm-d/KServe integration. They are prerequisites managed by GitOps, not
  auto-created by an `LLMInferenceService` object.
- NGINX terminates public TLS; Istio enforces east-west mTLS. The two gateways
  are complementary, not merged.

## Consequences

- KServe 0.18 requires Envoy Gateway/Envoy AI Gateway installed before LLM
  workloads (per KServe 0.18 install docs); the GitOps platform wave installs
  them first.
- Cleaner separation of routing concerns, at the cost of one extra control
  plane to operate.
- The normative chain is `kagent Agent -> kagent ModelConfig -> agentgateway
  AI backend -> Envoy AI Gateway -> KServe LLMInferenceService/llm-d`; no
  coordinator or specialist may bypass it.

## Alternatives Considered

- One merged gateway (rejected: conflates agent protocol routing with inference
  traffic and breaks the KServe-required Envoy dependency).
