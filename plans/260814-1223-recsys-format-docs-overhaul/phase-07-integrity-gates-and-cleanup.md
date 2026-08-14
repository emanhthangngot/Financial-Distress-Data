---
phase: 7
title: "Integrity gates, cleanup, and freeze"
status: in_progress
priority: P1
effort: "0.5d"
dependencies: [1, 2, 3, 4, 5, 6]
---

# Phase 7: Integrity gates, cleanup, and freeze

## Overview

Retire what the new layer replaced, prove nothing broke, and leave the repo in a
state where a grader's every click lands somewhere real.

## Requirements

- Functional: retired docs are deleted only after their claims exist in the new
  set and every inbound link is rewired.
- Functional: all quality gates green — doc gate, Phase 2 evidence audit, and
  the Stage 1 one-shot gate.
- Functional: image copies in `docs/pngs/` still match their manifest sources.
- Non-functional: no evidence SHA stamp left stale after the docs commits, per
  the existing freeze checklist in `docs/submission/README.md`.

## Architecture

Gate order matters — cheapest and most localized first:

```text
1. link + size gate      scripts/check_documentation.py
2. evidence audit        scripts/audit_phase2_evidence.py --track LLM
3. code gate             scripts/run_stage1_quality_gates.py
4. manual sweep          orphan images, orphan docs, index-table diff,
                         code-quote freshness
5. SHA restamp           scripts/stamp_phase2_evidence.py (after last commit)
```

## Related Code Files

- Delete (after rewiring): the absorbed `docs/*.md` marked in Phases 1 and 5,
  the flat `docs/submission/*.md` absorbed in Phase 4
- Modify: any file whose links pointed at a retired doc
- Modify: `docs/evidence-index.md` — either becomes the pointer into the new
  submission layer or is retired
- Run: `scripts/stamp_phase2_evidence.py`, `scripts/audit_phase2_evidence.py`,
  `scripts/check_documentation.py`, `scripts/run_stage1_quality_gates.py`

## Implementation Steps

1. Inbound-link sweep: for every doc marked for retirement, grep the whole repo
   for links to it. Rewire each to the new owner. Only then delete.
2. Claim diff: for each retired doc, confirm every rubric-relevant claim it made
   exists in the new set. Anything unmatched is restored, not dropped.
3. Orphan sweep both directions: images in `docs/pngs/` referenced by no doc,
   and doc image references pointing at a missing file.
4. Manifest integrity: for each `docs/pngs/` image marked as a copy, verify it
   still matches the source path recorded in the manifest.
5. Index-table diff: README's three tables versus the Phase 4/5 index READMEs.
   Same rows, same links, no drift.
6. Code-quote freshness: re-verify each quoted snippet against its linked file
   at the final commit. A quote that no longer matches is a broken claim.
7. Run the gates in order. Fix forward — never weaken a gate or raise the doc
   line cap to make a doc pass.
8. Restamp evidence SHAs with `scripts/stamp_phase2_evidence.py` after the final
   docs commit, then re-run the audit. This is the existing freeze requirement
   already recorded in `docs/submission/README.md`.
9. Write the completion report to
   `plans/reports/docs-260814-recsys-format-overhaul.md`: what shipped, what was
   retired, which captures were reused rather than re-taken, and any rubric row
   whose evidence remains weaker than its narrative suggests.
10. Ship via PR to `dev` per `AGENTS.md` — no direct push to `main`.

## Success Criteria

- [ ] Zero broken links repo-wide; `check_documentation.py` exits 0
- [ ] `audit_phase2_evidence.py --track LLM` reports no new findings versus the
      pre-change baseline
- [ ] `run_stage1_quality_gates.py` exits 0
- [ ] No orphan image in `docs/pngs/`; no doc references a missing image
- [ ] Every retired doc's claims verified present in the new set before deletion
- [ ] README index tables match the Phase 4/5 index tables exactly
- [ ] Every code quote matches its linked file at the final commit
- [ ] Evidence SHAs restamped after the last docs commit and the audit re-run
- [ ] Completion report written; PR opened against `dev`

## Risk Assessment

- **Risk:** deleting a doc still referenced by the audit matrix or a rubric row,
  turning a green gate red at freeze time.
  **Mitigation:** step 1's inbound-link sweep precedes every deletion, and the
  audit runs before the PR.
- **Risk:** SHA restamp loops — restamping creates a commit, which invalidates
  the stamp.
  **Mitigation:** this repo already handles it with a dedicated
  `chore(phase2): re-stamp LLM evidence SHAs` commit as the last commit; follow
  the same established pattern.
- **Risk:** cleanup pressure encourages weakening the doc gate.
  **Mitigation:** explicit rule in step 7 — split docs, never raise the cap;
  `AGENTS.md` already forbids changing a test's expected value to pass.
