# Coverage report

## Target-plan P11 baseline

Command attempted with the declared platform environment:

```text
.venv-platform/bin/python -m coverage run --parallel-mode \
  --source=src/ml,src/transforms,src/quality -m pytest tests -q
.venv-platform/bin/python -m coverage combine
.venv-platform/bin/python -m coverage report -m
```

Observed result:

```text
Coverage: 22%
Statements: 1,955
Missed: 1,519
```

`pyproject.toml` enforces `fail_under = 90`, so this baseline correctly fails the threshold.

The collection also reports three platform-environment dependency failures:

- `psycopg` missing for `tests/platform/pipelines/test_pgvector_store.py` and `tests/platform/product`.
- `hypothesis` missing for `tests/platform/verification/test_idempotency.py`.

Therefore this is a captured baseline, not AC-P11-1 completion evidence. Coverage must be rerun after the declared environments are dependency-complete and the ML, transforms, and quality test partitions are exercised.

## Current interpretation

- Core `.venv` quality gate: `378 passed, 2 xfailed`; it does not currently provide the coverage plugin.
- Platform `.venv-platform`: provides coverage, but the complete repository collection is dependency-incomplete.
- Target coverage acceptance remains open until the report shows every ML-track module above 90% and the command completes without collection errors.
