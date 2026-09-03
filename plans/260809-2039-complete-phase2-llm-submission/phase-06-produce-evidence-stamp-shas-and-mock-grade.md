---
phase: 6
title: "Produce evidence, stamp SHAs and mock-grade"
status: in-progress
priority: P1
effort: "1.5d"
dependencies: [1, 2, 3, 4, 5]
---

# Phase 6: Produce evidence, stamp SHAs and mock-grade

## Overview

Write the last nine points, populate the reviewer-facing document set, execute
the SHA-stamping loop the phase-1 auditor fix made reachable, run the strict
two-repo audit, mock-grade independently against the canonical CSV, and
hibernate.

Rubric rows owned (9 points) — IDs and paths copied verbatim from the CSV:

| Points | rubric_id | artifact_path (authority) |
|---:|---|---|
| 2 | `LLM-demonstrate-basic-underst-jupyter-notebook-demonstrate-a` | source `notebooks/agent-mcp-demo.ipynb` |
| 2 | `LLM-demonstrate-basic-underst-jupyter-notebooks-to-demonstra` | source — **retargeted in phase 1** to a distinct second notebook |
| 2 | `LLM-novel-ideas-idea-1` | source `src/llm/embedding_registry.py` |
| 2 | `LLM-novel-ideas-idea-2` | source `src/llm/citation_guard.py` |
| 1 | `LLM-documentation-low-level-ml-design` | source `docs/platform/low-level-design.md` |

Both notebook rows shipped pointing at the same file; phase 1 gives the second
its own path so each row has distinct proof. The two novel ideas are **code
modules**, not just a prose document — `src/llm/embedding_registry.py` and
`src/llm/citation_guard.py` are what the generated tests assert exist.

## Current status — 2026-08-11

- Project manager -> records the five live Phase 06 artifact proofs ->
  `notebooks/agent-understanding-demo.ipynb`, `notebooks/agent-mcp-demo.ipynb`,
  `src/llm/embedding_registry.py`,
  `src/llm/citation_guard.py`, and `docs/platform/low-level-design.md` were
  captured -> live artifact capture is complete, while the five canonical
  evidence markdown files and SHA-stamping remain pending commit approval.
- Project manager -> preserves rubric honesty -> six observability rows and
  seven gateway rows remain `design_only` -> no live route, viewer, or
  observability proof is claimed for those rows.
- Cost owner -> records the infrastructure state -> the evidence GCP VM is
  stopped and the pool resize is still being verified -> final hibernation
  verification remains open.
- Project manager -> keeps this phase in progress -> canonical evidence,
  separate SHA commits, strict audit, mock-grade, and final hibernation
  verification remain open -> Phase 06 is not complete.

## Requirements

- Functional: two executed Jupyter notebooks; both novel ideas implemented as
  the named modules and proven; `docs/submission/*.md` populated; all 60 LLM
  evidence files carrying real 40-hex SHAs that satisfy the ancestor rule with
  clean worktrees; the strict auditor exiting 0 for every row not named in
  `--accept-design-only`.
- Non-functional: "designed", "configured", "executed" and "passed" stay
  distinct. Do not rewrite evidence to match a claim — if a scenario fails, fix
  the system, re-run, and replace its evidence atomically.

## Architecture

**Novel ideas**, as fixed in the unified plan and now bound to concrete modules:

- `src/llm/embedding_registry.py` — *embedding-version hot swap*: dual-read
  validation plus an alias change with no downtime and no mixed-vector query.
  Note the TEI embedding service runs `maxReplicas: 1`; phase 1's capacity work
  determines whether two revisions can co-exist, and if they cannot, the proof
  is a sequenced swap with dual-read validation rather than two live replicas.
- `src/llm/citation_guard.py` — *citation / PII guard*: unsupported or sensitive
  output is blocked or rewritten, and the decision is linked to its OTel trace
  and the evidence manifest. This also feeds phase 4's PII-safety metric.

**SHA stamping — now convergent.** platform .hanged the auditor to accept a
`source_sha`/`gitops_sha` that is HEAD **or an ancestor of HEAD**, provided the
diff from that commit to HEAD touches only SHA lines in evidence files. That
makes the loop terminate:

1. Commit everything in the GitOps repository; capture its `HEAD`.
2. Commit everything in the source repository; capture its `HEAD`.
3. Rewrite all 60 evidence files' `source_sha` and `gitops_sha`.
4. **Commit the stamp as its own commit** in each repository — no `--amend`.
   The stamped SHAs are then ancestors of HEAD and the only delta since is the
   SHA lines themselves, which is exactly what the auditor now allows.

GitOps is stamped first because the source evidence records both SHAs.

**Audit invocation.** `--track LLM` is what makes an LLM-only submission pass;
`--ml 100 --llm 100` still assert the *matrix* totals across all 117 rows, so
the ML deferral stays visible. Run it with `.venv-phase2` on `PATH`, not just as
the interpreter — the 60 `validation_command` subprocesses invoke `pytest` from
`PATH`, and resolving `.venv`'s or the system's `pytest` would run the wrong
tree at the final gate.

```bash
PATH="$PWD/.venv-phase2/bin:$PATH" \
.venv-phase2/bin/python scripts/audit_phase2_evidence.py \
  --strict --require-executed --run-validations --track LLM \
  --phase1-base "$PHASE1_BASE_SHA" \
  --gitops-root ~/Studying/FSDS/financial-distress-gitops \
  --ml 100 --llm 100
  # append --accept-design-only <rubric_id>,... for any row taken off the cut ladder
```

`PHASE1_BASE_SHA` is the immutable 40-hex commit immediately before platform .ork
— never a moving branch name.

**Grader access to the private GitOps repo.** Decision 2026-08-09: the control
repo stays private because it carries a committed `terraform.tfstate` (cluster
CA, control-plane endpoint, project ID) and `ansible/inventory.ini` (SSH user,
key path). This phase grants the grader read access and says so in
`docs/submission/README.md`; otherwise every `gitops_sha` link is a 404 at
grading time.

## Related Code Files

- Create: `notebooks/agent-mcp-demo.ipynb` and the second notebook at the path
  phase 1 retargeted
- Create: `src/llm/embedding_registry.py`, `src/llm/citation_guard.py`
- Create: `scripts/stamp_phase2_evidence.py`
- Create: `docs/platform/novel-ideas.md` (executed proof for both ideas)
- Modify: `docs/submission/README.md`, `iac.md`, `security.md`,
  `observability.md`, `ci_cd.md`, `cost.md`, `routing_gateway.md`,
  `validation_verification.md`
- Modify: `README.md` (TOC, repo map, numbered deployment diagram),
  `docs/coursework.md`, `docs/platform/low-level-design.md`,
  `docs/platform/evidence/index.md`
- Create: 5 evidence files under `docs/platform/evidence/llm/`
- Regenerate (never hand-edit): `tests/platform/requirements/test_llm_ac_07_agent_understanding.py`,
  `test_llm_ac_19_documentation.py`, `test_llm_ac_20_novel.py`

## Implementation Steps

1. `make gcp-up`. Write and execute both notebooks against the live MCP servers
   — one pulling from the feature store, one doing RAG retrieval. Commit them
   with outputs and substantive narrative cells.
2. Implement `src/llm/embedding_registry.py` and `src/llm/citation_guard.py` and
   prove both. Capture the hot swap as dual-read validation plus an alias change
   with query results before, during and after; the guard as a blocked or
   rewritten output linked to its trace ID.
3. Populate `docs/submission/*.md` — one file per rubric section, each **linking
   into** `docs/platform/evidence/` rather than duplicating it. `cost.md` records
   the per-session credit deltas since phase 1, including the evidence VM,
   against the < USD 100 target. `README.md` records the grader's GitOps read
   access and names any row taken off the cut ladder.
4. Update the root `README.md` with the numbered deployment diagram (every
   deployable a node, every primary edge described, with a flow legend), the
   repo map and the TOC. Update `docs/coursework.md` to state the LLM-only scope
   and the honest ML deferral.
5. Re-run the platform .ate (`.venv/bin/python scripts/run_stage1_quality_gates.py`)
   to prove no regression and that `.venv` was never mutated.
6. Flip the final five rows to `executed`, regenerate the CSV and requirement
   tests, and confirm all 60 LLM rows are `executed` except any cut row.
7. Write `scripts/stamp_phase2_evidence.py` implementing the four-step loop
   above (separate stamp commit, never `--amend`) and run it. Verify both
   worktrees clean and every evidence file's SHAs satisfying the ancestor rule.
8. Run the strict two-repo audit with the `PATH` fix. Fix every gap by fixing
   the system and re-capturing — never by editing the claim. The secret denylist
   phase 1 added runs here too; treat any hit as a real leak.
9. Grant the grader read access to `financial-distress-gitops` and verify one
   evidence link resolves for that account.
10. Mock-grade independently against the canonical LLM CSV, row by row, not
    against this plan's checklist.
11. `make gcp-down` (node pools to zero **and** the evidence VM stopped); record
    the final credit balance; confirm the trial billing account was never
    upgraded; freeze both 40-hex submission SHAs.

## Success Criteria

- [ ] Coursework reviewer -> opens the LLM rubric -> follows every scored row to an explained, executed, version-matched artifact, with any cut row named openly.
- [ ] Evidence auditor -> runs the strict command -> exits 0; the 57 ML rows remain visibly `design_only`; the secret denylist reports no hit.
- [ ] Maintainer -> checks any evidence file's SHAs -> finds 40-hex commits that are ancestors of both HEADs with only SHA lines changed since, and both worktrees clean.
- [ ] Grader account -> clicks a `gitops_sha` link -> reaches the private control repo instead of a 404.
- [ ] Reader -> opens a notebook -> sees an agent calling an MCP server against the live feature store and RAG path, with outputs committed.
- [ ] Reviewer -> reads `docs/platform/novel-ideas.md` -> finds working proof for both ideas backed by the two named modules, not descriptions.
- [ ] Reviewer -> opens `README.md` -> finds a numbered deployment diagram where every deployable is a node and every primary edge is described.
- [ ] Cost owner -> reads `docs/submission/cost.md` -> sees per-session deltas including the evidence VM, a final balance under USD 100 of the free-trial credit, and no billing upgrade.
- [ ] platform .aintainer -> runs the Stage 1 gate -> passes unchanged.

## Risk Assessment

- **Stamping was unsatisfiable before phase 1's auditor fix.** If that fix was
  skipped or weakened, this phase cannot pass — verify the ancestor rule works
  on a throwaway commit before running the real stamp.
- **`--run-validations` executes 60 subprocesses** and can blow the wall clock,
  and resolves `pytest` from `PATH`. Mitigation: the `PATH` prefix above, and
  keeping the requirement tests import-light — one heavy import multiplies by 60.
- **Screenshot staleness after a late fix.** Mitigation: manifest version checks
  reject mismatched SHA/digest/timestamps; a late fix means re-capturing that
  scenario's evidence atomically.
- **Mock grading against the plan instead of the CSV** would launder gaps.
  Mitigation: step 10 grades from the canonical LLM CSV directly.
- **Novel idea 2 is cut-ladder entry 3 and the second notebook entry 5.**
  Cutting either requires naming the row in `--accept-design-only` and in
  `docs/submission/README.md`.
- Rollback: revert the bad release, re-run the affected scenario, replace its
  evidence atomically, re-audit. Never rewrite evidence to match a claim.
