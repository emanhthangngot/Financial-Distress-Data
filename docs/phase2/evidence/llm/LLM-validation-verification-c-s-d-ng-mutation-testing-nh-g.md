# Evidence — Mutation testing (mutmut)

Proves `mutmut` scoped to `src/llm/rag/chunking.py` clears the >80% hard gate
declared verbatim in both the `requirement` and `deliverables` columns of the
canonical rubric CSV.

- rubric_id: LLM-validation-verification-c-s-d-ng-mutation-testing-nh-g
- execution_timestamp: 2026-08-10T13:05:00+07:00
- source_sha: 81aa31f087110f19ed7415f3976c6eb3d3563fbb
- gitops_sha: 921bdc1075ef8335e0f509747bd64db2d525f73e
- versions: mutmut 3.3.1, pytest 9.1.1
- command: `python scripts/run_phase5_mutation_gate.py`
- expected_result: mutation score on `llm.rag.chunking.*` strictly above 80%, with the surviving-mutant list recorded
- actual_result: 62/72 mutants killed, 9 survived, 1 timeout = **86.11%**, above the 80% gate; full record at `plans/260809-2039-complete-phase2-llm-submission/reports/phase05-mutation-summary.json` and `phase05-mutmut-results.txt`
- redaction_status: reviewed — no secrets, pure test tooling output

## Command output (real run)

```json
{
  "scope": "llm.rag.chunking.*",
  "minimum_score_exclusive": 80.0,
  "score": 86.11,
  "killed": 62,
  "survived": 9,
  "timeout": 1,
  "no_tests": 0,
  "total": 72,
  "mutmut_run_exit_code": 0
}
```
