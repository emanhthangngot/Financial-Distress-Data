---
phase: 6
title: "Freeze the submission — docs first, stamp last, mock-grade, hibernate"
status: pending
priority: P1
effort: "0.75d (no cluster)"
dependencies: [5]
---

# Phase 6: Freeze the submission — docs first, stamp last, mock-grade, hibernate

# 0 points

## Overview

Turn a passing repository into a submittable one. The step order is the point:
the previous draft stamped first and then wrote documents, which invalidates the
stamp it just produced.

## Requirements

- Functional: every document, report and ledger written **and committed** before
  the stamp; both worktrees clean; all 60 evidence files carrying convergent
  SHAs; the strict two-repo gate exiting 0 with no `--accept-design-only`; a
  scrubbed GitOps mirror published for the grader; a row-by-row mock grade
  against the canonical CSV.
- Non-functional: `.venv` untouched; the platform .stage 1) gate green; no evidence
  rewritten to match a claim.

## Architecture

**Why docs come first.** `_audit_frozen_revisions` requires clean worktrees, and
`_only_evidence_sha_lines_changed` (`scripts/audit_phase2_evidence.py:609-638`)
requires that every commit after each evidence file's SHA touch only
`source_sha`/`gitops_sha` lines under `docs/platform/evidence/`. So any commit of
`cost.md`, `README.md`, `docs/coursework.md`, the window log, or the mock-grade
report **after** stamping invalidates all 60 rows. Order: write everything →
commit everything → stamp → gate → stop.

A corollary the previous draft got wrong: "record the final submission SHA in a
tracked file" is impossible by construction — writing it changes HEAD. Either
publish the SHA outside the repository (the submission form), or state
explicitly that the recorded value names the pre-stamp commit.

**Convergent stamping.** `scripts/stamp_phase2_evidence.py` commits the
implementation, commits the evidence with its captured body, then makes one
SHA-lines-only commit per repository. Never `--amend`. GitOps is stamped first
because source evidence records both SHAs. Verify the ancestor rule on a
throwaway commit before the real run.

```bash
.venv-phase2/bin/python scripts/stamp_phase2_evidence.py \
  --gitops-root ~/Studying/FSDS/financial-distress-gitops \
  --source-path <paths> --gitops-path <paths>
```

**The final gate**, with `PATH` prefixed so the ~60 `validation_command`
subprocesses resolve `pytest` from `.venv-phase2`:

```bash
PATH="$PWD/.venv-phase2/bin:$PATH" \
.venv-phase2/bin/python scripts/audit_phase2_evidence.py \
  --strict --require-executed --run-validations --track LLM \
  --phase1-base ddbcbe7bd41ae4883954b8a247efdc67c7329078 \
  --gitops-root ~/Studying/FSDS/financial-distress-gitops \
  --ml 100 --llm 100
```

No `--accept-design-only` unless a cut was taken — and then the same rows are
named in `docs/submission/README.md`.

**Grader access via a scrubbed mirror** (user decision, 2026-08-11). The control
repo carries a committed `terraform/gcp/terraform.tfstate` (control-plane
endpoint, project ID, authorized networks) and `ansible/inventory.ini` (SSH user,
key path, IAP ProxyCommand) — the auditor's own denylist treats two of those
values as leaks. Granting read access to the original would hand over live
infrastructure detail. Instead publish a read-only mirror containing only
`platform/`, `apps/`, `charts/`, `argocd/`, and point every `gitops_sha`
reference at the mirror's corresponding commit. The mirror must be built by a
scripted filter (so it is reproducible and reviewable), and verified to contain
no tfstate, tfvars, inventory, or key material before it is made visible.

**Mock grading is against the canonical CSV**
(`docs/Coursework Tracking (Public) - rubic final-coursework (final - llm).csv`),
row by row — not against this plan. For each row: points available, evidence
file, artifact, points a hostile grader would award, one-line reason.

## Related Code Files

- Modify: `docs/submission/cost.md`, `docs/submission/README.md`
- Modify: `README.md` (numbered deployment diagram, repo map, TOC), `docs/coursework.md`
- Create: `plans/260811-1627-close-llm-rubric-to-100/reports/mock-grade-<date>-llm.md`
- Create: a mirror-publishing script (scripted filter, not a manual copy)
- Modify (by script only): all `docs/platform/evidence/llm/*.md` SHA lines
- Read-only: `scripts/stamp_phase2_evidence.py`, `scripts/audit_phase2_evidence.py`

## Implementation Steps

1. Write everything that is not evidence: `docs/submission/cost.md` (per-session
   credit deltas including the evidence VM, final balance, explicit confirmation
   the trial account was never upgraded — replace every "TBD"), the corrected
   `docs/submission/README.md`, the root `README.md` (numbered deployment
   diagram where every deployable is a node and every primary edge is described,
   repo map, TOC), `docs/coursework.md` (LLM-only scope, honest ML deferral), the
   window logs, and the mock grade (step 2).
2. Mock-grade row by row from the canonical CSV. If the total is below 100, name
   exactly which rows lost points and why. Do this **before** the stamp so its
   report can be committed with everything else.
3. Build and publish the scrubbed GitOps mirror with the scripted filter; verify
   it contains no tfstate/tfvars/inventory/key material; record the mirror URL and
   the source↔mirror commit mapping in `docs/submission/README.md`.
4. Commit everything from steps 1-3 in both repositories. Confirm both worktrees
   are clean.
5. Verify the ancestor rule on a throwaway commit, then run
   `scripts/stamp_phase2_evidence.py` — GitOps first, then source, one dedicated
   stamp commit each. Never `--amend`.
6. Run the final gate. Expect `platform .ubric matrix is complete and consistent.`
   Commit nothing afterwards. If a gap appears, fix the system, re-capture that
   scenario, and repeat from step 4 — not by editing a claim.
7. Re-run the stage 1 gate: `.venv/bin/python scripts/run_stage1_quality_gates.py`
   → exit 0, proving `.venv` was never mutated.
8. Deliver the gateway credential out of band through the channel chosen in phase
   2. Record only the fact of delivery.
9. Confirm hibernation: `make gcp-status` → both pools at 0 nodes, evidence VM
   stopped. Publish the two frozen 40-hex submission SHAs through the submission
   form, not by editing a tracked file after the stamp.

## Success Criteria

- [ ] Auditor -> runs the final gate with no `--accept-design-only` -> exits 0; 60 LLM rows executed; 57 ML rows visibly `design_only`.
- [ ] Maintainer -> checks any evidence file's SHAs -> 40-hex ancestors of both HEADs, only SHA lines changed since, both worktrees clean, and nothing committed after the stamp.
- [ ] Stage 1 maintainer -> runs the stage 1 gate -> exit 0, unchanged.
- [ ] Cost owner -> reads `cost.md` -> per-session deltas including the evidence VM, a final balance, no billing upgrade, no "TBD".
- [ ] Grader account -> opens the scrubbed mirror at a referenced commit -> reaches the manifests, and finds no tfstate, tfvars, inventory or key material anywhere in it.
- [ ] Reviewer -> opens `README.md` -> a numbered deployment diagram where every deployable is a node and every primary edge is described.
- [ ] Reviewer -> opens the mock-grade report -> a row-by-row grade against the canonical CSV with an explicit total.
- [ ] Cost owner -> runs `make gcp-status` -> primary 0 nodes, secondary 0 nodes, evidence VM stopped.

## Risk Assessment

- **Any commit after the stamp** → all 60 rows fail the frozen-revision rule.
  Mitigation: the step order above; step 6 is the last action that touches either
  repository.
- **The mirror leaks anyway** → the very exposure the decision avoided.
  Mitigation: scripted filter plus an explicit pre-publication grep for tfstate,
  tfvars, `inventory`, `BEGIN ... PRIVATE KEY`, and the denylisted identifiers.
- **Mirror commit mapping is wrong** → `gitops_sha` references resolve to
  unrelated content. Mitigation: record the mapping and verify one reference end
  to end as the grader would.
- **Mock-grading against the plan** → laundered gaps and a false 100. Mitigation:
  step 2 grades from the CSV file directly.
- **A denylist hit at the final gate** → treat as a real leak: rotate the
  credential, re-capture, never edit the file to hide it.
- Rollback: revert the stamp commit, re-capture the affected evidence, re-stamp,
  re-audit.
