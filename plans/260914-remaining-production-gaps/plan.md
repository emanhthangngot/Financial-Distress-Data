---
title: "Remaining production gaps: Jenkins, LangGraph and deployment proof"
description: "Execute only unfinished work identified from the existing Financial-Distress-Data baseline; completed code and evidence remain unchanged."
status: in-progress
priority: P1
branch: dev
blockedBy: []
blocks: []
created: 2026-09-14
revised: 2026-09-14
---

# Remaining production gaps

## Purpose

This is a gap-only execution plan. It does **not** replace or repeat the historical unified P0-P12
architecture plan at `../260831-1644-rebuild-target-mlops-architecture/`. It records only work that
is still missing, unproven, stale or blocked in the current repository.

Do not rewrite completed source, preserve valid existing auth/UI/data paths, and do not recreate
already executed evidence. A task is complete only when its real behavior is exercised and its
revision-attributable evidence is captured.

## Baseline used

Observed repository state:

- Local quality gate passes: 376 passed, 2 xfailed; this is source-level proof only.
- Rubric matrix contains 161 rows / 300 points: 60 executed, 57 design-only and 44 pending.
- Strict production evidence audit reports 129 findings.
- No Jenkinsfile, Jenkins controller/JCasC/plugin catalog or Jenkins delivery runtime exists.
- No LangChain/LangGraph dependency or production graph implementation exists.
- Existing GKE has zero node-pool capacity; quota bundle is not granted. P4/P6 live work is blocked.
- Existing code and evidence are retained; no baseline evidence is deleted by this plan.

## Non-goals

- No rewrite of completed features.
- No second architecture or parallel agent runtime.
- No test-count expansion unrelated to a real behavior risk.
- No paid cloud/API/GPU capacity.
- No claim of production readiness from local tests, screenshots or YAML alone.

## Remaining work map

| Gap | Current state | Owner | Exit proof |
|---|---|---|---|
| P0 capacity and compatibility | Cloud quota hard stop; provider/Kaggle/domain/Jenkins gates incomplete | Gap-01 | Dated pass/blocked ledger |
| Data contract and pipeline | v2 temporal contract specified, implementation/evidence incomplete | Gap-02 | Fresh data through Gold with temporal checks |
| Streaming and features | Existing paths require real CDC/Feast/rolling-feature proof | Gap-02 | Real record through offline/online stores |
| Platform and Jenkins | Runtime absent; existing GKE has no workload capacity | Gap-03 | Restored controller, ephemeral agent, isolated credentials |
| ML and agents | ML production proof incomplete; hand-written agent path remains | Gap-04 | Promoted model and LangGraph parity/cutover proof |
| Serving and release | End-to-end production path and Jenkins lanes incomplete | Gap-05 | GitOps/Argo smoke, failure and rollback evidence |
| Evidence freeze | 129 strict audit findings remain | Gap-06 | Current attributable evidence and zero missing required rows |

## Execution order

`Gap-01` gates live work. `Gap-02` may continue locally after the local gate. `Gap-03` must
establish Jenkins before `Gap-05`. `Gap-04` may prepare locally, but its live exit consumes Gap-02
outputs. `Gap-06` captures incrementally and freezes only after Gap-05.

## Shared contracts

- v2 data contract from the existing unified plan remains authoritative: `known_from_ts`,
  `company_version_key`, `ticker`, `DECIMAL(18,0)` money, `DECIMAL(18,6)` ratios, `raw_`/`stg_`
  naming, vintage-preserving facts and Feast `event_timestamp`/`created_timestamp`.
- Jenkins builds, scans, signs and opens digest-only GitOps PRs. Argo CD alone mutates production.
- LangChain owns model/tool integration and middleware; LangGraph owns graph execution/checkpoints.
  Repository code retains MCP policy, auth, citation/abstention, circuit breaker, pgvector schema
  and external SSE compatibility.
- Existing successful behavior is the regression baseline; migration must preserve public contracts.

## Definition of done

The remaining work is complete only when the final operator can run one fresh-data analyst request
through feature retrieval, model inference, LangGraph/MCP/API/UI, Jenkins promotion and Argo
convergence; induce provider and rollout failures; observe explicit degraded/incomplete states;
restore the prior compatible release; and export redacted evidence tied to source SHA, GitOps SHA,
Jenkins build, artifact digest and runtime revision.
