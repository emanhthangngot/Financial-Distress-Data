# ADR-007: Mixed Helm/Kustomize Ownership

- Status: **Superseded by [ADR-010](./adr-010-llm-only-scope-and-platform-simplification.md) (2026-08-07)**
- Date: 2026-08-02
- Deciders: Phase 2 architecture review, platform operator
- Related: `docs/phase2/architecture.md`

> **Superseded:** Helm is the only render tool. Kustomize is dropped, so one
> resource has exactly one owner by construction; `resource-ownership.yaml` and
> the duplicate-owner CI check are removed as unnecessary. The ADR's premise —
> that KServe ships pinned Kustomize overlays — no longer applies, because
> KServe is not installed.

## Context

KServe 0.18 installation supports Helm, Kustomize and script methods. The plan
uses Helm for first-party apps and MLflow, and Kustomize for selected pinned
upstream resources. Two deploy tools can conflict if both own the same
resource.

## Decision

- One resource has exactly one owner.
  - Helm owns first-party apps and MLflow (charts we own).
  - Kustomize owns only selected pinned upstream bases/overlays and
    environment patches.
- `resource-ownership.yaml` in the GitOps repo records ownership; CI rejects
  any Kubernetes identity rendered by two owners.
- KServe/Envoy dependencies are never rendered from both OCI Helm charts and
  Kustomize.
- CI validates `helm lint/template`, `kustomize build`, `kubeconform`, and
  duplicate-owner checks.

## Consequences

- Deterministic apply order and no ownership conflicts.
- Slightly more tooling in CI, but provable non-overlap.

## Alternatives Considered

- All-Helm (rejected: some pinned upstream KServe resources are distributed as
  Kustomize overlays).
