---
title: "Achieve Mini Coursework Rubric 100"
description: "Implement and prove every item in the checked-in 100-point rubric."
status: completed
priority: P1
effort: "large; estimated 6-10 focused implementation weeks"
tags: [coursework, data-engineering, airflow, spark, flink, datahub]
created: 2026-07-21
---

# Achieve Mini Coursework Rubric 100

## Overview

Move from a fixture-backed Stage 1 prototype to a rubric-complete, reproducible local data platform. Every point requires implementation, automated validation, and the exact reviewer-facing proof requested by the rubric.

Audit context: [deep audit](../reports/deep-audit-260721-1033-mini-coursework-100.md).

Execution contract: [45-row rubric implementation matrix](./reports/rubric-implementation-matrix.md).

## Current Status

- Phases 1-9 completed; implementation, correlated evidence package, and mock grading are verified.
- Spark evidence proves equivalent output, 1.5595x median compute improvement, storage compaction, and PostgreSQL index use.
- Flink evidence proves event-time windows, late routing, TTL deduplication, burst handling, checkpoints, and savepoint restore.
- Final automated rubric audit: 100/100 across all 45 criteria.

## Planning Assumptions

- Full checked-in rubric remains authoritative; internal “platform .ubset” wording does not reduce scope.
- Use **PyFlink** initially to preserve the Python-first repository. Switch to Java only if a required API or connector cannot be verified in PyFlink.
- Use **DataHub**, not a substitute, because the rubric names DataHub explicitly.
- Keep raw Parquet + MinIO unless storage experiments prove a table format is needed; do not add Iceberg/Delta only for appearance.
- Novel ideas default to: cryptographically correlated evidence manifests and PIT-safe feature generation with automated leakage audit. Confirm with instructor before Phase 8 polish.
- CI uses small deterministic datasets; benchmark/evidence profiles use larger local datasets with recorded hardware and seed.

## Point Delivery Map

| Delivery phase | Rubric block | Points unlocked | Exit condition |
|---|---|---:|---|
| 3 | Offline + streaming generator | 20 | All seven problem types measured from configured output |
| 4 | Spark processing + storage optimization | 16 | Baseline/optimized correctness and before/after proof |
| 5 | Flink stream processing | 10 | Event-time window, late data, duplicate and burst proof |
| 6 | DP1/DP2/DP3 orchestration | 12 | Three real DAGs with ingest/validate UI evidence |
| 7 | Data governance | 12 | DataHub lineage, assertions and contracts for all DPs |
| 8 | README, Docker, schema docs, novel ideas | 30 | All human-facing proof complete and reproducible |
| **Total** |  | **100** | Phase 9 clean-room audit passes |

Phases 1-2 stabilize evidence and runtime correctness. They do not add separate rubric points but prevent later points from being rejected.

## Phases

| # | Phase | Status | Depends on |
|---|---|---|---|
| 1 | [Rubric contract and evidence foundation](./phase-01-start.md) | Completed | - |
| 2 | [Correct existing runtime contracts](./phase-02-correct-existing-runtime-contracts.md) | Completed | 1 |
| 3 | [Build configurable problem generator](./phase-03-build-configurable-problem-generator.md) | Completed | 1, 2 |
| 4 | [Spark optimization and storage proof](./phase-04-implement-spark-optimization-and-storage-proof.md) | Completed | 2, 3 |
| 5 | [Flink streaming processing](./phase-05-implement-flink-streaming-processing.md) | Completed | 3 |
| 6 | [Rubric DP1/DP2/DP3 Airflow pipelines](./phase-06-build-rubric-dp1-dp2-dp3-airflow-pipelines.md) | Completed | 3, 4, 5 |
| 7 | [DataHub governance and lineage](./phase-07-integrate-datahub-governance-and-lineage.md) | Completed | 6 |
| 8 | [Documentation, Docker, schema, novel ideas](./phase-08-complete-documentation-docker-and-novel-ideas.md) | Completed | 4, 5, 6, 7 |
| 9 | [Submission evidence and mock grading](./phase-09-run-submission-evidence-and-mock-grading.md) | Completed | all |

## Dependencies

- Local Docker resources sufficient for Airflow, Kafka, Flink, DataHub, PostgreSQL, MinIO, and Spark. Use profiles so the full stack is not required for unit tests.
- Instructor decisions listed in the deep audit should be resolved before locking Flink language and novel ideas.
- Evidence must come from a clean, correlated run; old evidence cannot substitute.

## Critical Path

```text
platform .> platform .> Phase 3 -> Phase 4 -> Phase 6 -> Phase 7 -> Phase 8 -> Phase 9
                              \-> Phase 5 -/
```

Phase 4 and Phase 5 may execute in parallel only after Phase 3 generator contracts freeze. Documentation drafts may start early, but screenshots and performance claims wait for verified runtime output.

## Execution Rules

1. Start each behavior change with a failing focused test or measurable baseline.
2. Do not mark a rubric row complete from code alone; implementation, automated check, document, and proof must all exist.
3. Keep one `run_id` from generator through DP1/DP2/DP3, DataHub, SQL exports, metrics, and screenshots.
4. Never overwrite accepted evidence or the last good dataset before replacement validation passes.
5. Use Compose profiles: `core`, `flink`, `governance`, and `evidence` to control resource usage.
6. Update as-built docs only after runtime verification; planned claims stay in this plan.
7. Review after Phases 2, 5, 7, and 9 because they cross public/runtime contracts.

## Milestones

| Milestone | Target state | Estimated cumulative effort |
|---|---|---:|
| M1 Runtime trustworthy | Phases 1-2 complete | 1.5-2.5 weeks |
| M2 Data problems reproducible | Phase 3 complete | 2.5-3.5 weeks |
| M3 Processing evidence complete | Phases 4-5 complete | 4-6 weeks |
| M4 Platform rubric complete | Phases 6-7 complete | 5.5-8 weeks |
| M5 Submission ready | Phases 8-9 complete | 6.5-10 weeks |

## Acceptance Criteria

- [x] Each of the 45 scored rubric rows maps to code/config, automated validation, document, and proof artifact.
- [x] DP1, DP2, and DP3 run independently and end-to-end from Airflow.
- [x] Spark and Flink baseline/optimized experiments are reproducible and measured.
- [x] DataHub shows lineage, validation/assertions, and contracts for all three pipelines.
- [x] Generator metrics prove all required offline and streaming problems.
- [x] Schema evidence proves all zones, SCD2 history, feature timestamps, and dim/fact relationships.
- [x] Two novel ideas have implementation, evaluation, and runtime proof.
- [x] A clean-room reviewer command produces a 100/100-ready evidence index with no stale artifacts.
- [x] Full automated gates pass without unsupported claims.

## Rollback Principle

Every phase stays behind explicit configuration/profile boundaries until verified. Preserve the current Stage 1 path while replacing misleading stubs; do not delete the last known-good dataset during a failed run.

<!-- slug: achieve-mini-coursework-rubric -->
