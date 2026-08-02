---
title: "Phase 5: Deliver ML track"
status: todo
estimate: "8-12 days"
---

# Phase 5: Deliver ML track

## Overview

Deliver the full 100-point ML track: a Feast-backed training notebook and Kubeflow pipeline, distributed training, MLflow model/data versioning, separately autoscaled feature and drift APIs, KServe inference, Knative Eventing drift flow, A/B testing, and executable proof.

## Requirements

- [ ] Baselines fit the classification task and time dependency: logistic regression plus XGBoost; optimize distress recall/PR-AUC without hiding calibration or false positives.
- [ ] Kubeflow Pipelines runs the same logical steps as the notebook and uses Kubeflow Trainer for distributed XGBoost.
- [ ] MLflow stores weight, hyperparameters, metrics, model signature/card, data snapshot/delta ID, code SHA and environment digest.
- [ ] KServe serves immutable promoted artifacts and supports old/new traffic split with observable A/B results.
- [ ] Feature API and real-time drift API are independent FastAPI deployables with Pydantic, async I/O, health/readiness, Helm atomic rollback and independent KEDA/HPA proof.
- [ ] Drift API enters through Knative Eventing and invokes the KServe-backed path required by the rubric.

## Design Contracts

- `TrainingDataService`: reads Feast historical features, joins labels, validates schema/deltas, and returns snapshot lineage.
- `PointInTimeSplitService`: derives non-overlapping time boundaries and train/validation/test frames without future leakage.
- `FeatureMaterializationService`: owns batch/stream materialization checkpoints, TTL and idempotency.
- `ModelTrainingService`: trains/evaluates distributed baselines and logs reproducible MLflow runs.
- `ModelPromotionService`: applies gates, resolves immutable artifact URI, opens GitOps PR, canaries, and emits Git-revert rollback metadata.

## Implementation Steps

1. Seed failing unit, equivalence partition, boundary value, property/idempotency, mutation, API contract, Helm, autoscaling, model promotion and rollback tests.
2. Build notebook: retrieve Feast offline data, PIT-join label, time split, train, validate, save `.joblib`, and document each step.
3. Convert notebook logic into KFP components: resolve data version -> validate -> split -> distributed train -> evaluate -> register candidate -> promotion decision.
4. Use Kubeflow Trainer for distributed training and capture worker topology, logs and successful pipeline graph.
5. Register model and incremental data version in MLflow. Promotion requires DQ pass, no leakage, metric/calibration thresholds, signed image, and complete evidence manifest.
6. Package prediction server for KServe. Source CI updates GitOps only with model artifact URI/version and immutable image digest.
7. Build `feature-api` and `drift-api`; add `helm upgrade --install --atomic`, rolling update, probes, PodDisruptionBudget and rollback test.
8. Autoscale each API separately; trigger load and capture replicas, request rate, latency and cooldown. Prefer KEDA HTTP/Prometheus scaler with HPA fallback documented.
9. Route drift events through Knative Broker/Trigger to the drift service and KServe prediction path; persist drift result and retraining recommendation.
10. Add A/B split for two inference revisions and dashboards for traffic, latency, errors, prediction distribution and proxy outcome metrics.
11. Generate Locust HTML for the feature API with accepted SLA: p95 latency, throughput, error rate and concurrency; include test parameters.

## Test Gates

- Changed-code unit coverage >90%; changed-code mutation score >80% using `mutmut`.
- Parametrized equivalence and boundary tests for input schema, missing/unknown ticker, timestamp edges, risk thresholds and API limits.
- Hypothesis idempotency for repeated predictions/materialization and PIT invariants.
- Locust HTML and screenshot for feature API; separate autoscale experiments for feature and drift APIs.
- KFP/Kubeflow Trainer execution, MLflow registry/version, KServe health, Knative event and A/B evidence.

## Success Criteria

- [ ] ML engineer -> runs the KFP pipeline -> receives a distributed training run whose model and incremental data version are registered in MLflow.
- [ ] Promotion controller -> evaluates an accepted candidate -> opens a GitOps PR containing immutable model and image references; it does not call KServe imperatively.
- [ ] Load tester -> stresses the feature API -> receives Locust HTML meeting the recorded SLA and observes KEDA/HPA scale-out and scale-in.
- [ ] Drift producer -> publishes a real-time event -> sees Knative delivery, drift calculation, persisted telemetry and retrain trigger decision.
- [ ] Reviewer -> inspects two KServe revisions -> sees controlled A/B traffic, comparative dashboard and a Git-based rollback path.
- [ ] Test runner -> executes changed-code gates -> reports >90% coverage and >80% mutation score without excluding relevant code.

## Risks and Rollback

- Risk: class imbalance inflates headline accuracy. Mitigation: emphasize PR-AUC, distress recall, calibration, confusion matrix and time-based holdout.
- Rollback: revert the GitOps promotion commit to the previous artifact/image digest; keep both MLflow versions and their data manifests.
