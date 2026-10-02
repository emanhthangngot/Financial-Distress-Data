---
phase: 6
title: "Gap 06: Close evidence and production freeze"
status: pending
priority: P1
effort: "Remaining evidence capture"
dependencies: ["phase-05-serving-and-release.md"]
---

# Gap 06: Close evidence and production freeze

## Objective

Re-capture only missing or stale evidence and prove the integrated release, failure and rollback
journey. Existing valid evidence remains untouched.

## Tasks

1. Re-run the strict evidence audit and classify the 129 findings by owning gap.
2. Capture rows only after their producing behavior passes in the required runtime.
3. Join each release row to source SHA, GitOps SHA, Jenkins build, artifact digest and Argo revision.
4. Exercise fresh-data, provider-unavailable, interrupted-stream, bad-rollout and rollback paths.
5. Update current docs/evidence navigation and export redacted artifacts before teardown.
6. Run the final consistency, naming, rubric and production readiness checks.

## Progress snapshot

Architecture inventory and local rubric matrix are refreshed: 9 Mermaid sources have 9 dry-run HTML
renders, `verify_target_architecture.py` passes, and `verify_rubric_coverage.py` reports 161 rows
and 300 points with no structural findings. The current mini runtime audit reports 96/100 with four
partial generator rows; the immutable historical package fails current hash validation and the
root evidence package is absent. Fresh provider, cluster, Jenkins and protected-edge evidence is
therefore not yet frozen. This phase remains pending.

## Acceptance criteria

- [ ] Evidence runner -> processes every required row -> no required row is missing, stale or falsely marked executed.
- [ ] Operator -> runs the integrated production scenario -> success, degraded, incomplete and rollback states are visible across UI, logs, metrics, traces and manifest.
- [ ] Release owner -> tears down the resource window -> evidence persists and no unapproved billable resource remains.
- [ ] Reviewer -> follows the current docs -> implementation, blockers and deployment instructions match reality.

## Risks

A green local gate is insufficient. Any cloud/provider/runtime blocker remains explicitly recorded and
prevents a production-ready claim.
