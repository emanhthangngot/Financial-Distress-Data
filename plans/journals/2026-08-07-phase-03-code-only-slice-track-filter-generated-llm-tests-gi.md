---
title: "Phase-03 code-only slice: --track filter, generated LLM tests, gitops skeleton"
date: 2026-08-07
summary: Implemented day-1 code steps of phase-03 GKE pivot; found and fixed a pytest -k collision bug in the locked rubric contract
---

# Phase-03 code-only slice: --track filter, generated LLM tests, gitops skeleton

## What happened

Resumed prior-session GKE pivot work on branch `docs/phase2-llm-only-gke-pivot`
(unmerged from `dev`). Scoped `/ak:cook phase-03` to the local/code-only slice
first, deferring real GCP provisioning (needs project ID + gcloud auth, not
available this session).

Implemented (phase-03 day-1, steps 5-6):
- `--track {ML,LLM}` repeatable CLI flag on `scripts/audit_phase2_evidence.py`,
  filtering only `_audit_executed`/`_audit_frozen_revisions`/
  `_audit_behavior_validations`; matrix-completeness and canonical-coverage
  checks stay unfiltered (always require all 117 rows).
- New `scripts/generate_phase2_requirement_tests.py`: generates
  `tests/phase2/requirements/` (conftest.py + 20 files, 60 parametrized
  cases) from the LLM rows of `docs/phase2/rubric-matrix.csv`. Each case's
  node id is the exact `rubric_id` so the row's own `validation_command`
  selects exactly one case; skips (not fails) while `evidence_type` is still
  `design_only`.
- Created GitHub repo `emanhthangngot/financial-distress-gitops` (day-0
  skeleton, 14 declared artifact placeholder paths, no cloud resources).

Code review (mandatory gate) found three real defects, all fixed:
- **H1**: two `rubric_id`s were prefix-substrings of each other
  (`LLM-observability-m-b-o-t-nh-t-c-c-metrics` / `...-metrics-1`, and an ML
  equivalent for feature-store offline/online jobs). `pytest -k` does
  substring match, not anchored match, so the shorter id's exact
  `validation_command` selected both rows — a mis-attribution bug in the
  phase-08 promotion gate. This was a pre-existing latent defect in the
  locked rubric-contract generator (`scripts/_phase2_rubric_items.py`'s
  blind `-{n}` dedup suffix), not introduced this session. Fixed with a
  `_COLLISION_RENAMES` override table giving the two rows content-based
  slugs, plus a regression test
  (`test_no_rubric_id_is_a_prefix_of_another`) asserting no rubric_id is
  ever a substring of another's.
- **H2**: the generated tests hardcoded a sibling-directory assumption for
  the GitOps checkout with no override, contradicting the auditor's own
  `--gitops-root` contract (no default, explicit flag required). Fixed:
  `PHASE2_GITOPS_ROOT` env override, and a distinct skip reason when the
  checkout itself is missing vs. when the artifact inside it is missing.
- **H3**: `--check` mode formatted content with black's Python API while
  write mode shelled out to `black` as a subprocess, and a bare
  `except Exception` silently fell back to unformatted content on any black
  failure — so a broken toolchain would misreport as CSV drift. Fixed: one
  formatting code path (`_format`) used by both modes, failure now raises.

## Decision

Scoped this run to code-only work and repo-skeleton creation; deferred
`terraform apply`, GKE cluster provisioning, Argo CD bootstrap, and DuckDNS
registration pending the user's GCP project ID (asked explicitly, user chose
to sequence: local setup first, GCP ID later). `terraform`/`ansible` install
blocked on sudo password (task #5, left pending — not completed silently).

## Next steps

- User runs `sudo pacman -S --noconfirm terraform ansible`.
- User supplies GCP project ID to resume phase-03 steps 1, 2, 9-16
  (quota check, `terraform apply`, ingress/cert-manager/DuckDNS, Argo CD,
  Knative/KServe install).
- Commits: `9aeb2a0` (feat, --track + generated tests), `24ad6f6` (fix,
  collision renames), both pushed to `origin/docs/phase2-llm-only-gke-pivot`.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
