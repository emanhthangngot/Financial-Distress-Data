---
phase: 6
title: "Build Rubric DP1 DP2 DP3 Airflow Pipelines"
status: completed
priority: P1
effort: "1 week"
dependencies: [3, 4, 5]
---

# Phase 6: Build Rubric DP1 DP2 DP3 Airflow Pipelines

## Overview

Replace misleading smoke DAGs with the three independently reviewable pipelines required by the rubric.

## Requirements

- DP1: source data to Bronze plus validation.
- DP2: Bronze to Silver/Gold plus validation.
- DP3: offline feature computation plus validation.
- Reusable Airflow Connections/Variables and run correlation.

## Related Code Files

- Create/replace DAGs under `dags/` for DP1, DP2, DP3
- Modify: `docker-compose.yml`, Airflow initialization
- Create: DAG structure/integration tests
- Create: `docs/data-pipeline-orchestration.md`

## Implementation Steps

1. Define explicit dataset inputs/outputs, task groups, ingest gates, and validate gates.
2. Configure service access via `AIRFLOW_CONN_*` and non-secret runtime parameters via Variables.
3. Add retries, backoff, timeouts, failure callbacks, and manifest finalization.
4. Make each pipeline idempotent for the same data interval.
5. Emit shared run IDs and OpenLineage events.
6. Test DAG import, graph shape, task behavior, failure propagation, and reruns.
7. Capture Airflow graph/grid proof for each pipeline.

## DAG Design

| DAG | Main stages | Inputs | Outputs |
|---|---|---|---|
| DP1 `ingest_source_to_bronze` | resolve run -> ingest batch/stream -> validate Bronze -> publish manifest | Generator source area, Kafka/Flink Bronze sink | Bronze datasets + rejected rows |
| DP2 `build_silver_gold` | read Bronze -> Spark transform -> validate staging -> promote -> publish lineage | Bronze run manifest | Silver + Gold facts/dims/OBT |
| DP3 `build_offline_features` | read PIT inputs -> compute 4Q/30D features -> leakage/quality gate -> promote | Gold facts/dims | `feat_*` tables |

## Task Breakdown

| ID | Task | Test/proof | Rubric points |
|---|---|---|---:|
| P6-T1 | Define Airflow Connections/Variables and bootstrap | Connection resolution test/UI | Shared requirement |
| P6-T2 | Implement DP1 ingest tasks | DAG structure + runtime rows | 2 ingest |
| P6-T3 | Implement DP1 validation/publication | Failure and pass tests | 2 validate |
| P6-T4 | Implement DP2 Spark ingest/build tasks | DAG structure + runtime rows | 2 ingest |
| P6-T5 | Implement DP2 DQ/atomic promotion | Failure and pass tests | 2 validate |
| P6-T6 | Implement actual 4Q/30D PIT feature calculations in DP3 | Golden window tests | 2 ingest |
| P6-T7 | Implement DP3 leakage/quality gate | Future-row rejection test | 2 validate |
| P6-T8 | Add retries, callbacks, run manifest and OpenLineage hooks | Retry/failure tests | Reliability |
| P6-T9 | Retire misleading smoke DAGs | DAG list assertion | Reviewer clarity |

## Validation

```bash
python -m pytest -q tests/test_airflow_dags.py tests/integration/test_dp1.py tests/integration/test_dp2.py tests/integration/test_dp3.py
docker compose exec -T airflow-scheduler airflow dags list-import-errors
docker compose exec -T airflow-scheduler airflow dags test ingest_source_to_bronze <logical-date>
docker compose exec -T airflow-scheduler airflow dags test build_silver_gold <logical-date>
docker compose exec -T airflow-scheduler airflow dags test build_offline_features <logical-date>
```

## Evidence Outputs

- Airflow Graph/Grid screenshots for DP1, DP2 and DP3.
- Task logs with common `run_id`.
- Passing validation queries and intentional-failure screenshots.
- Connections/Variables proof without exposing credentials.

## Success Criteria

- [x] Each DAG has visible ingest and validate stages.
- [x] Critical validation failure blocks publication/downstream triggering.
- [x] Stable object paths and atomic feature promotion make logical reruns idempotent.
- [ ] Airflow screenshots clearly show DP1, DP2, and DP3 order and success.

## Risks And Rollback

Keep one compatibility evidence DAG only if needed; remove or rename stubs so reviewers cannot confuse smoke behavior with real pipelines.

## Unresolved Questions

- Whether the instructor requires literal IDs `DP1`, `DP2`, and `DP3` in
  addition to the descriptive DAG IDs documented by the rubric plan.
- UI screenshots remain part of Phase 9 evidence capture.
