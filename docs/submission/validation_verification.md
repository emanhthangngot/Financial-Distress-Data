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

## Phase 05 static CI gates

Run these commands from the repository root with the Phase 2 dependencies
installed:

```bash
.venv/bin/python scripts/run_phase5_web_gate.py
.venv/bin/python scripts/run_phase5_mutation_gate.py
```

- The Web API gate runs the fixture/mock, equivalence/boundary, and adapter
  tests while measuring `apps/feature-mcp/app/main.py` and
  `apps/drift-mcp/app/main.py`. It requires both line and branch coverage to
  be at least 90%.
- The mutation gate runs `mutmut` against the declared pure subset
  `llm.rag.chunking.*` and requires a score strictly greater than 80%.
- The verified source-level run reported 60 passed and 6 skipped, 96.17% line
  coverage, 93.48% branch coverage, and 62 of 72 mutants killed (86.11%).
  These results are static gate verification, not a deployed-service claim.

The reusable Phase 2 workflow executes both gates after its test job and
before image builds.

## Live evidence outstanding

No Locust HTML, cold/warm measurement, signed release, GitOps rollout, or live
A/B result exists while the cluster is unavailable. The A/B model path is not
yet proven connected to the live agentgateway path, and warm-pool scale-down
still needs an evidence-window/HPA control design. Keep the associated rubric
rows `design_only` until runtime evidence exists.
