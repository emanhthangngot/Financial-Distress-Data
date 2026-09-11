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
  --source=src/ml,src/transforms,src/quality -m pytest \
  tests/platform/requirements/test_ml_ac_04_validation.py \
  tests/platform/verification/test_mutmut_target.py -q
.venv/bin/python -m coverage combine
.venv/bin/python -m coverage report -m
```

Observed result:

```text
Core: 378 passed, 2 xfailed, 1 warning
Platform ML selection: 13 passed
Combined: 1,955 statements, 605 missed, 69% total coverage
```

`pyproject.toml` enforces `fail_under = 90`, so the combined threshold still fails.

Important module results:

- `src/ml/reproducibility_manifest.py`: 98%
- `src/ml/ab_router.py`: 89%
- `src/ml/data_versioning.py`: 74%
- `src/ml/pipelines/training_pipeline.py`: 85%
- `src/ml/feast/materialization.py`: 21%
- `src/ml/label_pipeline.py`: 0%
- `src/quality/contract_checker.py`: 87%
- `src/transforms/features/pit.py`: 97%

This is now a valid combined core + collectible platform ML baseline. AC-P11-1 remains open because the target ML-track modules are not all above 90% and the full platform suite still has unrelated PostgreSQL/rubric failures.
