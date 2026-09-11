# Coverage report

## Target-plan P11 baseline

Coverage tooling was installed in both declared environments:

```text
uv pip install --python .venv/bin/python coverage pytest-cov
uv pip install --python .venv-platform/bin/python psycopg[binary] hypothesis
```

Coverage was collected in parallel and combined:

```text
rm -f .coverage .coverage.*
.venv/bin/python -m coverage run --parallel-mode \
  --source=src/ml,src/transforms,src/quality -m pytest tests -q
.venv-platform/bin/python -m coverage run --parallel-mode \
  --source=src/ml,src/transforms,src/quality -m pytest tests/platform -q || true
.venv/bin/python -m coverage combine
.venv/bin/python -m coverage report -m
```

Observed result:

```text
Core: 378 passed, 2 xfailed, 1 warning
Platform: 521 passed, 35 skipped, 15 failed, 44 errors
Combined: 1,955 statements, 489 missed, 75% total coverage
```

`pyproject.toml` enforces `fail_under = 90`, so the combined threshold still fails.

Important module results from the full combined run:

- `src/ml/ab_router.py`: 89%
- `src/ml/contracts.py`: 100%
- `src/ml/data_versioning.py`: 74%
- `src/ml/feast/feature_definitions.py`: 100%
- `src/ml/feast/materialization.py`: 21%
- `src/ml/feast/offline_job.py`: 49%
- `src/ml/feast/online_job.py`: 17%
- `src/ml/label_pipeline.py`: 93%
- `src/ml/mlflow_registry.py`: 23%
- `src/ml/pipelines/training_pipeline.py`: 85%
- `src/ml/reproducibility_manifest.py`: 98%
- `src/quality/contract_checker.py`: 87%
- `src/transforms/features/pit.py`: 97%

## Discovered platform findings

The full platform collection exposed findings outside P11 coverage work:

- 44 product/Postgres fixture errors caused by the phase-2 migration referencing `u.raw_user_meta_data` before that auth column exists.
- The original 15 non-product failures included six stale evidence mappings: six executed LLM CI/CD rows referenced the nonexistent `.github/workflows/platform-ci.yaml`, and two ML observability rows referenced nonexistent `dags/platform/phase2_drift_monitoring.py`. The canonical source now points those rows to the existing per-workflow files and `dags/drift_monitoring.py`.
- The remaining original non-product failures include missing executed LLM artifact paths and other evidence-contract issues; a post-repair full platform rerun is still required to establish the remaining count.
- 35 deliberate skips in the platform suite.

The mapping repair was validated by:

```text
scripts/audit_platform_evidence.py --matrix-only --strict: pass
pytest tests/platform/requirements/test_llm_ac_12_cicd.py: 6 passed
pytest tests/platform/test_rubric_row_contracts.py: 121 passed
```

Product/Postgres and remaining evidence findings are recorded for their owning work. They are not being fixed in P11 and are not used to invalidate the coverage measurement.

## Acceptance status

This is the most complete combined core + platform coverage baseline. AC-P11-1 remains open because several target ML modules are below 90%, the combined total is 75%, and the full platform run has separate product/evidence findings.
