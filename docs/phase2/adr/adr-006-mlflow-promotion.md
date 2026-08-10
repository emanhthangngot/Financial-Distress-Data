# ADR-006: MLflow Promotion Contract

- Status: **Deferred with the ML track — see [ADR-010](./adr-010-llm-only-scope-and-platform-simplification.md) (2026-08-07)**

> **Deferred:** MLflow is not installed for the LLM-only submission. This ADR
> stays valid and unchanged for the post-deadline ML retrofit
> (`plans/260802-1037-unified-phase2-ml-llm-gitops/phase-05-deliver-ml-track.md`).
- Date: 2026-08-02
- Deciders: Phase 2 architecture review, ML engineer
- Related: `docs/phase2/architecture.md`, `plans/.../phase-05-deliver-ml-track.md`

## Context

MLflow is needed for experiment tracking, candidate registration and
promotion. KServe serves immutable artifacts. The question is how promotion
flows from MLflow to KServe.

## Decision

- MLflow runs as an owned Helm chart in `ml-platform`, with an RDS backend and
  S3 artifacts.
- **MLflow is a promotion dependency, not a KServe runtime dependency.** KServe
  never reads the MLflow registry dynamically.
- The promotion controller resolves the approved MLflow production alias to an
  immutable S3 artifact URI and commits that URI (plus image digest) to the
  GitOps desired state.
- MLflow is ordered before promotion jobs; after desired state contains a valid
  artifact URI, the KServe controller does not wait on MLflow.

## Consequences

- Reproducible serving from immutable artifacts; Git is the source of truth
  for what is deployed.
- Rollback is a Git revert to the prior digest.

## Alternatives Considered

- KServe reading MLflow directly at serve time (rejected: mutable, not
  reproducible, breaks GitOps).
