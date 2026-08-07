# Validation & Verification

Row: `LLM-AC-10-VALIDATION`. 60 executable requirement contract tests
(`tests/phase2/requirements/test_llm_ac_01..20_*.py`) — one parametrized case
per rubric row, node id = exact `rubric_id`, so each row's
`validation_command` selects exactly one case and never pytest's exit code 5.

- Generator: `scripts/generate_phase2_requirement_tests.py --check` (drift
  detector; not yet wired into a CI gate — noted as a phase-07 follow-up).
- `--track {ML,LLM}` filter on `scripts/audit_phase2_evidence.py` lets
  `--require-executed` gate one track without disturbing the other's
  canonical-coverage requirement (all 117 rows always required).
- `mutmut`, Hypothesis, equivalence/boundary testing, coverage >90%: **TBD
  phase-05**.

Status: contract-test harness live and passing (60 skipped — design_only
rows); mutation/property testing pending phase-05.
