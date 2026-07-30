---
phase: 2
title: "Correct Existing Runtime Contracts"
status: completed
priority: P1
effort: "1-2 weeks"
dependencies: [1]
---

# Phase 2: Correct Existing Runtime Contracts

## Overview

Fix reproduced defects so later rubric work builds on trustworthy data.

## Requirements

- Atomic Silver/Gold publication.
- Typed failures instead of broad empty fallbacks.
- Consistent Python/Spark semantics.
- Real SCD2 history and persisted rejected records.
- Config-backed schemas and DQ.

## Related Code Files

- Modify: `src/jobs/stage1_spark_lakehouse_job.py`
- Modify: `src/transforms/silver/`, `src/transforms/gold/`, `src/transforms/features/`
- Modify: `src/quality/`, `src/metadata/`, `src/streaming/`
- Modify: `configs/*.yaml`, `sql/init_project_metadata.sql`
- Create focused integration tests under `tests/`

## Implementation Steps

1. Add tests for timezone dedup, blanks, invalid numbers/timestamps, latest event dedup, future freshness, null RI, SCD2 across runs, and PIT timestamps.
2. Parse timestamps and numeric fields explicitly; quarantine invalid rows.
3. Preserve company snapshots and maintain SCD2 state across runs.
4. Deduplicate all event facts by deterministic ID plus latest `created_ts`.
5. Join sector metadata before distress labeling and make exclusion config-driven.
6. Persist rejected Silver rows with run linkage.
7. Stage all outputs, run DQ, then promote atomically.
8. Remove or accurately rename smoke DAGs.

## Task Breakdown

| ID | Task | Primary files | Required tests |
|---|---|---|---|
| P2-T1 | Introduce typed schema with field types, blank policy, enums and timestamp parsing | `src/metadata/`, `configs/` | Schema compatibility + invalid-row tests |
| P2-T2 | Fix latest-row dedup in Python/Spark and deterministic event IDs | Silver/Gold/streaming modules | Timezone, replay and duplicate tests |
| P2-T3 | Make sector exclusion config-driven and join company metadata before labels | labels + Gold job | Financial-sector golden cases |
| P2-T4 | Implement historical SCD2 state across runs | company transform + storage | Two-run/no-change/null/change tests |
| P2-T5 | Persist rejected rows and source lineage metadata | Silver job + metadata writer | PostgreSQL integration test |
| P2-T6 | Replace broad stream fallback with typed optional-input policy | Spark runtime job | Missing optional vs corrupt input tests |
| P2-T7 | Implement staged write, DQ gate and promotion | IO + Spark job | Failure preserves previous snapshot |
| P2-T8 | Align Python and Spark semantics using common golden datasets | tests | Differential result comparison |
| P2-T9 | Fix DQ freshness, null RI, missing input and configured rules | quality modules | Edge-case DQ tests |
| P2-T10 | Split oversized Spark runtime module along real boundaries | `src/jobs/` | Existing API compatibility tests |

## Validation

```bash
python -m pytest -q tests/test_bronze_to_silver.py tests/test_silver_to_gold.py tests/test_distress_labels.py tests/test_dq_checks.py
python -m pytest -q tests/integration/test_scd2_pipeline.py tests/integration/test_atomic_publish.py
python -m ruff check src tests
python -m black --check src tests
```

## Evidence Outputs

- Regression report for every reproduced defect from the deep audit.
- Two-run SCD2 query output.
- Atomic-publication failure probe.
- Rejected-record PostgreSQL query output.
- Completion report: [Phase 2 runtime contracts](./reports/phase-02-260722-1349-runtime-contracts.md).

## Success Criteria

- [x] Every reproduced probe becomes a passing regression test.
- [x] Failed build leaves the previous published snapshot intact.
- [x] Corrupt stream input fails rather than producing empty facts.
- [x] Company changes produce valid SCD2 history in the stateful transform; repeated full-pipeline execution preserves the no-change state.
- [x] Python and Spark use the same typed contracts and pass shared contract fixtures plus the real Spark evidence run.

## Risks And Rollback

Schema changes require a new registry version and backfill. Keep readers compatible with the previous dataset version until migration proof passes.

## Resolved Design Decision

Keep deterministic `company_key` stable for fact relationships and use a separate `company_version_key` for each SCD2 version. This preserves existing joins while making historical versions individually addressable.
