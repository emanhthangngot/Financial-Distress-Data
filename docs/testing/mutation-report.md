# Mutation report

## Target-plan P11 scope

This report is for AC-P11-3. The target scope is:

- `src/ml/`
- `src/transforms/`
- `src/quality/`

The legacy Phase 05 report under `plans/260809-2039-complete-phase2-llm-submission/reports/` covers only `src/llm/rag/chunking.py` and must not be used as P11 evidence.

## Isolated pilot

`scripts/run_p11_mutation_gate.py` runs mutmut in a temporary project with a separate `pyproject.toml`, copied `src` and `tests`, and the alias-based target test harness. The legacy Phase 05 configuration and cache are not reused. The harness resolves the loaded file from mutmut's `<workdir>/mutants` tree and asserts that root is named `mutants`.

Pilot module:

- `src/ml/reproducibility_manifest.py`
- alias test: `tests/platform/verification/test_mutmut_target.py`

Corrected run result:

```text
186 total
28 killed
69 survived
0 timeout
89 no_tests
15.05% raw mutation score
```

Artifact: `plans/260831-1644-rebuild-target-mlops-architecture/reports/p11-mutation-pilot-summary.json`.

This run proves the isolated source configuration and mutant-tree path, but it is not an acceptable P11 score because 89 mutants were classified as `No Tests`. The untested branches must be covered or explicitly excluded before using the score as acceptance evidence.

## Current status

- Legacy Phase 05 mutmut configuration remains pinned to `src/llm/rag/chunking.py`; its CI gate is unchanged.
- Target P11 mutation runs use an isolated configuration/working directory because mutmut 3.7 reads `source_paths` from configuration and does not provide a scope override.
- Target-scope mutation score: pilot captured but invalid for acceptance due to `No Tests` classifications.
- Survivor and `No Tests` justification: pending.
- Full target scope expansion: pending until the pilot's classifications are made meaningful.

No target-plan mutation AC is claimed complete by this document.
