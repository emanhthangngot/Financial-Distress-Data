# ADR-014: Kubeflow Trainer boundary

## Status

Accepted — 2026-08-13.

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
