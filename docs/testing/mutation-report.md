# Mutation report

## Target-plan P11 scope

This report is for AC-P11-3. The target scope is:

- `src/ml/`
- `src/transforms/`
- `src/quality/`

The legacy Phase 05 report under `plans/260809-2039-complete-phase2-llm-submission/reports/` covers only `src/llm/rag/chunking.py` and must not be used as P11 evidence.

## Current status

- Legacy Phase 05 mutmut configuration remains pinned to `src/llm/rag/chunking.py`; its CI gate is unchanged.
- Target P11 mutation configuration is not enabled in the legacy gate.
- A target run must use an isolated mutmut configuration/working directory because mutmut 3.7 reads `source_paths` from configuration and does not provide a scope override.
- Before widening the run, one target module must be exercised through the repository's alias-based mutmut test harness; direct `src.*` imports can be classified as `No Tests` by mutmut 3.7.
- Target-scope mutation run: pending.
- Survivor justification: pending until the target-scope run produces its complete survivor list.

No target-plan mutation score is claimed by this document yet.
