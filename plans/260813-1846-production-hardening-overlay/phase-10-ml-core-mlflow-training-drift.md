---
phase: 10
title: "ML core: MLflow, training, distributed, drift"
status: cancelled
priority: P1
effort: "4d"
dependencies: [7, 9]
---

> **CANCELLED 2026-08-14 (user decision, ML track dropped).** Entirely ML-track scope (~26 pts) — MLflow, distributed training, drift retraining. Zero LLM rubric rows involved.
> Body below is kept as the historical record of what was planned/built; nothing further is executed against it. See `plan.md` Overview.

# Phase 10: ML core — MLflow, training pipeline, distributed training, drift

## Overview

The largest single block of ML rubric points, and the part with no production
substitute already in place. `requirements-phase2.txt` currently contains **no ML
library at all** — `src/ml/contracts.py` declares the abstract interfaces
(training, MLflow logging, registry alias resolution) but nothing implements them.

This phase implements them on the substrate the previous phases built.

## Requirements

- Functional: a training pipeline reads point-in-time-correct features from the
  Iceberg snapshot, trains a model, logs to MLflow, registers a version, and can
  be re-run reproducibly; distributed training is demonstrated; drift detection
  runs on a schedule and can trigger retraining through an API.
- Non-functional: every training run records its Iceberg snapshot ID, source
  commit SHA and image digest — reproducibility manifest complete.

## Architecture

**MLflow** for tracking and registry, backed by Postgres for metadata and MinIO
for artifacts. Current guidance is clear that production *monitoring* is outside
MLflow's core — drift, alerting and explainability need separate tooling — which
this plan already satisfies with Prometheus, Grafana and the drift module. So
MLflow is used for what it is genuinely best at and not stretched further.

**Distributed training.** The rubric names Kubeflow explicitly in one row
("Trigger retrain by calling Kubeflow API"). Full Kubeflow Pipelines is not viable
at this capacity budget; **Kubeflow Trainer operator standalone** provides the
distributed training primitive and an API surface to trigger from, at a fraction
of the footprint. This is a deliberate scope choice, recorded in an ADR, not an
omission.

**Drift.** Rather than adopting Evidently, compute PSI and KS statistics directly
against the Iceberg reference snapshot. The rubric does not name a tool, the
statistics are a few dozen lines against `numpy`/`scipy`, and computing them
in-repo means the drift result carries the snapshot ID natively — which keeps the
provenance chain intact. Adding a dependency here would break that.

**Point-in-time correctness** already has a home: `src/ml/leakage_guard.py` is
declared in the rubric matrix but absent from disk. It is implemented here against
Iceberg snapshots, which makes the guard checkable rather than assertional.

## Related Code Files

Source repo (all new or currently missing from disk):

- Create: `src/ml/mlflow_registry.py`, `leakage_guard.py`, `data_versioning.py`,
  `reproducibility_manifest.py`, `ab_router.py`
- Create: `src/ml/pipelines/training_pipeline.py`, `distributed_training.py`
- Create: `src/ml/drift/psi.py`, `ks.py`, `report.py`
- Create: `apps/feature-api/app/main.py`, `apps/drift-api/app/main.py`
- Create: `notebooks/ml-training.ipynb`
- Create: `dags/phase2/phase2_drift_monitoring.py` (thin wrapper)
- Create: `tests/platform/requirements/test_ml_ac_04_validation.py`
- Create: `docs/platform/adr/adr-014-kubeflow-trainer-scope.md`
- Modify: `requirements-phase2.txt` — `scikit-learn`, `xgboost`, `mlflow`, `scipy`

GitOps repo:

- Create: `charts/feature-api/`, `charts/drift-api/` (from the shared `fastapi-service` chart)
- Create: `platform/ml/mlflow.yaml`, `platform/ml/kubeflow-trainer.yaml`
- Create: `argocd/applications/platform-ml.yaml`

These paths are exactly the ones the phase 1 `--check-artifacts` run reports as
missing. This phase is where that 38-point source-side backlog is consumed.

## Implementation Steps

1. Add the ML dependencies. Verify the fast-loop test suite still runs in the
   expected time — a heavy import chain in a shared module would slow every test.
2. Deploy MLflow with Postgres and MinIO backends via Argo CD.
3. Implement `reproducibility_manifest.py` first, not last: snapshot ID, source
   SHA, image digest, environment digest. Everything downstream records through it.
4. Implement `leakage_guard.py` against Iceberg snapshots — assert no feature row
   has an event timestamp later than its label's decision timestamp.
5. Implement `training_pipeline.py`: snapshot-pinned read, leakage guard, train
   (logistic regression baseline plus XGBoost), evaluate, log to MLflow, register.
6. Implement `distributed_training.py` on Kubeflow Trainer; demonstrate a
   multi-worker run and capture it.
7. Implement the drift module (PSI, KS) and the scheduled `dags/phase2/` wrapper;
   wire the retrain trigger to the Trainer API.
8. Build the two FastAPI services — feature retrieval from the online store, and
   real-time drift detection — both async with pydantic validation, deployed via
   the shared parameterized Helm chart with `--atomic`.
9. Write `notebooks/ml-training.ipynb` demonstrating the modelling understanding
   the rubric asks for, reading from the same snapshot API.
10. Write the requirement tests and ADR-014.

## Verification

```bash
.venv/bin/python -m pytest tests/platform/requirements -k ml_ac
.venv/bin/python -m pytest tests -m "not slow"
.venv/bin/ruff check src dags tests scripts
.venv/bin/python scripts/audit_phase2_evidence.py --check-artifacts \
  --gitops-root ~/Studying/FSDS/financial-distress-gitops
```

## Success Criteria

- [ ] Training pipeline -> run twice against the same snapshot ID -> produces identical metrics
- [ ] Leakage guard -> given a deliberately leaked feature set -> fails with the offending rows named
- [ ] MLflow -> after a run -> shows the experiment, the registered version, and the full reproducibility manifest
- [ ] Distributed training -> submitted to Kubeflow Trainer -> completes across multiple workers, captured
- [ ] Drift DAG -> run against a drifted window -> emits PSI/KS above threshold and triggers retrain via API
- [ ] Both FastAPI services -> deployed with Helm `--atomic` -> healthy, async, pydantic-validated
- [ ] `--check-artifacts` -> after this phase -> source-side missing-artifact count drops to zero
- [ ] Strict `--track LLM` gate -> unchanged PASS 100/100

## ML rubric rows closed

- ML — Jupyter notebook demonstrating ML/DL understanding (2)
- ML Pipelines — training pipeline (2) and distributed training step (2)
- Versioning — model versioning (2)
- Web API for real-time drift detection — FastAPI + pydantic, async, Helm rolling
  update with auto fallback (6)
- Web API for data retrieval — same three rows (6)
- Feature Store — TTL definitions, offline and online push jobs, materialize (6)
- Observability — Airflow drift pipeline (1) and Kubeflow retrain trigger (1)
- Improve the Data Generator — simulate data drift, label table with id/label for
  training joins, and generator configuration (6). These live in `src/drift/` and
  `src/ml/label_pipeline.py`, **not** in the protected `src/generator/`, so they
  are legal work for this phase — confirm the distinction before starting.

Approximately 26 points. The single largest phase, and correctly so.

## Risk Assessment

- **Four days is the plan's biggest single estimate** and the most likely to slip.
  If it does, the cut order is: distributed training (2 pts) before the drift API,
  and the notebook before either — never the reproducibility manifest, which
  everything else records through.
- **Kubeflow Trainer CRDs may conflict with existing KServe/Knative CRDs.**
  Check CRD versions before installing; this class of mismatch is exactly what
  the plan's day-loss risk register warns about.
- **Adding heavy ML dependencies can slow the fast-loop test suite**, which
  currently runs 514 tests in under six seconds. Guard with lazy imports and
  measure after step 1.
