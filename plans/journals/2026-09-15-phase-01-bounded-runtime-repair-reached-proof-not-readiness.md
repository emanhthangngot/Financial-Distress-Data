---
title: "Phase 01 Bounded Runtime Repair Reached Proof, Not Readiness"
date: 2026-09-15
summary: "Phase 01 repaired drift, proved bounded NVL materialization and platform E2E, but remains BLOCKED/PARTIAL on authorization, durability, and external gates."
---

# Phase 01 Bounded Runtime Repair Reached Proof, Not Readiness

**Date**: 2026-09-15 03:15 +07
**Severity**: High
**Component**: Phase 01 GKE, GitOps, lakehouse producer, Feast, and observability
**Status**: BLOCKED/PARTIAL

## What Happened

On the existing GKE node, reconciliation first exposed SealedSecrets encrypted for the pre-rotation controller key; we resealed them with the active certificate. Next we fixed the observability namespace mismatch, a Prometheus NetworkPolicy namespace mismatch, MCP image/environment drift, the omitted Feast Redis port, and a stale/nonexistent producer image via GitOps commits `ae79945`, `8052af9`, `ec5a305`, `4d26f08`, `c213119`, `5b0cf4a`, and `e9cec0c`.

Producer attempts then exposed application defects: Bronze and Silver resolved to colliding object keys, and timestamp strings reached Parquet/Feast instead of typed timestamps. Source commits `45db6f1` and `4bd9474` fixed payload-path mapping and timestamp-aware Parquet fields; `6ddc216` recorded the dated gate evidence.

## The Brutal Truth

This was maddening because none of it was exotic: copied namespace configuration, credentials bound to a dead encryption key, and an image contract that existed only in assumptions. Each fix exposed another stale layer. The successful run brought relief, but calling it production-ready would be dishonest.

## Technical Details

Job `lakehouse-gold-producer-live-1789416417` succeeded with `gold_rows=843`, `risk_rows=16`, and risk tickers `HPG,NVL`. Feast materialized `company_risk_features`; direct NVL lookup returned numeric values including `z_score=-1.3011` and `distress_label=1`. Platform E2E returned `status=PASS` for workloads/services, model warm-up, coordinator round-trip, five Prometheus targets, and five Jaeger services. The repository gate recorded `377 passed, 2 xfailed`; this task reran nothing.

## What We Tried

A rebuilt timestamp-fix image was preferred over runtime injection, but the first full rebuild hit `100%` local root filesystem before export. We then used the previously pushed digest plus a temporary source ConfigMap for the bounded proof, and deleted that ConfigMap. The proof demonstrated behavior, not durable convergence at that point.

## Root Cause Analysis

The root cause was uncontrolled drift across encryption state, namespaces, deployment env, image references, storage-key semantics, and timestamp types. We rejected new cloud capacity, quota requests, and destructive cleanup because they would hide the defects while risking cost or data.

## Lessons Learned

Validate secrets against the active controller, test namespace selectors against live labels, pin runnable digests, and carry typed timestamps across every storage boundary. A green one-off run is not GitOps durability.

## Next Steps

Platform owner: obtain an approved window, teardown deadline, and backup/export destination before more runtime work. External owners must still prove Jenkins, provider access, LangGraph, domain/HTTPS, Kaggle/GPU, and row-level stale/recapture gates. Keep Phase 01 BLOCKED/PARTIAL. The CronJob stays suspended; `fsds-evidence-worker` stays TERMINATED, its disk preserved, Kourier stays `ClusterIP`, and no PV/PD, backup, or cloud data is deleted.

## Subsequent reconciliation

After this entry was drafted, GitOps authentication was restored through the repository's SSH remote. Producer promotion `55611f1`, suspension `34030fb`, and timestamp-safe image promotion `94b1d5d` were pushed. The final Artifact Registry digest is `sha256:be91a7bb6843bf8f73b73d55f9dc2f131b1070a1a22041954258025d216ec40d`; the bounded job itself remains the run with the temporary source mount, while no second cloud run was started.

## Review correction

The read-only review then reproduced a NULL-destroying epoch substitution for nullable timestamp fields in the first image. Source commit `0b7c025` preserves Arrow NULLs and keeps `report_release_date` on its prior non-timestamp path; the final image promotion `d6d7c59` carries that fix. A second bounded Job, `lakehouse-gold-producer-live-1789416418`, succeeded with the final digest and replaced the first run as clean evidence. Commit `b5096f7` also makes the platform E2E runner restore a hibernated model revision after its coordinator follow-up or on warm-up failure. Phase 01 remains BLOCKED/PARTIAL because the full Argo application is still degraded on the pre-existing dataflow SealedSecret and the external authorization and evidence gates remain open.

AgentWiki publish skipped. Local journal is the source of truth.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
