# Plan sync — production-hardening-overlay vs 11-commit ML descope

Scope: sync `plans/260813-1846-production-hardening-overlay/{plan.md,phase-01-start.md,phase-02-gitops-validation-gate.md}`
against source repo HEAD 4f62226 + gitops HEAD 1d0ebb6. Overview/Contract/Goals
already rewritten this session — this pass only touches status cells and
checkboxes. Files edited, none committed.

## Tooling constraint

This subagent session has no Bash tool — could not re-run pytest/audit/gate
commands live. Verification instead done by: (1) reading source files that
implement each claimed fix directly (`.githooks/pre-commit`,
`configs/evidence-checklist.yaml`, `scripts/phase2_ci/gitops_paths.py`,
`scripts/audit_phase2_evidence.py` PHASE1_PROTECTED, `pyproject.toml`,
`docker-compose.yml`, `.github/workflows/`), (2) cross-checking the two most
recent independent reports already in the repo
(`plans/reports/audit-260814-0734-hardening-followup-verification.md`,
`plans/reports/code-reviewer-260814-1017-ml-descope-review.md`), (3) trusting
the orchestrating agent's stated final-state command outputs only where a
static file check corroborates the same conclusion. Any checkbox below not
backed by one of these is left unchecked — flagged per item.

## plan.md changes

- platform .tatus cell: reworded — `validate-gitops.yml` CI workflow is
  committed and passes locally now (confirmed: file exists at
  `../financial-distress-gitops/.github/workflows/validate-gitops.yml`,
  digest-pin + secret-scan logic present in `validate-gitops.sh:162-213`) —
  but no PR was opened to prove it actually blocks a bad merge, so left that
  half open.
- Success Criteria: checked 3 of 6 (strict LLM 100/100, zero missing
  `artifact_path`, ML artifacts archived+excluded+non-fatal). Left 3
  unchecked: `capture_phase2_evidence.py` full regen (not run this session),
  GitOps CI blocking proof (no PR), and `infra/`+`docker-compose.yml` fully
  phase-name-free (false — `docker-compose.yml:216-249` still has
  `phase2-redis`/`phase2-postgres`/`phase2-pgdata`; `infra/phase1-cluster/`
  still exists un-flattened; `grep -rn 'phase2' infra docker-compose.yml`
  still hits). This matches phase-01's own Tier-1-renames-pending status —
  no drift between plan.md and phase-01.

## phase-01-start.md changes

Checked 2 new boxes:
- `baseline.md` records green outputs + both HEAD SHAs — file exists, records
  6 checks (matrix, fast loop, compose, stage-1 audit, ruff, black) plus both
  repo HEADs.
- `PHASE1_PROTECTED` extended — confirmed in `scripts/audit_phase2_evidence.py:61-103`:
  all six packages present, five file-level exceptions (more than the two
  originally scoped — three lakehouse contract files added). Gate re-run
  clean per the strict LLM 100/100 result.

Left unchecked, with notes added:
- Pre-commit hook "refuses the commit" — hook logic is correct and was fixed
  per code review (exceptions now synced with `PHASE1_PROTECTED_EXCEPTIONS`,
  diff now HEAD-relative) but nobody actually staged a protected-path edit
  and watched it get rejected this session, and no test file covers it.
- `src/generators/` deletion — no tracked `.py` source remains (it was
  already untracked before this plan), but stale `__pycache__/*.pyc` files
  are still on disk. Ambiguous whether this counts as "done"; left open.
- Tier 1 renames, `pyproject.toml` consolidation, `requirements*.txt`
  deletion, single-venv proof, `test_no_heavy_imports_at_module_scope`,
  8-workflow rename, `AGENTS.md` scope-relaxation text — all verified
  **not done** by direct file check (`requirements.txt`/`requirements-phase2.txt`
  both still exist, `pyproject.toml` still only declares `pandas`/`pyyaml` +
  `dev`/`runtime` extras with no `ml` extra, all 8 `phase2-*.yaml` workflow
  files still present under original names, `AGENTS.md` has no scope-relaxation
  or 19-package table text). Consistent with plan.md's own "remains future
  work" resolution note — no change needed, just confirmed still true.

## phase-02-gitops-validation-gate.md changes

Left the 3 open boxes unchecked but added evidence notes: digest-pin check
and secret-shaped-pattern grep both exist and are implemented correctly in
`validate-gitops.sh`, but none of the three remaining criteria (bad-manifest
rejection, bad-secret rejection, CI blocking a real PR) were exercised this
session — they need an actual negative-case run, not just code inspection.

## phase-03..12 banners

Read all 10 cancellation banners. 9 are self-consistent with final state.
One stale reference fixed: phase-09's banner said `infra/phase1-cluster/`
is "untracked, never wired into any active workflow" — true when phase 9 was
cancelled, but commit #5 in this session committed it (archived) into git.
Updated the banner to say it's "now committed as-is in the ML-scaffolding
archive commit." No other banner needed a fix — phase-03's fork-PR-fix note
and phase-12's evidence-tooling note both already correctly describe what was
kept vs. reverted.

## Overstatement check

No checkbox was left checked without a corresponding verification note. Three
previously-checked boxes in phase-01/phase-02 (`--check-artifacts`,
`--matrix-only --strict`, infra flatten, `validate-gitops.sh` exit 0,
`run_phase2_quality_gates.py`, unchanged strict-LLM PASS) were already correct
going in and were not touched. The plan.md top-level Success Criteria item 1
(strict 100/100) is now checked based on corroborating static evidence (the
three code-review-flagged bugs are verifiably fixed on disk) plus the
orchestrating session's reported final gate run — this is the one item where
I could not independently re-execute the exact command myself; flagged as
such above rather than silently trusting it.

## Unresolved questions

1. Can't independently re-run `audit_phase2_evidence.py --require-executed
   --run-validations --track LLM ...` or the two pytest suites without Bash
   access in this session — recommend the user (or a session with Bash) do
   one final live re-run before treating the plan.md item-1 checkbox as fully
   closed.
2. Is the strict-LLM-gate 100/100 claim durable across a future merge to
   `main`? Code review already flagged that merging this branch will itself
   invalidate all 60 evidence SHA stamps (diff against the frozen base picks
   up non-SHA changes) — a post-merge re-stamp commit is still owed and is
   not tracked as a checkbox anywhere in this plan.
3. Phase 1's own Success Criteria list 13 of 19 boxes still unchecked (Tier 1
   renames, dependency consolidation, single-venv, workflow renames,
   `AGENTS.md` updates). Per the plan's own 2026-08-14 resolution these are
   "future work, not executed in this pass" — but the phase-level `status`
   frontmatter still says `in_progress`, not `partial`/`done-for-submission`.
   Confirm with the user whether phase 1 should be marked complete-for-LLM-
   submission-purposes now, or left `in_progress` until Tier 1 lands.

## IMPORTANT — plan not finished

platform .lone still has 13 open success-criteria items (dependency
consolidation onto `pyproject.toml`, both `requirements*.txt` deletion,
single-venv proof, `test_no_heavy_imports_at_module_scope`, 8-workflow
rename, Tier 1 compose/service renames, `AGENTS.md` updates, pre-commit hook
live-tested). platform .as 3 open items (negative-case script tests, live PR
CI-blocking proof). Please have the main agent continue executing
`phase-01-start.md` Implementation Steps 9-12 and the remaining
`phase-02-gitops-validation-gate.md` verification steps rather than treating
this plan as done — the LLM gate passing 100/100 closes the plan's headline
acceptance criterion, but the plan's own phase-level task lists are not yet
complete and should not be abandoned mid-way.
