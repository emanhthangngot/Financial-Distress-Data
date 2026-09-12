# Mutation report

## Target-plan P11 scope

This report is for AC-P11-3. The required target scope is:

- `src/ml/`
- `src/transforms/`
- `src/quality/`

The legacy Phase 05 report under `plans/260809-2039-complete-phase2-llm-submission/reports/` covers only `src/llm/rag/chunking.py` and must not be used as P11 evidence.

## Isolated pilot

The isolated config includes `pythonpath`, markers, and `also_copy = ["docs", "src/ml", "src/quality", "src/transforms", "src/metadata"]` so all target modules and their schema dependency resolve inside the mutants tree.


Pilot modules and tests:

- `src/ml/reproducibility_manifest.py`
- `src/quality/dq_checks.py`
- `src/transforms/silver/core.py`
- `tests/platform/verification/test_mutmut_target.py`
- `tests/platform/requirements/test_ml_ac_04_validation.py`
- `tests/test_dq_checks.py`
- `tests/test_bronze_to_silver.py`

## Before/after survivor counts

| Run | Scope | Total | Killed | Survivors | No tests | Timeout | Raw score |
|---|---|---:|---:|---:|---:|---:|---:|
| Previous pilot | `reproducibility_manifest.py` | 186 | 56 | 66 | 64 | 0 | 30.11% |
| Environment-wrapper tests | `reproducibility_manifest.py` | 186 | 138 | 48 | 0 | 0 | 74.19% |
| Latest bounded pilot | `reproducibility_manifest.py` | 186 | 159 | 27 | 0 | 0 | 85.48% |
| Latest expanded pilot | `reproducibility_manifest.py`, `dq_checks.py`, `silver/core.py` | 692 | 427 | 265 | 0 | 0 | 61.71% |

The expanded run exercises all three bounded target modules with the platform verification tests plus
the existing DQ and Bronze→Silver suites. It eliminates the prior no-test bucket, but it does not
satisfy AC-P11-3: 265 mutants still require individual kill-or-justify disposition. The earlier
single-module pilot exceeded the rubric mutation-score requirement; the expanded score is not a
passing gate.

Artifacts:

- `plans/260831-1644-rebuild-target-mlops-architecture/reports/p11-mutation-pilot-summary.json`
- `plans/260831-1644-rebuild-target-mlops-architecture/reports/p11-mutmut-pilot-results.txt`

## Next mutation work

1. Inspect the remaining 29 survivors and add behavioral cases where a real invariant is missing.
2. Record a disposition for every remaining survivor: killed by a behavioral case or justified with the mutation name and invariant it does not violate.
3. Expand `TARGET_MODULES` to `src/ml/`, `src/transforms/`, and `src/quality/` only after the bounded module pilot has complete survivor disposition.

## Legacy separation

- Legacy Phase 05 mutmut configuration remains pinned to `src/llm/rag/chunking.py`; its CI gate is unchanged.
- Target P11 mutation runs use an isolated configuration/working directory because mutmut 3.7 reads `source_paths` from configuration and does not provide a scope override.

No target-plan mutation AC is claimed complete by this document.
