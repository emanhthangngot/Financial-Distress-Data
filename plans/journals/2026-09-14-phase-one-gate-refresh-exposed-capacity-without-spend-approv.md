---
title: Phase One Gate Refresh Exposed Capacity Without Spend Approval
date: 2026-09-14
summary: "Read-only gate refresh preserved the evidence baseline, found one Ready GKE node and two live load balancers, and kept cloud work blocked by quota and spend controls."
---

# Phase One Gate Refresh Exposed Capacity Without Spend Approval

**Date**: 2026-09-14 14:52 +07
**Severity**: High
**Component**: Production readiness gates / GKE
**Status**: Resolved for inventory; downstream work remains blocked

## What Happened

Phase 01 refreshed the live production gates without changing infrastructure. Work began from local `dev` revision `5fa76e1`, preserved the `evidence-baseline-pre-rebuild` tag and evidence tree, and merged back into local `dev`. Only the dated gate ledger and phase acceptance state changed; unrelated dirty work was untouched.

The refresh disproved one stale assumption: `fsds-evidence` now has one Ready GKE node (`v1.35.7-gke.1222000`). That is current inventory, not permission to deploy.

## The Brutal Truth

The frustrating part is that a live node looks like progress while the production path remains unsafe. We have capacity-shaped evidence, not an approved capacity window. Pretending otherwise would create unbudgeted cloud changes and surprise spend.

## Technical Details

Billing is enabled. In `asia-southeast1`, quota reports `CPUS=32` with usage `9`, `E2_CPUS=8` with usage `0`, and `PREEMPTIBLE_CPUS=0` with usage `0`. The cluster has one Ready node, but NGINX and Kourier still expose two `LoadBalancer` services; the target invariant is exactly one external entry point. No root `Jenkinsfile`, Jenkins runtime/catalog surface, or checked-in production LangGraph/LangChain implementation exists. Domain/HTTPS and Kaggle/GPU access were not exercised.

## What We Tried

We ran read-only billing, quota, cluster, node, service, tag, and repository-inventory checks. We did not run Terraform apply, mutate Kubernetes, request quota, call paid APIs, or create billable resources. Deleting either load balancer was rejected because an unreviewed cutover could break ingress.

## Root Cause Analysis

The blockers are not a flaky command or missing retry. Production work was planned before its spend window, teardown controls, external-entry cutover, Jenkins runtime, and LangGraph runtime were proven. The prior capacity report went stale; historical evidence cannot be relabeled as current proof.

## Lessons Learned

Recheck live gates immediately before cloud work, but never confuse observation with authorization. Preserve attributable baseline evidence, timestamp new facts, and keep `BLOCKED` or `UNVERIFIED` labels until the real runtime is exercised. A Ready node does not cancel a zero preemptible-CPU quota or an unresolved cost invariant.

## Next Steps

Before cloud-backed work, the platform owner must obtain an approved zero-spend window, document teardown and backup/export paths, confirm residual-cost controls, and review an atomic two-to-one load-balancer cutover. Phase 03 stays blocked on Jenkins and platform proof. Local preparation may continue for phases 02 and 04; phases 05 and 06 remain pending. The ML owner must prove LangGraph parity; serving and ML owners must separately prove HTTPS and Kaggle/GPU gates before claiming completion.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
