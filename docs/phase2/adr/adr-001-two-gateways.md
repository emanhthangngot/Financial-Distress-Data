# ADR-001: Two Gateways — agentgateway and Envoy AI Gateway

- Status: Accepted
- Date: 2026-08-02
- Deciders: Phase 2 architecture review
- Related: `docs/phase2/architecture.md`, `plans/260802-1037-unified-phase2-ml-llm-gitops/plan.md`

## Context

The LLM track needs both agent/MCP protocol routing and LLM inference traffic
routing. A single gateway cannot own both control surfaces cleanly.

## Decision

- **agentgateway** owns MCP/A2A protocol routing, agent identity, and global
  model configuration. It is the only path agents use to reach the inference
  platform.
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

## Alternatives Considered

- One merged gateway (rejected: conflates agent protocol routing with inference
  traffic and breaks the KServe-required Envoy dependency).
