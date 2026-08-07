---
title: "Phase 5: Deliver ML track"
status: deferred
estimate: "8-12 days standalone / 4-5 days as retrofit after the LLM track ships"
---

# Phase 5: Deliver ML track

> **DEFERRED — 2026-08-07. Not in the submission scope; resume after the deadline.**
>
> The coursework accepts one of the two tracks. With 7 days remaining and zero
> executed evidence, the submission delivers the LLM track only. This file stays
> in place unchanged in substance: it is the retrofit backlog, not dead work.
>
> **Do not churn the ML rows** in `docs/phase2/rubric-matrix.csv`,
> `scripts/_phase2_rubric_items.py`, or `docs/phase2/acceptance-criteria.md`.
> The 4-5 day retrofit estimate holds only while those 57 rows stay frozen, and
> the phase-08 auditor's canonical-coverage check requires all 117 rows present
> regardless of which track is submitted.

## Deferral Contract

### Why the retrofit is cheap (4-5 days, additive only)

ML's 100 points split into 68 points in sections shared with the LLM track and
32 points that are ML-only. Shipping the LLM track builds the shared 68 first.
The residual work:

| ML section | Points | State after the LLM track ships |
|---|---:|---|
| CI/CD | 16 | pipeline, signing, digest, Argo, GitOps PR exist; add ML deployables to the matrix |
| Routing & Gateway | 11 | NGINX + cert-manager + ingress exist; add the ML inference route |
| Observability | 10 | Prometheus/Grafana/Loki/Jaeger exist; add ML dashboards and metrics |
| Validation & Verification | 10 | coverage/mutation/property/Locust harness exists; add ML tests |
| Web API kéo dữ liệu + drift API | 12 | **already built** — the LLM track ships both as MCP-backed services |
| Improve the Data Generator | 6 | **already built** — done to ML depth in phase-04 |
| Feature Store | 6 | Feast online store exists; add offline materialization |
| IaC / Repository / Security / Docs / Novel / A/B | 15 | largely reusable |
| ML Pipelines (KFP) | 4 | new |
| Versioning (MLflow) | 4 | new |
| Autoscale | 4 | HPA config exists; copy values |
| ML (train LogReg + XGBoost) | 2 | new |

### Load-bearing decisions the LLM track MUST honor

Breaking any of these turns the retrofit from additive into rework:

1. **Feast offline store is defined from day one**, even though the LLM track
   only reads the online store. Feature views carry a correct `event_timestamp`
   and an offline source. Retrofitting point-in-time correctness onto an
   online-only key-value design is a schema redesign, not an addition.
2. **The label table schema is created in phase-04** (`ticker`,
   `event_timestamp`, `label`, `label_version`, `created_ts`,
   `training_eligible`) even with no training consumer. The LLM rubric requires
   the label table anyway (`LLM-improve-the-data-generato-t-o-b-ng-l...`, 2 pts).
3. **Both Web APIs stay generic services**; the MCP tool is a thin wrapper over
   them. Business logic never lives in the MCP server. ML reuses the services
   verbatim for its own 12 points.
4. **CI matrix iterates a deployable list**, never a hardcoded LLM service set.
   Adding an ML service is one list entry.
5. **One parameterized Helm chart** serves every FastAPI deployable. ML adds a
   values file only.
6. **Argo CD ApplicationSet uses a directory generator**, so a new ML app is
   discovered without editing Argo config.
7. **Metrics carry a `service` label; Grafana dashboards use template
   variables**, so ML panels are a variable value rather than a new dashboard.
8. **`src/ml/contracts.py` stubs stay in the repository**, unchanged.
9. **`src/drift/` is created by the LLM track** (the drift MCP tool needs it)
   with the ML drift contract shape already in mind.

### Explicitly out of the LLM-track scope

Kubeflow Pipelines, Kubeflow Trainer, MLflow, distributed XGBoost training,
model promotion gates, KServe ML `InferenceService`, and Knative Eventing. None
of these appear in any LLM rubric row. Installing them "just in case" is the
single largest way to lose the 7-day budget.

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
9. Route real-time drift events through Knative Broker/Trigger to the drift service and KServe prediction path. Separately execute the scheduled Airflow drift DAG: pull Feast offline data, join proxy/ground-truth reference, compute Evidently metrics, push them through Pushgateway to Grafana, then call the Kubeflow Pipelines API when threshold is exceeded. Persist idempotency key, decision, KFP run ID/status; a recommendation alone is not sufficient.
10. Add A/B split for two inference revisions and dashboards for traffic, latency, errors, prediction distribution and proxy outcome metrics.
11. Generate Locust HTML for the feature API with accepted SLA: p95 latency, throughput, error rate and concurrency; include test parameters.
12. Implement the feature-specific gates in `tests/phase2/requirements/test_ml_ac_01_web_api.py` through `test_ml_ac_18_novel.py`; every scored row's exact `validation_command` must select an assertion for that row, not only the metadata contract test.

## Test Gates

- Changed-code unit coverage >90%; changed-code mutation score >80% using `mutmut`.
- Parametrized equivalence and boundary tests for input schema, missing/unknown ticker, timestamp edges, risk thresholds and API limits.
- Hypothesis idempotency for repeated predictions/materialization and PIT invariants.
- Locust HTML and screenshot for feature API; separate autoscale experiments for feature and drift APIs.
- KFP/Kubeflow Trainer execution, MLflow registry/version, KServe health, Knative event, A/B evidence, and scheduled drift skip/trigger evidence with actual KFP API run ID.
- `python scripts/audit_phase2_evidence.py --require-executed --run-validations ...` must execute all ML acceptance files successfully before any row is marked `executed`.

## Success Criteria

- [ ] ML engineer -> runs the KFP pipeline -> receives a distributed training run whose model and incremental data version are registered in MLflow.
- [ ] Promotion controller -> evaluates an accepted candidate -> opens a GitOps PR containing immutable model and image references; it does not call KServe imperatively.
- [ ] Load tester -> stresses the feature API -> receives Locust HTML meeting the recorded SLA and observes KEDA/HPA scale-out and scale-in.
- [ ] Drift producer -> publishes a real-time event -> sees Knative delivery, drift calculation and persisted telemetry; scheduled ML operator -> crosses the threshold -> sees an actual idempotent KFP run ID/status rather than only a recommendation.
- [ ] Reviewer -> inspects two KServe revisions -> sees controlled A/B traffic, comparative dashboard and a Git-based rollback path.
- [ ] Test runner -> executes changed-code gates -> reports >90% coverage and >80% mutation score without excluding relevant code.

## Risks and Rollback

- Risk: class imbalance inflates headline accuracy. Mitigation: emphasize PR-AUC, distress recall, calibration, confusion matrix and time-based holdout.
- Rollback: revert the GitOps promotion commit to the previous artifact/image digest; keep both MLflow versions and their data manifests.
