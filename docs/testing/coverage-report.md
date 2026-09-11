# Coverage report

## Target-plan P11 baseline

Coverage tooling was installed in the passing core environment with:

```text
uv pip install --python .venv/bin/python coverage pytest-cov
```

Measured command:

```text
.venv/bin/python -m coverage run --parallel-mode \
  --source=src/ml,src/transforms,src/quality -m pytest tests -q
.venv/bin/python -m coverage combine
.venv/bin/python -m coverage report -m
```

Observed result:

```text
378 passed, 2 xfailed, 1 warning
1,955 statements
868 missed
56% total coverage
```

`pyproject.toml` enforces `fail_under = 90`, so the threshold fails correctly.

## Module gaps

The ML scope remains substantially below the target. Examples from the report:

- `src/ml/contracts.py`: 100%
- `src/ml/leakage_guard.py`: 68%
- `src/ml/data_versioning.py`: 0%
- `src/ml/reproducibility_manifest.py`: 0% in the core suite because its focused platform tests are not part of `tests/`
- `src/ml/training_pipeline.py`: 0%

The transforms and quality packages also contain modules below 90%, so AC-P11-1 remains open. This is a valid full-suite baseline: unlike the earlier platform attempt, collection completed without dependency errors.

## Environment interpretation

- Core `.venv`: complete repository suite passes and now has coverage tooling; measured total is 56%.
- Platform `.venv-platform`: focused platform tests pass, but the complete repository collection lacks `psycopg` and `hypothesis`.
- Target coverage acceptance remains open until the ML-track modules are exercised and every required module exceeds 90%.
