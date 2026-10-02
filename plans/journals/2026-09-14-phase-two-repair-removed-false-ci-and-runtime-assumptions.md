---
title: Phase Two Repair Removed False CI and Runtime Assumptions
date: 2026-09-14
summary: "Phase 02 replaced a nonexistent CI manifest, made direct script imports and Redis ports explicit, passed focused verification, and remains blocked on stopped MinIO and Redis services."
---

# Phase Two Repair Removed False CI and Runtime Assumptions

**Date**: 2026-09-14 16:52 +07
**Severity**: High
**Component**: Phase 02 CI, cluster pipeline, and Feast runtime configuration
**Status**: Blocked on runtime services

## What Happened

Phase 02 repaired four concrete defects in commit `a01e29f`: CI installed the nonexistent `requirements-phase2.txt`; `scripts/run_cluster_pipeline.py` assumed the repository root was already on `sys.path`; Feast hardcoded Redis port `6379`; and the feature MCP image did not provide `FEAST_REDIS_PORT` during `feast apply`. The repair added `requirements-platform.txt`, installed the project extras plus that manifest in `.github/workflows/phase2-ci.yaml`, bootstrapped the repository root for direct script execution, and made Redis host/port configuration consistent.

## The Brutal Truth

We wired a verification workflow to a file that did not exist and treated shell-specific import behavior as an application contract. That is careless, and it made the pipeline look more complete than it was. The frustrating part is that these were boring integration defects, not hard distributed-systems problems; disciplined execution-path checks would have exposed them immediately.

## Technical Details

The direct invocation failure mode was `ModuleNotFoundError: No module named 'src'`. `feature_repo/structured/feature_store.cluster.yaml` now uses `${FEAST_REDIS_HOST}:${FEAST_REDIS_PORT},db=0`, while both the script and Docker build default the port to `6379`. Fresh verification passed 32 focused tests, Ruff, Black, `.venv-platform` `pip check`, `python scripts/run_cluster_pipeline.py --help`, and `docker compose --profile platform config`.

## What We Tried

We chose one platform manifest instead of recreating the obsolete Phase 02 manifest, and explicit script bootstrapping instead of requiring callers to remember `PYTHONPATH=.`. We rejected another hardcoded Redis port because it would preserve configuration drift. We did not start services or fake a materialization result.

## Root Cause Analysis

The root cause was verification designed around assumed launch context and stale dependency wiring rather than the commands CI and operators actually run. Configuration ownership was also split: Redis host was injectable while its port was silently fixed elsewhere.

## Lessons Learned

Run entry points exactly as documented, require every CI manifest to exist in the checked-out tree, and keep endpoint host and port under the same configuration contract. Static configuration success is not runtime proof.

## Next Steps

The platform owner must start MinIO and platform Redis in the next approved runtime window and confirm listeners. The Phase 02 owner must then run full Feast materialization, capture the result, and only then update acceptance evidence. Until that happens, the plan criteria stay unchecked; Phase 01 also remains blocked by external cloud, spend, and ownership controls.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
