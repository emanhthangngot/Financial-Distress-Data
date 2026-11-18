# ADR-014: Distributed training — Ray, not Kubeflow Trainer HTTP

## Status

**Amended 2026-09-05** (unified rebuild,
`plans/260831-1644-rebuild-target-mlops-architecture/phase-07-ml-track.md`).
Originally accepted 2026-08-13 as a Kubeflow Trainer HTTP submission
boundary.

> **Amended:** distributed training runs on a **Ray cluster**
> (`ns: kubeflow`, target architecture component #45), not a
> `submit_kubeflow` HTTP call to Kubeflow Trainer. Kubeflow Pipeline
> (component #44) still orchestrates the training pipeline stages; Ray is
> the distributed-execution backend a pipeline stage submits to, not a
> replacement for the pipeline itself. Phase-07 owns `src/ml/pipelines/`.
> The local-baseline / cluster-submission split this ADR's original decision
> established stays: deterministic local tests never require a live Ray
> cluster, and a real Ray job is a separate, cluster-dependent acceptance
> step, exactly as the original text below already required for Kubeflow
> Trainer.

## Decision

The training module exposes a dependency-light local baseline and a separate
`submit_kubeflow` HTTP boundary. Local tests exercise deterministic sharding,
point-in-time validation, metrics, and manifest creation without requiring a
cluster. The submission boundary emits a Trainer-style payload and performs a
real request only when explicitly invoked with an endpoint.

## Rationale

This keeps import-time and unit-test behavior reproducible while preserving the
production integration seam requested by the ML rubric. A local pass is not
reported as distributed cluster evidence; the live Kubeflow run remains a
cluster-dependent acceptance step.

## Consequences

Training provenance is recorded in the same manifest regardless of backend.
Optional MLflow/scikit-learn/XGBoost dependencies can be added by a deployment
image without forcing heavy imports into the the platform test environment.
