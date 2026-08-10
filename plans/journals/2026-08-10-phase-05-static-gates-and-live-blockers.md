---
title: "Phase 05 static gates and live-evidence blockers"
date: 2026-08-10
phase: 05
status: blocked
---

# Phase 05 static gates and live-evidence blockers

## Context

Phase 2 / LLM-track Phase 05. This records the uncommitted working-tree state
and the Phase 05 status reconciliation; it is not release, GitOps, or runtime
evidence.

## What happened

- Reusable CI now accepts a deployables JSON matrix; six callers grant OIDC
  `id-token: write`. It builds immutable GHCR digests, signs them with cosign,
  passes the digest as an artifact, and targets named real GitOps manifests
  instead of the unused `pipelines/<name>/digest.txt` placeholder.
- Phase 05 verification runs before image builds. Fixture/mock Web API tests,
  equivalence/boundary checks, Hypothesis idempotency tests, and executable
  contract implementations were added. Contracts require injected benchmark
  measurements, so unavailable runtime timings are not fabricated.
- Review-driven corrections preserved the real GitOps branch and package-write
  requirements, added a build dependency on both verification gates, and fixed
  static NetworkPolicy routes for CronJobs and the feature API.

## Hard gates

- Source verification: **60 passed, 6 skipped**.
- Web API coverage: **96.17% lines** (352/366) and **93.48% branches**
  (43/46), above the 90% gate.
- Mutation scope `llm.rag.chunking.*`: **62/72 killed, 9 survived, 1 timeout**
  = **86.11%**, above the strict >80% gate.
- The default matrix audit cannot establish its merge base because
  `origin/dev` is not an ancestor of `HEAD`; it passed only with
  `--git-base dev`.

## Decision and next

Phase 05 remains **blocked**. No signed release run, GitOps PR/merge, Argo
rollout, changed pod image, gateway Locust HTML, cold/warm measurement, or A/B
comparison exists. The cluster is not running; the A/B path is not yet proven
connected to live `agentgateway`, and warm-pool scale-down still needs an
evidence-window/HPA control design. Therefore no rubric row or evidence file
is claimed as executed.

> Historical work record — the Phase 05 plan and status reconciliation remain
> the current authority.
