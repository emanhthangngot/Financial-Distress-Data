---
phase: 12
title: "Evidence capture system and submission freeze"
status: cancelled
priority: P1
effort: "2.5d"
dependencies: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
---

> **CANCELLED 2026-08-14 (user decision, ML track dropped).** This was the ML track's final evidence freeze (remainder of the 57 ML points) plus an all-subsystems soak that only the cancelled phases needed. The LLM track's own freeze is tracked separately in plans/260811-1627-close-llm-rubric-to-100/ phase 6. The generic evidence-capture fail-closed fixes this phase produced were kept (folded into the phase-1/phase-2-adjacent evidence-tooling commit).
> Body below is kept as the historical record of what was planned/built; nothing further is executed against it. See `plan.md` Overview.

# Phase 12: Evidence capture system and submission freeze

## Overview

Turn evidence production from a manual activity into a scripted, checklist-driven
system — the user's explicit first-class requirement — then run the concurrent
soak, capture everything, and freeze both tracks for submission.

## Requirements

- Functional: one command regenerates the full evidence set for a named rubric
  section; every screenshot has a declared purpose; the narrative summary tells
  the failure-to-fix story with each step pointing at its exact artifact.
- Non-functional: both tracks pass the strict two-repository auditor at 100/100;
  all five new subsystems run concurrently through the soak.

## Architecture

Two capture disciplines were studied and both are adopted, because they solve
different problems.

**From `yas-cd` — sequential numbering plus narrative.** Evidence files numbered
`00_` through `35_` in demo order, and a summary that tells the story: release
`v0.1.0` failed the GitOps gate, `v0.1.1` failed twice for different reasons,
`v0.1.2` succeeded after two specific fixes — each step citing its exact log file,
plus a self-declared "Known issues" section admitting an unrelated runtime bug.
A reader understands the system in two minutes, and the honesty is more persuasive
than an unbroken wall of PASS.

**From `RecSys-MLops` — reference semantics plus per-section checklists.** An
explicit convention for what a link means:

> - a relative repository link points to **current** source or configuration
> - a GitHub URL pinned to a full commit SHA points to **historical** proof that
>   was intentionally superseded; it is not a runnable path in the current checkout
> - screenshots, run IDs, metrics and timestamps describe **a captured run**;
>   re-run the associated current command before using them as a statement about
>   live state

Plus a "Current Authoritative Sources" table mapping each concern to exactly one
owning file, and a per-section screenshot checklist naming which image proves what.
This directly prevents the defect phase 1 measured — declared artifact paths that
drift away from reality.

**Existing base to extend, not replace:** `scripts/capture_ui_screenshots.py` and
`docs/ui-screenshot-runbook.md` already work. They become the browser-capture
backend of the wider capture driver.

The project's own evidence contract stays the authority and is not weakened —
it is already stricter than either reference repo (dual-repo SHA ancestry,
redaction status, clean-worktree gate, executable `validation_command`). What is
added is presentation and automation on top.

## Related Code Files

Source repo:

- Create: `scripts/capture_phase2_evidence.py` — the one-command driver
- Create: `configs/evidence-checklist.yaml` — per-section: what to capture, which command, what it proves
- Create: `docs/platform/evidence/README.md` — reference semantics + authoritative-sources table
- Create: `docs/platform/evidence/ml/00-run-summary.md` — numbered narrative + known issues
- Create: `docs/platform/evidence/llm/00-run-summary.md` — same for the LLM track
- Create: `docs/platform/evidence/validation-verification/` — coverage table, mutation summary, load SLA summary
- Modify: `scripts/capture_ui_screenshots.py` — invoked as a backend by the driver
- Modify: `docs/ui-screenshot-runbook.md` — point at the driver

## Implementation Steps

1. Write `configs/evidence-checklist.yaml`: for each rubric section, the artifacts
   to produce, the exact non-interactive command producing each, and the
   one-line claim each artifact supports. This file is the contract; the script
   is only its executor.
2. Write `scripts/capture_phase2_evidence.py`: takes a section name (or `--all`),
   runs each declared command, captures stdout/artifacts, invokes the existing
   screenshot capture where a screenshot is declared, and stamps every artifact
   with the eight evidence-contract fields via the existing
   `scripts/stamp_phase2_evidence.py`.
3. Write `docs/platform/evidence/README.md` with the reference-semantics convention
   and the authoritative-sources table.
4. Run the **concurrent soak**: bring up all five new subsystems plus the ML stack
   plus the platform data plane simultaneously and hold for a defined window,
   recording `kubectl top nodes`, pod status and dashboards. This is the direct
   evidence for the user's "all running concurrently" requirement.
5. Run `capture_phase2_evidence.py --all` and produce the complete set.
6. Write the two narrative summaries in the `yas-cd` style — real failures
   encountered during phases 1-11, their root causes and fixes, each citing its
   artifact, plus an honest "Known issues" section.
7. Assemble the validation-verification bundle: per-module coverage table,
   mutation score against its gate (`scripts/run_phase5_mutation_gate.py` already
   produces the numbers), Locust raw report plus a machine-readable SLA summary,
   and the screenshot checklist.
8. Run both strict gates. Fix findings. Repeat until both are 100/100.
8b. **Cost ledger.** Record actual spend for the whole plan window from the
   billing export enabled in phase 4 step 0: gross, credit applied, remaining
   balance, and cost per phase. The soak window is the single most expensive
   entry and should be reported separately. Bring the cluster down immediately
   after the captures — at 24 vCPU the burn is roughly $0.9-1.2/hr.
9. Write the production limitations section: what is production-shaped versus
   genuinely production (no HA, no multi-AZ, no DR, single-region), and the
   remaining gap versus a full production system. Declaring this is stronger than
   letting an assessor find it.
10. Freeze: tag both repositories, record both SHAs, confirm clean worktrees.

## Verification

```bash
.venv/bin/python scripts/capture_phase2_evidence.py --all \
  --gitops-root ~/Studying/FSDS/financial-distress-gitops
.venv/bin/python scripts/audit_phase2_evidence.py --require-executed --run-validations \
  --phase1-base "$PHASE1_BASE_SHA" --gitops-root ~/Studying/FSDS/financial-distress-gitops \
  --track LLM --llm 100
.venv/bin/python scripts/audit_phase2_evidence.py --require-executed --run-validations \
  --phase1-base "$PHASE1_BASE_SHA" --gitops-root ~/Studying/FSDS/financial-distress-gitops \
  --track ML --ml 100
.venv/bin/python scripts/run_stage1_quality_gates.py
```

## Success Criteria

- [ ] `capture_phase2_evidence.py --all` -> single command -> regenerates the complete evidence set with zero manual capture
- [ ] Every screenshot -> looked up in the checklist -> has a declared claim it supports; no orphans
- [ ] Concurrent soak -> all five new subsystems plus ML stack plus platform .lane up simultaneously -> held for the window, resource usage captured
- [ ] Strict auditor `--track LLM` -> PASS 100/100
- [ ] Strict auditor `--track ML` -> PASS 100/100
- [ ] `--check-artifacts` -> zero missing artifacts across both repos
- [ ] Narrative summaries -> read end to end -> tell the failure-to-fix story with every step citing a real artifact, and declare known issues
- [ ] Both repositories -> tagged with clean worktrees, SHAs recorded

## ML rubric rows closed

- Documentation — all documents in `docs/`, linked from README (1)
- Repository Design — clean code, clean repo, design patterns demonstrated (2)
- Validation & Verification x5 — EP/BVA, mutation testing, property-based
  idempotency, load testing, and the section row (10)
- Plus final capture for every row from phases 4-11 that needed executed proof

## Risk Assessment

- **Evidence captured in earlier phases may be stale** if later phases changed
  behaviour. Step 5's full regeneration is not optional — it is the reason the
  capture system exists.
- **The soak is the most expensive cluster window in the plan.** Schedule it
  deliberately, run captures in one pass, and bring the cluster down immediately
  afterwards.
- **Both tracks at 100/100 is a high bar** and step 8 may iterate several times.
  Budget for iteration rather than treating the first run as final.
- **Writing an honest "Known issues" section may surface something uncomfortable.**
  Write it anyway; the reference repo that did so is more credible for it.
