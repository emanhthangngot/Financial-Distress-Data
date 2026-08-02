---
title: "Phase 8: Produce evidence, mock-grade and promote"
status: todo
estimate: "6-8 days"
---

# Phase 8: Produce evidence, mock-grade and promote

## Overview

Run the system, capture reviewer-readable proof for every scored row, audit claims against artifacts, perform independent mock grading, promote the final Git revisions, and destroy the evidence plane.

## Evidence Rules

- Every artifact records requirement ID, execution timestamp, exact 40-hex source SHA, exact 40-hex GitOps SHA, image/model/data/agent versions, mandatory reproduction command, expected result, actual result and redaction status.
- Screenshots supplement machine-readable outputs; they never replace logs/reports/manifests when the latter are available.
- Each major `docs/phase2/` section explains what an image proves. No orphan screenshot dump.
- “Designed”, “configured”, “executed”, and “passed” remain distinct statuses.
- Capture only the relevant window/region and redact account IDs, hosts where needed, tokens, emails and private data.

## Mandatory Evidence Runs

1. Run Phase 1 full quality/evidence gate to prove no regression.
2. Run coverage, changed-code mutation, equivalence/boundary, Hypothesis and security gates for both tracks.
3. Provision one named EKS evidence session; capture cost preview, TTL, Terraform outputs and state timeline.
4. Capture Argo sync waves, GitOps commit/digest, rolling update/atomic fallback, autoscaling for feature and drift APIs, and Git-revert rollback.
5. Capture Feast materialization/offline+online stream jobs, TTL rationale, Airflow ordering, DataHub lineage, drift config/label merge, versioned data, and both scheduled drift branches: skip below threshold plus actual KFP API run ID/status above threshold via Pushgateway/Grafana.
6. Capture notebook, successful KFP distributed training, MLflow model/data versions, KServe, Knative drift, ML A/B and dashboards.
7. Capture custom LLM deploy/benchmark/optimization, global config, gateways, registry, MCP tools, two specialists/coordinator, sandbox, replicas/autoscale, warm-up/HA, both UIs and LLM/agent A/B.
8. Generate Locust HTML for required Web APIs and capture parameters/SLA summaries.
9. Capture active F5 NGINX OSS version/digest, retired-controller rejection, hidden services, basic auth/rate limit, valid HTTPS/domain, Terraform, mandatory Vast.ai Ansible role health/idempotent second run/cost/teardown, Vault, Istio authorization, metrics/logs/traces and telemetry.
10. Capture design-pattern code, five classes per track, and working proof for two novel ideas per track.
11. Export evidence manifest to immutable S3, fetch it with source-side CI, run strict two-repo auditor plus every row's behavior-validation command, mock-grade independently against the original 57+60 rows, resolve every gap, then freeze both 40-hex submission SHAs.
12. Destroy EKS before TTL, verify zero live session-tagged resources, and record retained monthly-cost inventory.

## Reviewer Document Set

- `README.md`: business, TOC, repo map and high-level numbered deployment diagram. Every deployable is a node, every primary edge is solid, numbered/described, and included in a flow legend; repository-wide file/module/class/function docstrings are checked.
- `docs/phase2/ml.md`, `llm.md`, `data-and-feast.md`, `gitops.md`, `iac.md`, `security.md`, `observability.md`, `testing.md`, `cost-and-operations.md`.
- `docs/phase2/evidence/index.md`: rubric-ID index linked to reports, screenshots and raw outputs.
- `docs/phase2/low-level-design.md`: five classes per track and design patterns.
- `docs/phase2/novel-ideas.md`: four ideas and executed proof.

## Validation

- `python scripts/audit_phase2_evidence.py --strict --require-executed --run-validations --phase1-base "$PHASE1_BASE_SHA" --gitops-root "$GITOPS_CHECKOUT" --ml 100 --llm 100`

Before promotion, record `PHASE1_BASE_SHA` as the immutable 40-hex commit
immediately before Phase 2 work. Do not substitute a moving branch name. The
gate compares every evidence source/GitOps SHA with the two checked-out
`HEAD`s and rejects protected Phase 1 changes against that frozen baseline.
Both source and GitOps checkouts must be clean; the recorded commits therefore
contain the implementation, manifests, and evidence that the auditor reads.
- Link/image integrity, duplicate/stale screenshot, secret/PII, timestamp/version and rubric-total checks.
- Independent manual mock grade using the two original CSVs, not the implementation checklist alone.
- AWS resource inventory and cost report after destroy.

## Success Criteria

- [ ] Coursework reviewer -> opens either rubric -> follows every scored row to an explained, executed and version-matched artifact.
- [ ] Evidence auditor -> evaluates the frozen submission -> reports ML 100/100 and LLM 100/100 with no missing, stale, secret-bearing or design-only proof.
- [ ] Reviewer -> inspects README and detailed docs -> understands deployable units, numbered data flows, classes, patterns, security and operating limits.
- [ ] Cost owner -> closes the session -> sees EKS destroyed before hard TTL and retained resources within the declared monthly cap.
- [ ] Maintainer -> checks final source and GitOps SHAs -> can reproduce the release and roll it back through Git alone.

## Risks and Rollback

- Risk: screenshot-heavy evidence becomes stale after a late release. Mitigation: manifest version checks reject mismatched SHA/digest/timestamps.
- Rollback: do not rewrite evidence to match claims; revert the bad release, rerun the affected scenario, replace its evidence atomically, and re-audit.
