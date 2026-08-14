---
title: "LLM evidence bundle presentation"
description: "Adapt RecSys-MLops' validation-verification evidence-bundle presentation (coverage table, mutation/locust summary files, screenshot checklist, Current Production Sources table) to the LLM track, using already-captured real numbers — no new test/mutation/load runs. Additive only: append to docs/phase2/evidence/README.md, add new files under docs/phase2/evidence/llm/validation-verification/; existing per-row evidence .md files stay untouched (canonical, must not be rewritten)."
status: completed
priority: P2
effort: "0.5d, no cloud quota, no new test runs"
tags: [phase2, llm, evidence, docs]
blockedBy: []
blocks: []
created: 2026-08-14
---

# LLM evidence bundle presentation

## Overview

`itsmekhoathekid/RecSys-MLops` (pinned `e99df9d1`, studied in
[`xia-260813-1731-gitops-and-mlops-reference-study.md`](../reports/xia-260813-1731-gitops-and-mlops-reference-study.md))
presents its validation evidence as a bundle, not scattered per-row files:
a `validation-verification/README.md` with a per-component coverage table,
a "Required Proof" list linking straight to test source lines, a screenshot
checklist naming exactly which image proves what, plus standalone
`mutation-summary.md` and `locust-sla-summary.md` files. It also keeps a
"Current Production Sources" table mapping each operational concern to one
authoritative file, so a reader never has to guess which of several
candidate paths is the live one.

We have the *same underlying data*, already captured with real numbers on
2026-08-10, but split across 5 separate canonical evidence files under
`docs/phase2/evidence/llm/LLM-validation-verification-*.md` with no bundle
view: coverage 96.17% lines / 93.48% branches, mutation 86.11% (62 killed / 9
survived / 1 timeout of 72), idempotency and equivalence-partition tests
passing, and a real Locust run (1352 requests, 0 failures, p95 140ms, 15.06
req/s) that surfaced and fixed 5 real bugs. This plan packages that existing
data the way RecSys presents it — verified format, fetched from the pinned
commit itself, not reconstructed from memory — and improves on it: RecSys's
bundle doesn't link back to individually reproducible per-claim evidence
files or record what broke during the real run; ours does both, and keeps
that as the improvement.

Accepted brainstorm contract (stated here, no separate report — task is
small, bounded, and low-risk enough that the scope-challenge gate is
satisfied inline):

**Outcome.** `docs/phase2/evidence/llm/validation-verification/README.md`
exists in RecSys's exact section shape (Coverage / Required Proof / Screenshot
Checklist / Mutation Summary / Locust Summary), populated with our real,
already-captured numbers and cross-linked to the 5 canonical evidence files
that back each claim. Standalone `mutation-summary.md` and
`locust-sla-summary.md` exist in RecSys's exact field shape. A "Current
Production Sources" table is appended to `docs/phase2/evidence/README.md`
(format preserved, only appended to) mapping LLM-track concerns to their one
authoritative file.

**Constraints** (verified in-repo, not assumed):

| Constraint | Evidence |
|---|---|
| Canonical evidence `.md` files "must not be rewritten by a capture run" | `docs/phase2/evidence/README.md:3-6` |
| All underlying numbers already exist, real, dated 2026-08-10 | `docs/phase2/evidence/llm/LLM-validation-verification-*.md` (read verbatim this session) |
| Raw Locust artifacts already on disk | `docs/phase2/evidence/llm/locust-report.html`, `locust_stats.csv`, etc. |
| Raw mutation numbers already on disk | `plans/260809-2039-complete-phase2-llm-submission/reports/phase05-mutation-summary.json` |
| RecSys bundle format (fetched verbatim from the pinned commit, not recalled) | `docs/submission/rubic-final-coursework-(final-ml)/validation-verification/{README.md,mutation-summary.md,locust-sla-summary.md}` at `e99df9d1` |
| Strict `--track LLM` gate must stay green | acceptance criterion below |
| `PHASE1_PROTECTED` untouched — this plan only adds `docs/` content | `scripts/audit_phase2_evidence.py:58-71` |

**Non-goals** (deliberately rejected, with reason):

| Rejected | Reason |
|---|---|
| Re-run mutmut / locust / pytest coverage | Numbers already captured and evidence-stamped 2026-08-10; re-running produces a second, possibly-drifted number for no rubric benefit and risks the strict gate's SHA-drift check |
| Capture new PNG screenshots | We have HTML/CSV/JSON artifacts, not screenshots, for this row set; the checklist references those instead of inventing image captures that were never taken |
| Rewrite the 5 canonical `LLM-validation-verification-*.md` files | Evidence contract forbids rewriting canonical rows; this plan only *adds* a bundle view that links to them |
| Extend the bundle to ML-track rows | ML track is out of scope for this repo (`plans/260813-1846-production-hardening-overlay`); LLM-only |
| Copy RecSys's Jenkins/coursework framing verbatim | Different CI system (GitHub Actions, not Jenkins); adapt structure, not tooling references |

**Acceptance criteria** (`WHO -> ACTION -> RESULT`):

1. Reader -> opens `docs/phase2/evidence/llm/validation-verification/README.md` -> sees Coverage table, Required Proof list (linking to real test files/lines), Screenshot/artifact checklist, Mutation Summary, Locust Summary — same section order as RecSys, our real numbers.
2. Reader -> opens `mutation-summary.md` / `locust-sla-summary.md` -> sees RecSys's exact field list (Mutation score/Gate/Killed/Survived/Timeout/.../Targets/Mutant filters; Host/Requests/Failures/Failure rate/Throughput/p95 latency/SLA/Result) populated with our numbers.
3. Reader -> opens `docs/phase2/evidence/README.md` -> finds a new "Current Production Sources" table below the existing content, format/prose above unchanged.
4. `scripts/audit_phase2_evidence.py --require-executed --run-validations --track LLM --phase1-base <SHA> --gitops-root <path> --ml 100 --llm 100` -> run after this change, on a committed clean tree -> still PASS 100/100 (new files are additive, not referenced as `artifact_path`/`evidence_path` for any row, so they cannot change the score).
5. `.venv/bin/python -m pytest tests` and `.venv-phase2/bin/python -m pytest tests/phase2` -> unchanged pass counts (this plan touches no code, no tests).

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Bundle the 5 scattered validation-verification evidence rows into one RecSys-shaped README, using real numbers only | P0 |
| 2 | Add standalone mutation-summary.md / locust-sla-summary.md in RecSys's exact field format | P1 |
| 3 | Add a "Current Production Sources" table to the existing evidence README, format preserved | P1 |
| 4 | Improve on RecSys: keep the cross-links to reproducible per-claim evidence and the real-bugs-found log RecSys's bundle lacks | P1 |

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Build the LLM validation-verification bundle](./phase-01-start.md) | Completed |

## Success Criteria

- [x] `docs/phase2/evidence/llm/validation-verification/README.md` created, RecSys section shape, real numbers, links to the 5 canonical evidence files (every relative link verified with `[ -e ]` this session)
- [x] `docs/phase2/evidence/llm/validation-verification/mutation-summary.md` and `locust-sla-summary.md` created, RecSys field format
- [x] `docs/phase2/evidence/README.md` gets a new "Current Production Sources" table appended; `git diff` confirms existing prose byte-identical above it
- [x] Strict `--track LLM` gate still PASS 100/100 after adding these files, on a committed clean tree with re-stamped SHAs
- [x] Full test suites unchanged: `.venv` 311 passed, `.venv-phase2` 549 passed/35 skipped — identical to before this phase

**Deviation from the plan as written (user correction, mid-implementation):**
screenshots are real tool output, not the fabricated "styled terminal HTML"
mockup the plan originally sketched. Coverage and Locust get real screenshots
(`coverage.py`'s own HTML report; the real `locust-report.html`, both
photographed via `mcp__claude-in-chrome`). Mutation/idempotency/equivalence
have no native browser report tool in this repo (`mutmut` has no HTML
command; no `pytest-html` plugin installed) — they stay text-only rather than
screenshotting an invented mockup. See the bundle README's "Artifact
Checklist" section for the explicit reasoning.

## Open questions

None.

<!-- slug: llm-evidence-bundle-presentation -->
