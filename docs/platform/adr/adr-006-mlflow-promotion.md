# ADR-006: MLflow Promotion Contract

- Status: **Un-deferred by [ADR-016](./adr-016-full-platform-restore.md) (2026-09-05) — active from P7**

> **Un-deferred (2026-09-05, unified rebuild):** the platform restore
> (ADR-016) reinstates the ML track. MLflow is active from
> `plans/260831-1644-rebuild-target-mlops-architecture/phase-07-ml-track.md`
> onward; the promotion contract below is unchanged from its original
> design and needs no rewrite, only reactivation.

> **Previously deferred (2026-08-07):** MLflow was not installed for the
> LLM-only submission. This ADR stayed valid and unchanged for the
> post-deadline ML retrofit — see
> [ADR-010](./adr-010-llm-only-scope-and-platform-simplification.md).
- Date: 2026-08-02
- Deciders: the platform architecture review, ML engineer
- Related: `docs/platform/architecture.md`, `plans/260831-1644-rebuild-target-mlops-architecture/phase-07-ml-track.md`


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
