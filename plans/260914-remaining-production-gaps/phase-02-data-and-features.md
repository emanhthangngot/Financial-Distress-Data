---
phase: 2
title: "Gap 02: Complete data and feature runtime"
status: in-progress
priority: P1
effort: "Remaining implementation after local inventory"
dependencies: ["phase-01-gates-and-inventory.md"]
---

# Gap 02: Complete data and feature runtime

## Objective

Finish only the missing v2 contract implementation and real data-plane behavior. Preserve working
fixture paths and existing Bronze evidence.

## Tasks

1. Complete temporal SCD2, vintage, label-boundary and as-of fixes in the owned files.
2. Migrate active Gold readers to the v2 Iceberg contract without dual production paths.
3. Implement real adapter/generator behavior for source units, unavailable history and restatements.
4. Mirror Python semantics in Spark and run one fresh Airflow Bronze-to-Gold request.
5. Complete CDC, genuine rolling windows, Feast offline/online jobs and materialization.
6. Produce the four P5 delivery contracts for later Jenkins catalog registration.

## Progress snapshot

Local implementation slices are partially evidenced on `dev` working tree: temporal contracts remain covered by the existing focused suite; `.venv-platform/bin/python -m pytest tests/platform/test_spark_gold_value_parity.py -q` passes 5 tests for actual PySpark/Python values, keys, grain, timestamps and provenance; and `.venv/bin/python -m pytest tests/test_vnstock_live_adapter.py -q` passes 12 adapter tests for VCI/KBS units, tier-cap routing and synthetic provenance at the adapter boundary. Review found that synthetic provenance is not yet carried through the schema contract and that Feast was missing from the declared platform extra; both remediations are in progress. The earlier 5-test Feast result came from a pre-existing environment and is not clean-environment evidence. A fresh cluster Feast materialization remains unexecuted because local MinIO, Redis and PostgreSQL services are stopped.

## Acceptance criteria

- [x] Data pipeline -> replays a restatement and queries an earlier cutoff -> the existing temporal SCD2/as-of focused suite preserves the original eligible vintage and rejects future knowledge.
- [x] Spark job -> processes the same fixture as Python -> 5 local PySpark parity tests match grain, keys, timestamps, provenance and derived values.
- [ ] Collector -> requests unavailable historical periods -> adapter tests exercise `tier_period_cap`, but the synthetic provenance marker is currently dropped at the schema boundary; AC3 remains open until provenance is contract-carried and consumed downstream.
- [ ] Feast -> materializes a fresh feature record -> 5 disposable Feast tests prove offline/online knowledge-time identity, but fresh cluster materialization evidence is still blocked by stopped services.

## Files

Use ownership from the existing unified plan only; no new parallel data architecture.

## Risks

This is the highest data-integrity risk. Stop downstream model claims if parity or temporal checks fail.
