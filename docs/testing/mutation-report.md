# Mutation report

## Target-plan P11 scope

This report is for AC-P11-3. The target scope is:

- `src/ml/`
- `src/transforms/`
- `src/quality/`

The legacy Phase 05 report under `plans/260809-2039-complete-phase2-llm-submission/reports/` covers only `src/llm/rag/chunking.py` and must not be used as P11 evidence.

## Isolated pilot

`scripts/run_p11_mutation_gate.py` runs mutmut in a temporary project with a separate `pyproject.toml`, copied `src`, `tests`, and `docs`, while preserving the repository `tests/conftest.py` and appending alias registration. The isolated config includes `pythonpath`, markers, and `also_copy = ["docs", "src/ml"]` so the platform rubric fixture and non-target ML imports resolve inside the mutants tree.

Pilot module and tests:

- `src/ml/reproducibility_manifest.py`
- `tests/platform/verification/test_mutmut_target.py`
- `tests/platform/requirements/test_ml_ac_04_validation.py`

Corrected run result:

```text
186 total
31 killed
66 survived
0 timeout
89 no_tests
16.67% raw mutation score
```

The real ML validation selection now collects and passes 7 clean tests. The mutation run reaches actual mutants and kills 31; the remaining `No Tests` classifications are untested functions/branches in the pilot module, not infrastructure collection failures.

Artifact: `plans/260831-1644-rebuild-target-mlops-architecture/reports/p11-mutation-pilot-summary.json`.

The result is not acceptable P11 evidence because `no_tests > 0` and the score is below 90%. The untested branches and survivors require behavioral coverage or explicit justification.

## Current status

- Legacy Phase 05 mutmut configuration remains pinned to `src/llm/rag/chunking.py`; its CI gate is unchanged.
- Target P11 mutation runs use an isolated configuration/working directory because mutmut 3.7 reads `source_paths` from configuration and does not provide a scope override.
- Target-scope mutation score: pilot captured, target threshold not met.
- Survivor and `No Tests` justification: pending.
- Full target scope expansion: pending until this pilot's classifications are made meaningful.

No target-plan mutation AC is claimed complete by this document.
