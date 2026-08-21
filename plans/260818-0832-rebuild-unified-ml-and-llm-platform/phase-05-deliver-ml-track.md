---
title: "Phase 5: Deliver The ML Track"
status: todo
priority: P1
effort: "2 weeks"
dependencies: [3, 4]
---

# Phase 5: Deliver The ML Track

## Overview

Build the 57 ML rubric rows that have never existed: the notebook, the Kubeflow
training pipeline with Ray distributed training, MLflow model and data versioning,
KServe/Triton champion-candidate serving, both FastAPI services, KEDA autoscaling,
the drift pipeline with retrain trigger, and A/B testing. This is the unbuilt half
of the coursework and carries the schedule's variance.

## Requirements

Functional:
- [ ] A Jupyter notebook pulling training data from the Feast offline store and producing a model, covering load → EDA → feature prep → train → evaluate → register
- [ ] A Kubeflow pipeline with the same steps as the notebook, running to completion
- [ ] The train step uses distributed training on a Ray cluster
- [ ] MLflow stores model weights, hyperparameters and metrics; models are versioned and tagged (`candidate`, `production`)
- [ ] Each training run pins an Iceberg snapshot ID, giving incremental data versioning
- [ ] Training reads only the embargoed train window from `src/lakehouse/holdout.py`; the frozen holdout is never in the training pull
- [ ] Every MLflow run logs `holdout_tag` and `holdout_snapshot` as parameters, and its evaluation metrics are computed on that pinned snapshot
- [ ] The current champion is scored on `holdout-v1` and registered as the promotion baseline before any candidate is evaluated
- [ ] Feature API: FastAPI, Pydantic validation, async, k8s healthchecks, reads Feast online store by entity ID, forwards to the inference engine
- [ ] Drift API: FastAPI, Pydantic validation, async, k8s healthchecks, real-time drift detection
- [ ] The drift service is triggered through **Knative Eventing** (Broker → Trigger) combined with KServe, as the rubric names literally — not by a plain HTTP call
- [ ] Both APIs deployed by Helm with rolling update and automatic rollback (`--atomic`)
- [ ] Both APIs autoscaled by KEDA on request rate, with a demonstrated scale-out and scale-in
- [ ] KServe serves the model through Triton, with a champion and a candidate `InferenceService`
- [ ] An Airflow drift pipeline compares offline features against reference, pushes PSI to Prometheus via PushGateway, and triggers a Kubeflow retrain
- [ ] Triton and `feature-api` log every request to a Kafka `inference_log` topic, sunk to `gold.inference_log` on Iceberg (request id, timestamp, model version, feature version, features, prediction, latency)
- [ ] The drift pipeline also compares `gold.inference_log` against the holdout reference, and joins `gold.labels` on `label_event_ts` for performance drift once outcomes land
- [ ] A/B traffic split between two model versions driven by **Argo Rollouts**, progressive (10% -> 25% -> 50%) with a Prometheus analysis gate and automatic rollback on regression, with a dashboard comparing the versions
- [ ] Rollouts routes traffic through `trafficRouting.nginx` (stable Ingress + canary Ingress with `nginx.ingress.kubernetes.io/canary-weight`), and the Argo CD Application carries `ignoreDifferences` for that annotation so a sync does not revert a weight step
- [ ] Feature API fronted by gateway **basic authentication and rate limiting**, both demonstrated
- [ ] Both APIs follow the API → Service → Repository layering from `plan.md`, with Triton reached through the `ModelRuntime` interface rather than a direct client call
- [ ] Both APIs instrumented with the **OpenTelemetry** SDK, exporting OTLP spans that link the incoming request to the Feast read and the inference call
- [ ] A/B comparison covers prediction-distribution divergence, latency, error rate and cost per 1K predictions

Non-functional:
- [ ] Feature API p99 latency under 200 ms at the load-tested throughput
- [ ] A failed rollout rolls back automatically without manual intervention

## Architecture

Reference 1's ML half, namespace for namespace:

```
Feast offline ──▶ Kubeflow pipeline ──▶ Ray cluster (tuning + distributed training)
                        │                        │
                        └────────────────────────┴──▶ MLflow (Postgres metadata + MinIO artifacts)
                                                              │  tag: candidate
                                                              ▼
                                         watcher ──▶ KServe/Triton candidate ──A/B──▶ champion
                                                              ▲
Airflow drift DAG ──PSI──▶ PushGateway ──▶ Grafana ──retrain trigger──┘
```

Distributed training uses Ray Train wrapping XGBoost, so the "distributed training"
row is satisfied by a real multi-worker run with per-worker logs, not by a
single-process job on a multi-core node. The evidence is the Ray dashboard showing
work distributed across workers.

Data versioning is incremental by construction: a training run records the Iceberg
snapshot ID it read. The second run against a slightly changed table stores only
the new snapshot's metadata, not a copy of the data — which is precisely the
"lần train thứ 2 data chỉ có 1 chút thay đổi thì chỉ lưu trữ lại phần thay đổi" the
rubric asks for. The proof is snapshot diffing, showing added files only.

A/B testing splits traffic between champion and candidate `InferenceService`s. With
no ground truth available, the comparison dashboard tracks prediction distribution
divergence, latency and error rate rather than accuracy — the same assumption the
rubric states.

Because online A/B has no ground truth, **the offline gate is the only place model
quality is actually checked**. Argo Rollouts can catch a candidate that crashes or
slows down; it cannot catch one that predicts confidently and wrongly, since the
label needed to know that arrives a `label_horizon` later. That puts the whole
weight of quality control on scoring against the frozen holdout from phase 2 —
which is why the promotion gate in phase 7 fails hard rather than warning when
champion and candidate carry different `holdout_snapshot` values. Two models
scored on different data produce a comparison that looks valid and means nothing,
and nothing downstream would flag it.

## Related Code Files

- Create: `notebooks/financial-distress-model.ipynb`, `src/ml/pipeline/` (Kubeflow components), `src/ml/train_ray.py`, `src/ml/registry.py`, `src/ml/data_version.py`, `src/ml/evaluate_holdout.py`, `scripts/score_champion_baseline.py`, `apps/feature-api/`, `apps/drift-api/`, `dags/drift_monitoring.py`, `scripts/run_ab_comparison.py`
- Modify: `src/drift/**` (PSI computation, PushGateway emit), `src/ml/**`
- Create in GitOps: `charts/feature-api/`, `charts/drift-api/`, `platform/kubeflow/pipelines/`, `platform/kserve/triton-champion.yaml`, `platform/kserve/triton-candidate.yaml`, `platform/keda/`, `platform/ml/ab-testing.yaml`
- Delete: `dags/phase2/phase2_drift_monitoring.py`, `dags/phase2/phase2_label_drift_build.py`

## Implementation Steps

1. Write the notebook end to end against the Feast offline store: load features by entity + timestamp, EDA on the real 10M-row dataset, feature preparation, train, evaluate, register to MLflow. Document each step — the documentation is itself a graded row.
2. Convert the notebook into Kubeflow pipeline components, one per notebook step, with typed inputs/outputs so intermediate artifacts are tracked.
3. Replace the train component with a Ray Train + XGBoost distributed job across ≥2 workers. Capture the Ray dashboard showing distributed execution.
4. Implement MLflow registration: weights, hyperparameters, metrics, and a model tag transitioning `candidate` → `production`.
5. Implement `data_version.py`: record the Iceberg snapshot ID per run; provide a diff showing the second run's incremental delta.
5b. Implement `evaluate_holdout.py`: read `gold.distress_holdout_v1` at tag `holdout-v1`, compute AUC, KS and the prediction-distribution summary, and log them to the run alongside `holdout_tag` and `holdout_snapshot`. Both the notebook and the Kubeflow evaluate component call this one function, so the notebook's numbers and the pipeline's numbers are comparable by construction — a graded row in its own right.
5c. Run `scripts/score_champion_baseline.py` once against the current champion and register the result as the promotion baseline. Skipping this is the most likely way the first phase-7 promotion fails: the gate has a candidate score and nothing to compare it against.
6. Build the feature API — async FastAPI, Pydantic request/response models, `/healthz` and `/readyz`, Feast online read by entity ID, forward to the inference engine. Apply the layering contract: routers hold no business logic, the service layer imports no framework and no store client, and Feast access sits behind a `FeatureRepository` interface so tests fake it without a live store. Reach Triton through the `ModelRuntime` adapter, not a Triton client in the service layer.
7. Build the drift API — async FastAPI, Pydantic models, healthchecks, computing drift statistics on demand against a reference window. Wire it as a **Knative Eventing** sink: a Broker receives drift-check events and a Trigger routes them to the service, combined with KServe as the rubric's CI/CD row states verbatim (*"sử dụng KNative Eventing kết hợp với KServe"*). A direct HTTP invocation does not satisfy that row.
8. Package both as one parameterized Helm chart; deploy through Argo CD with `--atomic` semantics; force a bad image to demonstrate automatic rollback and capture it.
9. Deploy KEDA HTTP scalers for both APIs; drive load and capture the scale-out and the scale-back-in.
10. Deploy Triton as champion and candidate `InferenceService`s serving the MLflow-registered model, on the **same KServe 0.18+ install** phase 4 provisions for llm-d. One KServe version serves both tracks; do not stand up a second install for the ML track.
11. Build the Airflow drift DAG: pull recent offline features, compute PSI against the reference window, push to Prometheus via PushGateway, and call the Kubeflow API to trigger retraining when PSI exceeds threshold.
12. Configure the A/B test as an **Argo Rollouts** `Rollout` with a canary strategy: weight steps 10% -> 25% -> 50%, an `AnalysisTemplate` querying Prometheus between steps, automatic promotion on pass and automatic rollback to weight 0 on regression. This is the mechanism the reference architecture draws; a static traffic split with no gate does not demonstrate "monitor it, and deploy". Build the per-version comparison dashboard alongside it.
13. Put the feature API behind NGINX Ingress **basic auth and a rate limit** (`nginx.ingress.kubernetes.io/limit-rps` plus an auth secret sourced from Vault). Demonstrate both: an unauthenticated request rejected, and a request burst returning 429 once over the limit. The ML rubric asks for this on the data-pulling Web API specifically, not on a UI.

## Success Criteria

- [ ] Notebook runs top to bottom against the real offline store, producing a registered model
- [ ] Kubeflow pipeline completes with the same step count as the notebook, captured from the Kubeflow UI
- [ ] Ray dashboard shows the training job distributed across ≥2 workers with per-worker progress
- [ ] MLflow shows ≥2 model versions with weights, hyperparameters, metrics and tags
- [ ] Two training runs record two Iceberg snapshot IDs; the diff shows only added files for the second
- [ ] Every MLflow run carries `holdout_tag` and `holdout_snapshot`; a test asserts no run is registered without them
- [ ] The champion's holdout baseline exists in MLflow before the first candidate is evaluated
- [ ] Notebook and Kubeflow pipeline report the same holdout metrics for the same model, within floating-point tolerance
- [ ] Both APIs pass Pydantic validation tests, expose healthchecks, and serve async
- [ ] An event published to the Knative Broker reaches the drift service via its Trigger, captured end to end
- [ ] A deliberately broken rollout rolls back automatically, captured from Argo CD / Helm output
- [ ] KEDA scales each API up under load and back to baseline, captured from the HPA/ScaledObject state over time
- [ ] Champion and candidate `InferenceService`s both serve predictions
- [ ] Drift DAG run pushes a PSI value visible on a Grafana panel and triggers a Kubeflow run
- [ ] Argo Rollouts advances through all three weight steps with the Prometheus gate passing, captured from the Rollouts dashboard or `kubectl argo rollouts get`
- [ ] A deliberately regressed candidate is rolled back to weight 0 automatically by the analysis gate
- [ ] A/B dashboard shows both versions receiving traffic with comparable per-version metrics
- [ ] Unauthenticated request to the feature API is rejected; a burst past the configured rate returns 429
- [ ] `python scripts/run_quality_gates.py` passes

## Risk Assessment

- **Kubeflow is the heaviest install in the plan and is version-sensitive against the GKE Kubernetes version.** Mitigation: install and smoke-test Kubeflow Pipelines standalone (not full Kubeflow) in phase 4's window, before this phase depends on it. Standalone Pipelines is sufficient for the rubric wording and far lighter.
- **Ray + Kubeflow + Triton together may exceed the node pool even at 48 vCPU.** Mitigation: Ray workers are ephemeral — scale the Ray cluster up for the training run and back to zero afterwards. Never leave Ray, Kubeflow and Spark resident simultaneously. The same discipline applies to DataHub, Trino and Flink; see phase 4's capacity risk.
- **Ray on CPU gives no throughput win, and claiming one would be checkable and wrong.** XGBoost already threads across cores within a process, so multiple Ray workers on CPU-only nodes distribute the mechanism without accelerating it — Ray's own documentation says as much. The success criterion is deliberately written as "the dashboard shows work distributed across ≥2 workers", which is what the rubric asks for. Mitigation: in the phase-8 write-up, claim the mechanism and say plainly that no speedup is expected on CPU. Do not present a timing comparison that implies otherwise.
- **Triton model-format conversion (XGBoost → Triton FIL backend) is a known friction point.** Mitigation: validate the conversion locally against a toy model before the pipeline depends on it. Fallback: KServe's native sklearn/xgboost server, which still satisfies "Inference Engine (ví dụ KServe)".
- **The retrain trigger can loop.** Mitigation: gate the Kubeflow trigger on a cooldown window and a minimum PSI delta, and assert the guard in a test.
- **The offline gate is the only real quality check, and it fails silently when misconfigured.** A candidate scored on the wrong snapshot still produces a plausible AUC, still passes, still promotes — there is no error to observe. Mitigation: the equality assert on `holdout_snapshot` in phase 7 exits non-zero rather than warning, and the daily tag test from phase 2 catches the upstream cause before a promotion ever reaches it.
- **A/B without ground truth invites a meaningless dashboard.** Mitigation: state the assumption explicitly and measure what is measurable — prediction distribution divergence, latency, error rate — rather than implying accuracy comparison.
