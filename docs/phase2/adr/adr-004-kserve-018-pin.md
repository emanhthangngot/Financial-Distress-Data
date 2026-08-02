# ADR-004: KServe 0.18 Pin

- Status: Accepted
- Date: 2026-08-02
- Deciders: Phase 2 architecture review, platform operator
- Related: `docs/phase2/architecture.md`

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
