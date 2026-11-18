---
title: "GCP runtime health fix"
date: 2026-08-13
timezone: Asia/Ho_Chi_Minh
branch: dev
platform: Linux
status: complete
tags: [phase2, gcp, gitops, runtime]
---

# GCP runtime health fix

**Date**: 2026-08-13 12:59
**Severity**: High
**Component**: platform .KE/ArgoCD runtime health
**Status**: Resolved with residual risk

## What Happened

We finished the runtime-health repair without changing platform .pp contracts. The cluster had been carrying a mix of GitOps drift, a broken orphan `default/web` Deployment, and kagent API registration failure. The durable fix landed across GitOps PRs `#50` to `#65`, with the last meaningful convergence in `#61` through `#65`: ignore operator-owned drift where appropriate, split/apply kagent CRDs safely, keep the controller on server-side apply, configure Grafana MCP discovery, and reseal its token with the active controller certificate.

## The Brutal Truth

This hurt because the platform was not actually “broken” in one clean way. It was broken in layers: Argo noise hiding real ownership mistakes, CRDs too large for the old apply path, and a web deployment surviving in the wrong namespace long enough to confuse everything. The exhausting part is that this was avoidable. We let operational drift and partial fixes accumulate until the cluster became harder to reason about than the product itself.

## Technical Details

- ArgoCD finished at `13/13` applications `Synced/Healthy`.
- kagent CRDs `agents.kagent.dev` and `sandboxagents.kagent.dev` are installed and `Established=True`; controller is ready.
- `kagent-grafana-mcp` reconciled `Accepted=True`, `Reconciled`, with `65` registered tools; direct MCP initialize probe returned HTTP `200`.
- The SealedSecret is now `Synced=True`; the stale-certificate intermediate was replaced, obsolete Viewer service accounts were removed, and temporary token-creator pods were deleted.
- `scripts/run_phase2_e2e.py` passed `28/28`.
- Source gate passed: `311` pytest, `ruff`, `black`, `docker compose config`, Stage 1 evidence audit.
- Product/web gates were already green: `184` tests, typecheck/lint, live e2e `6`, assistant e2e `6`.

## What We Tried

- Replaced the unsafe all-in-one agent apply path with a split CRD/application strategy because the oversized CRD OpenAPI schema was the real blocker.
- Preserved operator-managed drift exceptions instead of fighting controllers Argo does not own.
- Removed the orphan `default/web` path instead of pretending it was a transient health blip.
- Revalidated against live cluster state instead of stopping at rendered manifests.

## Root Cause Analysis

Root cause was not “GCP flakiness.” It was our own operational mess:
- We let an orphan deployment and GitOps-untracked state survive long enough to become normal.
- We used an apply strategy that was wrong for large CRDs, then paid for it with missing API mappings and controller startup failure.
- We mixed real failures with operator-managed drift, which made Argo health noisier and slowed diagnosis.

## Lessons Learned

If a controller owns mutation, teach Argo that explicitly or expect useless drift. If a CRD is large, do not shove it through the same apply path as ordinary workloads. Most importantly, kill orphan resources early; stale runtime objects are how teams waste hours arguing with the wrong symptom.

## Next Steps

1. User/operator -> provide a sealed GHCR `read:packages` credential out-of-band -> cold-node recovery for web becomes real instead of lucky node-cache survival.
2. GitOps maintainers -> keep PRs `#61` to `#65` as the durable reference for runtime-health repair -> do not collapse those fixes back into a broad unsafe app definition.
3. Future runtime checks -> keep reporting the residual plainly -> GHCR private-digest cold pulls are still not self-healing.

AgentWiki publish skipped: `agentwiki` CLI was unavailable in this session, and no AgentWiki MCP capability was exposed here. Local journal is the source of truth.

Status: DONE_WITH_CONCERNS
Summary: Runtime health is repaired and live-verified, but cold-node web recovery still depends on a user-supplied sealed GHCR package-read credential.
