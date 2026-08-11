---
phase: 1
title: "Align the contract, the repos and the audit mechanics"
status: complete
priority: P1
effort: "0.75d (no cluster)"
dependencies: []
---

# Phase 1: Align the contract, the repos and the audit mechanics

## Overview

Before anything is deployed or captured, make the gate reachable and the flip
mechanism satisfiable. Every item here was found by the red team to be
unsatisfiable, contradictory, or silently wrong today. No rubric row is claimed.

## Requirements

- Functional: the GitOps checkout sits on the branch Argo actually deploys; the
  frozen `PHASE1_BASE_SHA` is recorded; the 8 rows whose `artifact_path` cannot
  carry a row-specific behavioral assertion are re-pointed and all 13 assertion
  strings are pre-written and reviewable; a redaction convention exists that the
  auditor's denylist accepts; the plan's own gate expectations match what the
  auditor actually enforces.
- Non-functional: no Phase 1 (coursework stage 1) protected path is touched; the
  47 already-executed rows keep passing after every change here.

## Architecture

**Branch alignment (blocker for everything).** Every Argo source pins
`targetRevision: master` (`argocd/applications/platform-observability.yaml:26,29,39`;
`argocd/applicationset-dev.yaml`), and CI opens digest PRs `--base master`. The
GitOps checkout is on `feat/phase5-ab-pvc-clones`, and the `gitops_sha`
`921bdc1` recorded in all 47 evidence files is **not** an ancestor of
`origin/master` (`git merge-base --is-ancestor` → false; `origin/master...HEAD`
→ 3 behind / 1 ahead). Two consequences:

- Committing the sealed secret to the current branch means Argo syncs
  `master`'s placeholder and the routes return 503, not 401.
- Checking `master` out locally without merging breaks the ancestor rule for all
  47 rows.

So: merge the feature branch into `master`, check `master` out, re-run the
baseline gate, and make every later GitOps commit land on `master`.
"GitOps checkout branch == Argo `targetRevision`" is an exit condition.

**The gate is not clean until after stamping.**
`_only_evidence_sha_lines_changed` (`scripts/audit_phase2_evidence.py:609-638`)
allows post-evidence commits only when every changed line is a
`source_sha`/`gitops_sha` line under `docs/phase2/evidence/`. The GitOps repo has
no such directory, so **any** GitOps commit invalidates the frozen-revision check
for all 47 existing rows until they are re-stamped. The plan therefore expects a
clean strict gate **only** in the final phase, immediately after the stamp.
Earlier phases run the gate expecting exactly these frozen-revision errors and
nothing else.

**Behavioral assertions are matched against the artifact file, not the
evidence** (`tests/phase2/requirements/conftest.py:143-187`). All 7 Routing &
Gateway rows declare `artifact_path: platform/ingress/f5-nginx-values.yaml` —
an F5 controller values file with no token meaning "agent-test UI",
"registry UI", "authentication", "log viewer" or "trace viewer" — and the traces
row declares `platform/observability/loki-otel-values.yaml`, which contains no
Jaeger content. Flipping them without re-pointing forces invented tokens, which
the Evidence Rule forbids. The predecessor plan's Path Authority Rule permits a
retarget in `scripts/_phase2_rubric_items.py::EXPLICIT_IMPLEMENTATION` exactly
when rows collide on one artifact and each needs distinct proof — that is this
case. Re-point to the file that implements each row (`routes-ui.yaml`,
`routes-viewers.yaml`, `duckdns-certificate.yaml`, `basic-auth-sealed-secret.yaml`,
`jaeger.yaml`, `otel-collector.yaml`, `grafana-dashboards/llm-observability.yaml`
as appropriate) and write all 13 assertion strings into this phase's report so
they are reviewed before any capture.

**Redaction convention.** `_audit_all_evidence_bodies`
(`scripts/audit_phase2_evidence.py:753-770`) scans every `.md` under
`docs/phase2/evidence/` against `EVIDENCE_SECRET_DENYLIST` (`:712-741`), which
trips on `Authorization\s*:` (even with the value redacted), the literal ingress
IP `34.21.242.110`, the GCP project ID, and any ≥200-char base64 run. Those are
exactly what a gateway capture prints. Define substitutions
(`<INGRESS_IP>`, `<GCP_PROJECT>`, and an `Authoriz<redacted>ation` form or simply
dropping the header line) and prove them against a synthetic evidence file
before any real capture.

**Denylist gaps to close in the same pass.** The list does not catch
`curl -u user:pass`, `https://user:pass@host`, or a bcrypt `$2[aby]$` htpasswd
line — the three shapes most likely to leak the gateway credential into a public
repo. Extend it, so the safety net exists before captures start.

**Two contract contradictions to fix.** `docs/phase2/evidence-contract.md:62-63`
says SHAs must *equal* checkout HEAD, while the auditor implements the ancestor
rule the freeze depends on. And the token-metrics row's canonical CSV
`requirement` names TTFT and PII-catch frequency in addition to token counts and
round-trip time; the capture spec must carry the full CSV string, since the mock
grade is scored against the CSV.

## Related Code Files

- Modify: `docs/phase2/evidence-contract.md` (frozen `PHASE1_BASE_SHA`; ancestor-rule correction)
- Modify: `docs/submission/README.md` (truthful status: 47 executed and stamped, 13 outstanding)
- Modify: `scripts/_phase2_rubric_items.py` (`EXPLICIT_IMPLEMENTATION` re-point for the 8 mismatched rows)
- Modify: `scripts/audit_phase2_evidence.py` (`EVIDENCE_SECRET_DENYLIST` additions)
- Regenerate (never hand-edit): `docs/phase2/rubric-matrix.csv`, `tests/phase2/requirements/test_llm_ac_13_routing.py`, `test_llm_ac_15_observability.py`
- Create: `plans/260811-1627-close-llm-rubric-to-100/reports/` — the 13 pre-written assertion strings, the redaction convention, the baseline gate output
- GitOps: branch merge only, no manifest change in this phase

## Implementation Steps

1. Run the baseline gate and keep the output verbatim (13 rows in
   `--accept-design-only`, `--phase1-base ddbcbe7bd41ae4883954b8a247efdc67c7329078`).
   Note it requires a clean worktree, so commit or stash this plan first —
   an untracked plan directory alone makes it fail with
   `source checkout is not clean`.
2. Merge the GitOps feature branch into `master`, push, check `master` out
   locally. Confirm `git merge-base --is-ancestor 921bdc1 origin/master` now
   succeeds and re-run step 1's gate.
3. Record `PHASE1_BASE_SHA=ddbcbe7bd41ae4883954b8a247efdc67c7329078` in
   `docs/phase2/evidence-contract.md` with one sentence on why that commit, and
   correct the HEAD-vs-ancestor contradiction in the same file.
4. Re-point `EXPLICIT_IMPLEMENTATION` for the 8 rows whose declared artifact
   cannot carry a distinct assertion; regenerate the matrix and the two
   requirement test files; confirm the 47 executed rows are untouched by the
   regeneration diff.
5. Write the 13 behavioral assertion strings into this phase's report, each
   naming the artifact file and the token, and verify each token exists in its
   file **today** (they are manifest facts, not capture facts).
6. Extend `EVIDENCE_SECRET_DENYLIST` with `curl -u` / `--user`, `//user:pass@`,
   and `$2[aby]$` patterns. Re-run the gate to prove no existing evidence trips
   the new patterns.
7. Write the redaction convention and prove it: create a synthetic evidence file
   containing a realistic redacted `curl -v` 401 exchange and a hide-services
   negative, run the auditor's body scan over it, and iterate until it passes.
   Keep the passing sample as the template for phase 5.
8. Copy the **full** CSV `requirement` string for all 13 rows into this phase's
   report — including TTFT and the PII-catch frequency on the token-metrics row —
   so phase 5 captures what the grader scores, not a paraphrase.
9. Correct `docs/submission/README.md` to the real state. Do not claim the 13.
10. Re-run the baseline gate. Expect the pre-existing frozen-revision behavior
    described above and nothing new.

## Success Criteria

- [ ] Operator -> runs `git merge-base --is-ancestor 921bdc1 origin/master` in the GitOps repo -> succeeds, and `git branch --show-current` prints `master`.
- [ ] Maintainer -> greps `docs/phase2/evidence-contract.md` -> finds a 40-hex `PHASE1_BASE_SHA` and no HEAD-equality claim that contradicts the ancestor rule.
- [ ] Maintainer -> reads this phase's report -> finds 13 assertion strings, each verified present in its re-pointed artifact file today.
- [ ] Auditor -> scans the synthetic redacted capture -> zero denylist hits, and the sample is kept as phase 5's template.
- [ ] Auditor -> re-runs the baseline gate after every change here -> the 47 executed rows still pass; no new finding class appears.
- [ ] Reader -> opens `docs/submission/README.md` -> reads a status matching the repository.
- [ ] Cost owner -> runs `make gcp-status` -> cluster still at zero nodes.

## Risk Assessment

- **The GitOps merge conflicts or drags `master` backwards** → Argo reconciles an
  older platform. Mitigation: merge, then diff `master` against the feature
  branch for the platform paths before pushing; the Application has
  `selfHeal: true`, so a bad `master` self-applies.
- **Re-pointing artifacts changes rows the graders already saw** → confusion at
  grading. Mitigation: only the 8 unsatisfiable rows move, and the report records
  old path → new path with the reason.
- **Denylist additions break existing evidence** → a previously passing row
  fails. Mitigation: step 6 re-runs the gate immediately.
- **Recording an unverified `PHASE1_BASE_SHA`** → the final gate reads as a Phase
  1 regression. Mitigation: step 1 proves it empirically first.
- Rollback: every change here is a docs/script edit plus one GitOps branch merge;
  revert the commits and the repository returns to today's state.
