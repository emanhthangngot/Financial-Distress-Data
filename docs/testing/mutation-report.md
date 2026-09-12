# Mutation report

## Target-plan P11 scope

This report is for AC-P11-3. The required target scope is:

- `src/ml/`
- `src/transforms/`
- `src/quality/`

The legacy Phase 05 report under `plans/260809-2039-complete-phase2-llm-submission/reports/` covers only `src/llm/rag/chunking.py` and must not be used as P11 evidence.

## Isolated pilot

`scripts/run_p11_mutation_gate.py` runs mutmut in a temporary project with a separate `pyproject.toml`, copied `src`, `tests`, and `docs`, while preserving the repository `tests/conftest.py` and appending alias registration. The isolated config includes `pythonpath`, markers, and `also_copy = ["docs", "src/ml"]` so the platform rubric fixture and target ML imports resolve inside the mutants tree.

Pilot module and tests:

- `src/ml/reproducibility_manifest.py`
- `tests/platform/verification/test_mutmut_target.py`
- `tests/platform/requirements/test_ml_ac_04_validation.py`

The target test harness covers git source-SHA success/failure paths, `build_manifest` validation boundaries, and `manifest_from_env` source fallback, optional defaults, and required-value failures. It copies parametrized input dictionaries before mutation runs so mutmut's repeated in-process pytest calls do not alter test data.

## Before/after survivor counts

| Run | Scope | Total | Killed | Survivors | No tests | Timeout |
|---|---|---:|---:|---:|---:|---:|
| Previous pilot | `reproducibility_manifest.py` | 186 | 56 | 66 | 64 | 0 |
| Latest pilot | `reproducibility_manifest.py` | 186 | 138 | 48 | 0 | 0 |

The latest raw mutation score is `74.19%`. Score is reported for diagnosis only; AC-P11-3 is governed by survivor count and written disposition, not an invented percentage threshold.

The latest direct target suite passes `14 tests`. The new environment-wrapper cases eliminated all 64 previous `No Tests` mutants; 48 survivors remain and have not yet been individually killed or justified. The report therefore does not claim AC-P11-3 complete.

Artifact: `plans/260831-1644-rebuild-target-mlops-architecture/reports/p11-mutation-pilot-summary.json`.

## Next mutation work

1. Inspect the remaining 48 survivors and add behavioral cases where a real invariant is missing.
2. Record a disposition for every remaining survivor: killed by a behavioral case or justified with the mutation name and invariant it does not violate.
3. Expand `TARGET_MODULES` to `src/ml/`, `src/transforms/`, and `src/quality/` only after the bounded module pilot has complete survivor disposition.

## Legacy separation

- Legacy Phase 05 mutmut configuration remains pinned to `src/llm/rag/chunking.py`; its CI gate is unchanged.
- Target P11 mutation runs use an isolated configuration/working directory because mutmut 3.7 reads `source_paths` from configuration and does not provide a scope override.

No target-plan mutation AC is claimed complete by this document.
