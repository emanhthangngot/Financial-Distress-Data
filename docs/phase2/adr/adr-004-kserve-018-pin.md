# ADR-004: KServe 0.18 Pin

- Status: **Partially revived by [ADR-010](./adr-010-llm-only-scope-and-platform-simplification.md) (2026-08-07, afternoon amendment)**
- Date: 2026-08-02
- Deciders: Phase 2 architecture review, platform operator
- Related: `docs/phase2/architecture.md`

> **Partially revived:** the 2026-08-07 morning amendment to ADR-010 dropped
> KServe entirely (evidence plane was a 16 GB rented `k3d` VM). The same day's
> afternoon amendment moved the evidence plane to GKE (~43 GB allocatable) and
> restored KServe `InferenceService` + Knative Serving + an llm-d router — this
> pin is back in effect for those three. **Envoy Gateway and Envoy AI Gateway
> stay dropped**: the plan routes through agentgateway, not the Envoy chain the
> 0.18 guide assumes, so that half of this ADR does not apply. Every chart and
> manifest stays version-pinned; no upgrade happens during the evidence window.

## Context

KServe `LLMInferenceService` integrates with llm-d and requires Envoy
Gateway/Envoy AI Gateway. A later release may change the install contract.

## Decision

- Pin KServe to the verified **0.18** integration for the entire coursework.
- All KServe charts/manifests are pinned; upgrades require a compatibility
  spike proving behavior before any version change.
- Envoy Gateway and Envoy AI Gateway are installed as prerequisites by GitOps
  before LLM workloads, per the KServe 0.18 installation guide.
- One resource has exactly one owner: Helm owns apps and MLflow; Kustomize
  owns only selected pinned upstream bases/overlays. KServe/Envoy dependencies
  are never rendered from both OCI Helm charts and Kustomize.

## Consequences

- Reproducible installs and deterministic evidence.
- No surprise upgrades during the evidence window.

## Alternatives Considered

- Latest KServe (rejected: unverified compatibility risk with llm-d/Envoy).
