---
title: "Phase 8: Produce evidence, mock-grade and promote"
status: todo
estimate: "1.5 days (day 6 + day 7)"
---

# Phase 8: Produce evidence, mock-grade and promote

## Overview

Run the system, capture reviewer-readable proof for every scored LLM row, audit
claims against artifacts, perform independent mock grading, promote the final
Git revisions, and destroy the cloud evidence resources.

**Scope: the 60 LLM rows only.** The 57 ML rows stay in the matrix as
`design_only` and are excluded from the executed gate by `--track LLM`. See the
plan index's Session 2 validation log.

## Day 6 — the SHA-stamping step, do not defer to day 7

The evidence contract requires every evidence file's `source_sha` and
`gitops_sha` to be a real 40-hex commit equal to the current `HEAD` of the
respective repository, with both worktrees clean. That is circular: the evidence
records the SHA of the commit that contains the evidence.

Working flow, scripted as `scripts/stamp_phase2_evidence.py`:

1. Commit everything in the GitOps repository; capture its `HEAD`.
2. Commit everything in the source repository; capture its `HEAD`.
3. Rewrite the 60 evidence files' `source_sha` and `gitops_sha` fields.
4. `git commit --amend` in each repository.

Order matters — stamp GitOps first, because the source evidence records both.
Doing this by hand at 3am on day 7 is the most likely late failure in the plan.

## Evidence Rules

- Every artifact records requirement ID, execution timestamp, exact 40-hex source SHA, exact 40-hex GitOps SHA, image/model/data/agent versions, mandatory reproduction command, expected result, actual result and redaction status.
- Screenshots supplement machine-readable outputs; they never replace logs/reports/manifests when the latter are available.
- Product UI evidence must include `UI-APPROVED-01` (analyst workspace),
  `UI-APPROVED-02` (agent chat) and `UI-APPROVED-03` (agent registry/evidence
  operations). Each capture records route, state, viewport, source SHA, GitOps
  SHA, data/model/agent version, expected/actual result and redaction status;
  the original approved binaries are retained unchanged when supplied.
- Each major `docs/platform/` section explains what an image proves. No orphan screenshot dump.
- “Designed”, “configured”, “executed”, and “passed” remain distinct statuses.
- Capture only the relevant window/region and redact account IDs, hosts where needed, tokens, emails and private data.

## Mandatory Evidence Runs

1. Run the platform .ull quality/evidence gate to prove no regression — this also
   proves `.venv` was never mutated by platform .ependencies.
2. Run coverage, mutation (`mutmut`, on its declared module subset),
   equivalence/boundary, Hypothesis and security gates for the LLM track.
3. Capture the GCP evidence run: `terraform apply` plan/output, the DuckDNS
   cert-manager HTTPS certificate, and a `make gcp-up`/`gcp-down` hibernate
   cycle with its recorded cost delta.
4. Capture Argo sync waves, GitOps commit/digest, rolling update and atomic
   fallback, autoscaling for both MCP-backed APIs, and Git-revert rollback.
5. Capture Feast materialization, both stream-feature jobs (offline and online),
   TTL rationale, Airflow ordering, DataHub lineage, the label table, drift
   configuration and the RAG corpus with its governance metadata.
6. Capture the model server deploy, the benchmark before/after table, the global
   `ModelConfig`, agentgateway routes, the agent registry, both MCP tools, the
   two specialists and the coordinator, the sandbox with its three negative
   demonstrations, replicas and autoscale, warm-up cold-versus-warm numbers,
   `UI-APPROVED-02` agent chat, `UI-APPROVED-03` registry, and the LLM/agent A/B
   comparison. Capture `UI-APPROVED-01` analyst surfaces with cached and
   cluster-off provenance states.
7. Generate the Locust HTML for the Web API kéo dữ liệu and capture its
   parameters and SLA summary.
8. Capture the active F5 NGINX OSS version and digest, retired-controller
   rejection, backends unreachable except through the ingress (a negative curl
   plus a successful one), authentication on the chat UI, the reachable log
   viewer and trace viewer, Terraform, the Ansible evidence-host role with its
   `changed=0` second run, sealed-secrets, and metrics/logs/traces telemetry.
9. Capture design-pattern code, the five LLM classes, and working proof for both
   novel ideas.
10. Run the strict two-repo auditor with `--track LLM` plus every LLM row's
    behavior-validation command, mock-grade independently against the canonical
    LLM CSV, resolve every gap, then freeze both 40-hex submission SHAs.
11. Run `make gcp-down` to hibernate the cluster (node pools to zero, PVCs
    retained), record the final GCP Billing credit balance, and confirm the
    trial billing account was never upgraded to paid.
12. Populate `docs/submission/*.md` (created as skeletons in phase-03) as the
    reviewer-facing index: one file per rubric section, each linking into its
    `docs/platform/evidence/` artifacts. `cost.md` records the GCP spend measured
    in step 11 against the < USD 100 target.

## Reviewer Document Set

- `README.md`: business, TOC, repo map and high-level numbered deployment diagram. Every deployable is a node, every primary edge is solid, numbered/described, and included in a flow legend; repository-wide file/module/class/function docstrings are checked.
- `docs/platform/ml.md`, `llm.md`, `data-and-feast.md`, `gitops.md`, `iac.md`, `security.md`, `observability.md`, `testing.md`, `cost-and-operations.md`.
- `docs/platform/evidence/index.md`: rubric-ID index linked to reports, screenshots and raw outputs.
- `docs/platform/low-level-design.md`: five classes per track and design patterns.
- `docs/platform/novel-ideas.md`: four ideas and executed proof.
- `docs/submission/*.md`: one reviewer-facing file per rubric section (`iac.md`,
  `security.md`, `observability.md`, `ci_cd.md`, `cost.md`, `routing_gateway.md`,
  `validation_verification.md`, …), each linking into its
  `docs/platform/evidence/` artifacts rather than duplicating them. Skeletons
  created in phase-03, populated here.

## Validation

- `python scripts/audit_phase2_evidence.py --strict --require-executed --run-validations --track LLM --phase1-base "$PHASE1_BASE_SHA" --gitops-root "$GITOPS_CHECKOUT" --ml 100 --llm 100`

`--ml 100 --llm 100` stays: those flags assert the *matrix* totals, which must
still cover all 117 rows. `--track LLM` narrows only the executed-evidence and
behavior-validation gates. Added in phase-03; without it this command fails with
57 errors regardless of how good the LLM evidence is.

Before promotion, record `PHASE1_BASE_SHA` as the immutable 40-hex commit
immediately before platform .ork. Do not substitute a moving branch name. The
gate compares every evidence source/GitOps SHA with the two checked-out
`HEAD`s and rejects protected platform .hanges against that frozen baseline.
Both source and GitOps checkouts must be clean; the recorded commits therefore
contain the implementation, manifests, and evidence that the auditor reads.
- Link/image integrity, duplicate/stale screenshot, secret/PII, timestamp/version and rubric-total checks.
- Independent manual mock grade using the two original CSVs, not the implementation checklist alone.
- GCP Billing credit report after the final `make gcp-down` hibernate cycle.

## Success Criteria

- [ ] Coursework reviewer -> opens the LLM rubric -> follows every scored row to an explained, executed and version-matched artifact.
- [ ] Evidence auditor -> evaluates the frozen submission with `--track LLM` -> reports no missing, stale, secret-bearing or design-only LLM proof; the 57 ML rows remain visibly `design_only` rather than silently removed.
- [ ] Reviewer -> inspects README and detailed docs -> understands deployable units, numbered data flows, classes, patterns, security and operating limits, and finds the deferred ML track stated honestly.
- [ ] Cost owner -> hibernates the cluster with `make gcp-down` -> sees node pools at zero, PVCs intact, the trial billing account never upgraded, and total weekly spend under USD 100 of the 300 free-trial credit.
- [ ] Maintainer -> checks final source and GitOps SHAs -> can reproduce the release and roll it back through Git alone.
- [ ] UI reviewer -> checks the three approved UI IDs and every required viewport/state -> finds no orphan screenshot, stale SHA, missing provenance, inaccessible control or false live-inference label.

## Risks and Rollback

- Risk: screenshot-heavy evidence becomes stale after a late release. Mitigation: manifest version checks reject mismatched SHA/digest/timestamps.
- Rollback: do not rewrite evidence to match claims; revert the bad release, rerun the affected scenario, replace its evidence atomically, and re-audit.
