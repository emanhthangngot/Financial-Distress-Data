# Mutation report

## Target-plan P11 scope

This report is for AC-P11-3. The target scope is:

- `src/ml/`
- `src/transforms/`
- `src/quality/`

The legacy Phase 05 report under `plans/260809-2039-complete-phase2-llm-submission/reports/` covers only `src/llm/rag/chunking.py` and must not be used as P11 evidence.

## Isolated pilot

`scripts/run_p11_mutation_gate.py` runs mutmut in a temporary project with a separate `pyproject.toml`, copied `src`, and the alias-based target test harness. The legacy Phase 05 configuration and cache are not reused.

Pilot module:

- `src/ml/reproducibility_manifest.py`
- alias test: `tests/platform/verification/test_mutmut_target.py`

Observed result:

```text
82 total
28 killed
54 survived
0 timeout
0 no_tests
34.15% mutation score
```

Artifact: `plans/260831-1644-rebuild-target-mlops-architecture/reports/p11-mutation-pilot-summary.json`.

The alias/import mechanism works: mutmut generated 82 mutants and classified all 82, with zero `No Tests`. The score is below the target threshold, so AC-P11-3 remains open. The surviving mutants require stronger behavioral tests before adding more target modules.

## Current status

- Legacy Phase 05 mutmut configuration remains pinned to `src/llm/rag/chunking.py`; its CI gate is unchanged.
- Target P11 mutation runs use an isolated configuration/working directory because mutmut 3.7 reads `source_paths` from configuration and does not provide a scope override.
- Target-scope mutation score: pilot captured, target threshold not met.
- Survivor justification: pending.
- Full target scope expansion: pending until the pilot's survivors are reduced or explicitly justified.

No target-plan mutation AC is claimed complete by this document.
