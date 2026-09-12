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

The target test harness covers git source-SHA success/failure paths, `build_manifest` validation boundaries, and `manifest_from_env` source fallback, optional defaults, required-value failures, and runtime source fallback. The two digest assertions monkeypatch Python/platform identity to stable test values before asserting hard-coded hashes, avoiding self-referential comparisons and host-dependent results. It copies parametrized input dictionaries before mutation runs so mutmut's repeated in-process pytest calls do not alter test data.

## Before/after survivor counts

| Run | Scope | Total | Killed | Survivors | No tests | Timeout | Raw score |
|---|---|---:|---:|---:|---:|---:|---:|
| Previous pilot | `reproducibility_manifest.py` | 186 | 56 | 66 | 64 | 0 | 30.11% |
| Environment-wrapper tests | `reproducibility_manifest.py` | 186 | 138 | 48 | 0 | 0 | 74.19% |
| Latest pilot | `reproducibility_manifest.py` | 186 | 159 | 27 | 0 | 0 | 85.48% |
The latest run exceeds the rubric mutation-score requirement of `>80%` for the bounded pilot, but it does not satisfy the full target-plan scope yet. AC-P11-3 additionally requires every survivor to be killed or justified in writing; 27 survivors remain without individual disposition.

The latest direct target suite passes `16 tests`. A direct coverage run reports `100%` for `src/ml/reproducibility_manifest.py` (`55 statements, 0 missed`). This is module evidence, not a claim that all ML-track modules exceed the P11 90% requirement.

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
