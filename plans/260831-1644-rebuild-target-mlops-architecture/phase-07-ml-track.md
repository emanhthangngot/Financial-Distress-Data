---
phase: 7
title: "Phase 7: ML track — notebooks, Kubeflow, Ray, MLflow, Triton, drift and retrain"
status: pending
priority: P1
effort: "14-20 days"
dependencies: ["phase-04-data-plane.md", "phase-05-cdc-streaming.md", "phase-06-platform.md"]
owns: ["src/ml/pipelines/", "src/ml/mlflow*", "src/ml/promotion_gate.py", "src/ml/data_versioning.py", "notebooks/", "platform/kubeflow/", "platform/tracking/", "platform/serving/triton-isvc.yaml", "dags/drift_check.py", "dags/retrain_trigger.py"]
---

# Phase 7: ML track — notebooks, Kubeflow, Ray, MLflow, Triton, drift and retrain

## Overview

Largest phase, and the one that closes the biggest gap: **all 57 ML rubric rows are currently
`design_only`** — none has ever executed. This phase turns the ML track from a design document into
a running system. **Resident cost: +3-4 vCPU windowed.**

ADR-014 (Ray distributed training) and ADR-006 (MLflow promotion, un-deferred) must be **accepted**
before this phase opens (P3 gate).

## Requirements

- Functional:
  - KFP, KubeRay, RayCluster and MLflow all `Healthy`.
  - A **Jupyter notebook** pulls features from the offline store through Feast and trains a model
    (ML 22).
  - A training **pipeline** reproduces the notebook with **the same number of steps** (ML 23).
  - The train step uses **distributed training** (ML 24); the MLflow `run_id` exists before the Ray
    job is submitted, and Ray reports per-epoch and per-worker metrics into that run.
  - Model weights and hyper-parameters land in the MLflow **Model Registry** (ML 25).
  - Each training pull **versions the data incrementally** (ML 26).
  - The promotion gate hard-fails when champion and candidate were scored on different snapshots.
  - Triton `InferenceService` canary steps 10 % → 25 % → 50 % (ML 51) with a **two-version
    monitoring dashboard** (ML 52).
  - An Airflow drift DAG pulls from the offline store, compares against ground truth, pushes through
    PushGateway (ML 49) and **triggers retrain by calling the Kubeflow API** (ML 50).
  - The real-time drift-detection Web API uses **KNative Eventing with KServe** (ML 34).
- Non-functional: `holdout-v1` (frozen in P4, pinned to a knowledge-time cutoff) is the only allowed
  evaluation snapshot; all training is windowed.

## Architecture

```
Iceberg Gold @ knowledge-time cutoff
        │
        ▼
 Jupyter notebook  ──(same step count)──►  KFP pipeline
        │                                       │
        │                            step 1: log MLflow run_id
        │                            step 2: version the data pull (incremental)
        │                            step 3: submit Ray distributed training → that run_id
        │                                       │
        │                              MLflow artifact store (MinIO)
        │                              MLflow Model Registry
        │                                       │
        │                            promotion_gate.py — holdout-v1 equality
        │                                       │
        ▼                                       ▼
   drift DAG (Airflow)              Triton InferenceService (ns: kserve)
   offline store vs ground truth    canaryTrafficPercent 10 → 25 → 50
        │  PushGateway                          │
        └──► Kubeflow API ──► retrain run       └──► two-version Grafana dashboard

   drift-api (real-time)  ──  KNative Eventing trigger ──► KServe
```

### Novel ideas (ML 57, ML 58)

- **Idea 1 — measured restatement leakage.** Using the P4 multi-vintage generator and the P2
  knowledge-time guard, report holdout AUC on latest-vintage features minus AUC on as-known
  features. The gap is the quantified proof that the naive pipeline leaks. The guard **fails** on
  the seeded restatement and passes with the vintage filter.
- **Idea 2 — cost-governed reproducibility manifest.** `src/ml/reproducibility_manifest.py` already
  exists; bind it to the live run so every promotion carries the data snapshot tag, the code SHA,
  the container digest and the measured cluster-hour cost.

## Related Code Files

- Restore from archive: `platform/kubeflow/` (KFP standalone, KubeRay, RayCluster),
  `platform/tracking/` (MLflow + Postgres + MinIO bucket)
- Modify: `src/ml/mlflow_registry.py` — bind to live MLflow; add `mlflow` to `pyproject.toml`
- Modify: `src/ml/pipelines/distributed_training.py` — bind to Ray; add `ray[train]`
- Modify: `src/ml/data_versioning.py` — incremental version per training pull (ML 26)
- Modify: `src/ml/reproducibility_manifest.py`, `src/ml/ab_router.py`
- Create: `src/ml/promotion_gate.py` — holdout equality assertion
- Create: `notebooks/ml-training.ipynb` (replaces the current stub), `notebooks/ml-eda.ipynb`
- Create: `platform/serving/triton-isvc.yaml` with `canaryTrafficPercent`
- Create: `platform/serving/knative-eventing-drift-trigger.yaml` (ML 34)
- Create: `dags/drift_check.py`, `dags/retrain_trigger.py`
- Create: `docs/evidence/ml/leakage-delta.md` (novel idea 1 write-up)

## Implementation Steps

1. **Restore `platform-kubeflow` and `platform-tracking`** (2-3 d) — KFP standalone, KubeRay,
   RayCluster; MLflow with its Postgres and MinIO bucket.
2. **Bind MLflow** (1 d) — `src/ml/mlflow_registry.py` against the live server; verify experiment
   and run creation, and Model Registry write.
3. **Author the notebook** (1-2 d) — pull features through Feast from the offline store at a named
   knowledge-time cutoff; train; evaluate on `holdout-v1`. **Record its step count** — the pipeline
   must match it.
4. **Bind Ray** (2 d) — `src/ml/pipelines/distributed_training.py` to the live cluster; run a toy
   distributed job; confirm per-worker metrics.
5. **KFP pipeline with step parity** (2-3 d) — step 1 logs the MLflow `run_id`; step 2 versions the
   data pull incrementally; step 3 submits the Ray job referencing that `run_id`. Assert the step
   count equals the notebook's.
6. **Promotion gate** (1 d) — hard equality assertion that champion and candidate are both scored at
   `holdout-v1`; `PromotionError` when snapshots differ; promote only when candidate ≥ champion.
7. **Triton + canary + dual dashboard** (1-2 d) — deploy the `InferenceService` in `ns: kserve`;
   step `canaryTrafficPercent` 10 → 25 → 50; build the Grafana dashboard comparing both versions
   without ground truth (ML 52 explicitly assumes no ground truth — monitor drift and traffic).
8. **Drift DAG + Kubeflow retrain trigger** (2-3 d) — Airflow DAG reads the offline store,
   compares against ground truth, pushes metrics through PushGateway, and on breach **calls the
   Kubeflow API** to start a retrain run. Verify a new KFP run appears.
9. **KNative Eventing drift path** (1 d) — a `Trigger` routes drift events to the KServe-backed
   drift API; verify an emitted event produces an invocation.
10. **Novel idea 1 measurement** (1-2 d) — train twice, once on latest-vintage features and once on
    as-known features at the same cutoff; report the holdout AUC delta; confirm the guard fails and
    then passes.
11. **End-to-end** (2 d) — full KFP run; `run_id` before Ray; gate rejects a snapshot mismatch;
    Triton canary steps; drift DAG fires retrain.

## Success Criteria

- [ ] AC-P7-1: Argo CD → syncs `platform-kubeflow` and `platform-tracking` → KFP, KubeRay,
      RayCluster and MLflow report `Healthy`
- [ ] AC-P7-2 **(ML 22)**: Data scientist → runs `notebooks/ml-training.ipynb` → pulls features from
      the offline store through Feast and produces a trained model
- [ ] AC-P7-3 **(ML 23)**: Engineer → compares the notebook and the KFP pipeline → **step counts are
      equal** and each step performs the same operation
- [ ] AC-P7-4 **(ML 24)**: KFP pipeline → reaches the train step → training runs distributed across
      more than one Ray worker; per-worker metrics appear in the MLflow run
- [ ] AC-P7-5: KFP pipeline → starts a training run → the MLflow `run_id` exists **before** the Ray
      job is submitted
- [ ] AC-P7-6 **(ML 25)**: Training pipeline → completes → model weights and hyper-parameters are
      retrievable from the MLflow Model Registry by version
- [ ] AC-P7-7 **(ML 26)**: Training pipeline → pulls from Feast twice → the second pull records an
      incremented data version referencing only the delta
- [ ] AC-P7-8: `src/ml/promotion_gate.py` → candidate scored on a different snapshot than champion →
      fails with a hard equality error; promotion blocked
- [ ] AC-P7-9: `src/ml/promotion_gate.py` → both scored at `holdout-v1` → promotes only when
      candidate accuracy ≥ champion
- [ ] AC-P7-10 **(ML 51)**: Triton `InferenceService` → receives a canary revision → serves N−1 at
      90 % and N at 10 %; the operator steps to 25 % then 50 %
- [ ] AC-P7-11 **(ML 52)**: Analyst → opens the Grafana dashboard → sees both model versions
      monitored side by side without ground truth (drift + traffic + latency)
- [ ] AC-P7-12 **(ML 49-50)**: Drift DAG → detects a threshold breach → pushes through PushGateway
      **and calls the Kubeflow API**; a new KFP retrain run is observable
- [ ] AC-P7-13 **(ML 34)**: Event source → emits a drift event → a KNative Eventing `Trigger`
      invokes the KServe-backed drift API; the invocation appears in the trace
- [ ] AC-P7-14 **(ML 57, novel idea 1)**: Engineer → trains on latest-vintage and on as-known
      features at the same cutoff → reports a non-trivial holdout AUC delta; the leakage guard
      **fails** on the seeded restatement and passes with the vintage filter
- [ ] AC-P7-15 **(ML 58, novel idea 2)**: Promotion → completes → the reproducibility manifest
      carries data snapshot tag, code SHA, image digest and measured cluster-hour cost

## Risk Assessment

**Risk:** Ray cannot allocate enough CPU. Signal: RayCluster pods `Pending`. Mitigation: G0 branch A
before P7; windowed clusters only. Response: reduce parallelism to two workers — AC-P7-4 needs
*more than one* worker, not many.

**Risk:** distributed training is unjustifiable at real scale (~64 000 statement rows) and a
reviewer notices. Signal: the training set is tiny. Mitigation: train on the **generated** 10-50M-row
corpus, not the 64 000 real rows, and say so explicitly in the write-up. Response: state the scale
honestly; the rubric grades that the mechanism works, and the generator is what makes it meaningful.

**Risk:** the notebook and the pipeline drift apart in step count. Signal: AC-P7-3 fails after a
later edit. Mitigation: assert step parity in a test, not by inspection. Response: fix whichever
side drifted.

**Risk:** MLflow's registry schema conflicts with existing contracts. Signal: registry write fails on
migration. Mitigation: run `mlflow_registry.py` unit tests against the live server before extending.
Response: reset the MLflow database and re-migrate.

**Risk:** the promotion gate rejects valid candidates because the holdout drifted. Signal:
`PromotionError` on an identical snapshot. Mitigation: `holdout-v1` is an immutable Iceberg tag
pinned to a knowledge-time cutoff. Response: restore from the P4 snapshot; by Iceberg semantics this
should be impossible.

**Risk:** the measured leakage delta is near zero and novel idea 1 has no evidence. Signal:
AC-P7-14's AUC gap is within noise. Mitigation: P4 calibrates restatement magnitude and cohort
correlation before this phase. Response: regenerate with stronger magnitudes; a near-zero delta
means the fixture was too mild, not that the leakage is unreal.
