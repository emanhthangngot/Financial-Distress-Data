---
title: "Phase 8: Produce evidence, mock-grade and promote"
status: todo
estimate: "6-8 days"
---

# Phase 8: Produce evidence, mock-grade and promote

## Overview

Run the system, capture reviewer-readable proof for every scored row, audit claims against artifacts, perform independent mock grading, promote the final Git revisions, and destroy the evidence plane.

## Evidence Rules

- Every artifact records requirement ID, execution timestamp, source SHA, GitOps SHA, image/model/data/agent versions, command/scenario, expected result, actual result and redaction status.
- Screenshots supplement machine-readable outputs; they never replace logs/reports/manifests when the latter are available.
- Each major `docs/phase2/` section explains what an image proves. No orphan screenshot dump.
- “Designed”, “configured”, “executed”, and “passed” remain distinct statuses.
- Capture only the relevant window/region and redact account IDs, hosts where needed, tokens, emails and private data.

## Mandatory Evidence Runs

1. Run Phase 1 full quality/evidence gate to prove no regression.
2. Run coverage, changed-code mutation, equivalence/boundary, Hypothesis and security gates for both tracks.
3. Provision one named EKS evidence session; capture cost preview, TTL, Terraform outputs and state timeline.
4. Capture Argo sync waves, GitOps commit/digest, rolling update/atomic fallback, autoscaling for feature and drift APIs, and Git-revert rollback.
5. Capture Feast materialization/offline+online stream jobs, TTL rationale, Airflow ordering, DataHub lineage, drift config/label merge and versioned data.
6. Capture notebook, successful KFP distributed training, MLflow model/data versions, KServe, Knative drift, ML A/B and dashboards.
7. Capture custom LLM deploy/benchmark/optimization, global config, gateways, registry, MCP tools, two specialists/coordinator, sandbox, replicas/autoscale, warm-up/HA, both UIs and LLM/agent A/B.
8. Generate Locust HTML for required Web APIs and capture parameters/SLA summaries.
9. Capture NGINX hidden services, basic auth/rate limit, valid HTTPS/domain, Terraform, Ansible, Vault, Istio authorization, metrics/logs/traces and telemetry.
10. Capture design-pattern code, five classes per track, and working proof for two novel ideas per track.
11. Export evidence manifest, run strict auditor, mock-grade independently by row, resolve every gap, then freeze submission SHA.
12. Destroy EKS before TTL, verify zero live session-tagged resources, and record retained monthly-cost inventory.

## Reviewer Document Set

- `README.md`: business, TOC, repo map and high-level numbered deployment diagram only.
- `docs/phase2/ml.md`, `llm.md`, `data-and-feast.md`, `gitops.md`, `iac.md`, `security.md`, `observability.md`, `testing.md`, `cost-and-operations.md`.
- `docs/phase2/evidence/index.md`: rubric-ID index linked to reports, screenshots and raw outputs.
- `docs/phase2/low-level-design.md`: five classes per track and design patterns.
- `docs/phase2/novel-ideas.md`: four ideas and executed proof.

## Validation

- `python scripts/audit_phase2_evidence.py --strict --require-executed --ml 100 --llm 100`
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
