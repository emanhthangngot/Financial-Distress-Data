---
phase: 5
title: "Phase 5: CDC, streaming and feature stores"
status: pending
priority: P1
effort: "10-14 days"
dependencies: ["phase-04-data-plane.md"]
owns: ["src/cdc/", "src/streaming/", "src/ml/feast/", "feature_repo/", "platform/streaming/", "platform/features/"]
---

# Phase 5: CDC, streaming and feature stores

## Overview

Deploy Kafka, Debezium, Flink and Feast; bind the CDC and streaming contracts to real runtimes;
implement the Flink realtime feature job; deploy the two stream-feature jobs the rubric names
(offline store and online store); define per-table TTL **with rationale**; prove the point-in-time
leakage guard against the live Postgres offline store using the P4 restatement fixture.
Runs in parallel with P6 — no shared files. **Resident cost: 5-7 vCPU windowed.**

ADR-005 (Postgres offline) and ADR-013 (Debezium → Kafka → Flink) must be **accepted** before this
phase opens (P3 gate).

## Requirements

- Functional:
  - Debezium connector `RUNNING` against source Postgres; Kafka topic receives initial-snapshot
    records matching the source row count.
  - Flink realtime job writes online features to Redis within the configured watermark.
  - Feast materializes from the Postgres offline store into Redis; every requested entity key
    returns non-null.
  - **Two separate deployed jobs**: stream feature → OFFLINE store, and stream feature → ONLINE
    store (ML 19-20, LLM 38-39).
  - **TTL defined per feature table with a written rationale** (ML 21).
  - The leakage guard raises `LeakageError` on the restatement fixture when the knowledge-time filter
    is absent, and passes with it.
- Non-functional: streaming stack tears down cleanly — the replication slot is dropped on shutdown;
  Feast entity timestamps are knowledge-time, matching the P2 contract.

## Architecture

```
source Postgres (WAL, wal_level=logical)
        │
        ▼
    Debezium (Kafka Connect)
        │
        ▼
      Kafka  ── topics: financial.price_events / news_events / alert_events
        │
        ├──► Flink realtime feature job ──► Redis          (ONLINE store)
        │
        └──► stream-feature-offline job ──► Postgres       (OFFLINE store)

    Feast registry (ml.feast_registry_revision)
        │  materialize (incremental, Airflow-driven)
        ▼
    Postgres OFFLINE  ──►  Redis ONLINE
        │
        ▼
    leakage_guard.py — compares feature.known_from_ts to fact_distress_label.decision_ts
```

### TTL policy (ML 21 — the rationale is the graded part)

| Feature table | TTL | Rationale |
|---|---|---|
| `feat_company_financial_4q` | 400 days | Quarterly source; a 4-quarter window plus one quarter of publication lag. Shorter would expire a feature before the next filing replaces it. |
| `feat_company_market_30d` | 45 days | Daily source over a 30-day window plus a 15-day buffer for market holidays and late arrival. |
| `feat_company_news_30d` | 45 days | Same window as market; news arrives irregularly, so the buffer absorbs quiet periods. |
| `feat_company_unified` | 400 days | Bounded by its longest input (`financial_4q`); a shorter TTL would silently drop the financial leg of the join. |

Each TTL is written into `feature_repo/structured/` and restated in
`docs/architecture/feature-contracts.md` with the reasoning above — the rubric asks for the
justification, not the number.

### Feast temporal contract — a design decision, not a fallback (schema audit F14)

Verified Feast behaviour: `event_timestamp` is the **inclusive upper bound** of the point-in-time
join, and `created_timestamp_column` is a tie-breaker where Feast selects the row with the
**highest** `created_timestamp` for a given `event_timestamp`. Feast's documented position on
restatements is that its "last known good" logic prioritises the most recent information, and that
seeing the world as it was known at the time requires explicit version management or custom
filtering.

So Feast's default is the adversary here: mapping the knowledge axis onto `created_timestamp` makes
Feast always return the newest vintage — exactly the leakage this project exists to prevent.

```
feat_*  event_timestamp   := known_from_ts     ← knowledge time IS Feast's join axis
        created_timestamp := ingest wall clock ← breaks ties between retries of one ingest only
        report_period     := feature attribute, NOT a time axis
```

Fixed in ADR-017 and enforced by the P2 ERD CHECK `event_timestamp = known_from_ts`. This is no
longer a §Risk response — the risk entry below now only covers the case where the materialization
writes the wrong column.

## Related Code Files

- Restore from archive: `platform/streaming/kafka/`, `platform/streaming/flink/`,
  `platform/streaming/debezium/`, `platform/features/feast/`
- Modify: `src/cdc/config.py`, `src/cdc/flink_cdc_job.py`, `src/cdc/reconcile.py` — bind to the real
  Debezium connector
- Modify: `src/streaming/flink_contract.py`, `src/streaming/flink/`, `kafka_producer.py`,
  `kafka_to_bronze_consumer.py`
- Modify: `src/ml/feast/` — Postgres offline store per the ADR-005 amendment; knowledge-time entity
  timestamps
- Modify: `feature_repo/structured/feature_store.cluster.yaml` — live cluster endpoints
- Modify: `infra/stream-feature-offline/`, `infra/stream-feature-online/` — the two rubric-named jobs
- Modify: `src/ml/leakage_guard.py` call sites for the live offline store
- Create: `docs/architecture/feature-contracts.md` (TTL table + rationale)
- Modify: `pyproject.toml` — add `confluent-kafka`, `apache-flink`, `feast`
- Modify: `dags/feature_materialize.py` — incremental materialize offline → online (ML 18)

## Implementation Steps

1. **Restore `platform-streaming`** (2-3 d) — Kafka, Kafka Connect + Debezium, Flink Operator.
2. **Register the Debezium connector** (1 d) — against source Postgres; verify Kafka Connect
   reports `RUNNING` and the initial-snapshot record count matches the source table count.
3. **Flink realtime feature job** (2-3 d) — bind `src/cdc/flink_cdc_job.py` to the live runtime;
   write online features to Redis inside the watermark; observable through `feature-api`.
4. **Restore `platform-features`** (1 d) — Feast with the Postgres offline store and the existing
   Redis online store; record the registry revision in `ml.feast_registry_revision`.
5. **Repoint the feature repo** (0.5 d) — `feature_store.cluster.yaml` to live endpoints.
6. **Deploy the two stream-feature jobs** (1 d) — one pushing to the OFFLINE store, one to the
   ONLINE store, as separately deployed workloads with their own manifests. The rubric scores them
   as two rows; a single job doing both does not satisfy it.
7. **Define and document TTL** (0.5 d) — apply the table above in `feature_repo/`; write
   `docs/architecture/feature-contracts.md`.
8. **Incremental materialize DAG** (1 d) — Airflow DAG that materializes only new data from offline
   to online; verify a second run moves zero rows when nothing changed.
9. **Leakage guard against the live store** (1 d) — run the P4 restatement fixture through the live
   Postgres offline store; confirm `LeakageError` without the knowledge-time filter and a pass with it.
10. **Teardown test** (1 d) — delete `platform-streaming`; verify `pg_replication_slots` returns
    zero rows for the connector slot.

## Success Criteria

- [ ] AC-P5-1: Debezium → registered against source Postgres → Kafka Connect reports `RUNNING`; the
      topic receives initial-snapshot records matching the source row count
- [ ] AC-P5-2: Flink realtime job → consumes a CDC record → writes the online feature to Redis
      within the configured watermark, observable through `feature-api`
- [ ] AC-P5-3: Feast → materializes from the Postgres offline store → Redis holds non-null feature
      values for every requested entity key
- [ ] AC-P5-4: Platform operator → lists workloads → **two distinct deployed jobs** exist, one
      pushing stream features to the OFFLINE store and one to the ONLINE store
- [ ] AC-P5-5: Airflow → runs the incremental materialize DAG twice with no new data → the second
      run moves zero rows
- [ ] AC-P5-6: Reader → opens `docs/architecture/feature-contracts.md` → finds a TTL for every
      `feat_company_*` table **and the reason it was chosen**; the values match `feature_repo/`
- [ ] AC-P5-7: `src/ml/leakage_guard.py` → validates a point-in-time join over the live offline
      store using the P4 restatement fixture → **raises `LeakageError`** without the knowledge-time
      filter; passes with it
- [ ] AC-P5-8: Platform operator → tears down `platform-streaming` → `pg_replication_slots` returns
      zero rows for the connector slot

### Mini-track streaming and DP3 rows (added 2026-09-02)

P3 §`owning_phase` part 2 assigns these to P5. They are **13 + 12 = 25 points** that the
2026-09-01 revision left with no owner and no AC, and that `plan.md` §Schedule Reality wrongly
priced at **0** when it listed "Debezium + Flink CDC" as a zero-cost cut. Baseline numbers come from
`docs/evidence/flink/` at tag `evidence-baseline-pre-rebuild` (P3 step 0).

- [ ] AC-P5-9 **(mini 20)**: Flink → runs the realtime feature job **without** optimizations →
      baseline throughput, end-to-end latency, checkpoint duration and backpressure ratio are
      captured under a fixed input rate
- [ ] AC-P5-10 **(mini 21)**: Flink → receives a generated **burst** at the configured multiple of
      steady rate → the optimized job holds latency within its SLO; the artifact pairs baseline and
      optimized numbers **and states which technique absorbed the burst and why** (parallelism,
      buffer timeout, credit-based flow control, or rate limiting)
- [ ] AC-P5-11 **(mini 22)**: Flink → receives **late-arriving** events beyond the watermark →
      the optimized job accounts for them per the configured allowed-lateness / side-output policy
      with a written explanation; late-event count and correction volume are recorded
- [ ] AC-P5-12 **(mini 23)**: Flink → receives the third streaming problem (stream duplicates) →
      the optimized job deduplicates with a stated technique and explanation; duplicate rate before
      and after is recorded
- [ ] AC-P5-13 **(mini 24)**: Flink → runs **window processing** → a named window type (tumbling or
      sliding) with its size, watermark strategy and allowed lateness is configured, and the windowed
      aggregate is observable through `feature-api`
- [ ] AC-P5-14 **(mini 31-32, DP3)**: Airflow → runs DP3 (offline feature table) → the DAG has a
      distinct **ingest** task and a distinct **validate** task; the validate task fails the run on a
      seeded feature-contract violation
- [ ] AC-P5-15 **(mini 37-38, DP3 governance)**: DataHub → shows DP3 → it is linked to its upstream
      Gold tables and its downstream feature tables with lineage edges, **and** carries its feature
      contract plus a validation result; the knowledge-time axis appears in the graph
- [ ] AC-P5-16 **(F14)**: Engineer → reads any materialized `feat_*` row → `event_timestamp` equals
      `known_from_ts`; a restated vintage does **not** overwrite the earlier vintage's feature row

## Risk Assessment

**Risk:** Debezium cannot reach the Postgres WAL. Signal: connector state `FAILED` with a
replication error. Mitigation: verify `wal_level = logical` was set at P4 initial deploy; check the
NetworkPolicy allows Kafka Connect → Postgres. Response: add an explicit egress rule for the Kafka
Connect pod.

**Risk:** Flink lag exceeds the watermark under load. Signal: growing consumer lag on the CDC topic.
Mitigation: benchmark the job at 50k events/s before connecting it to the live topic. Response:
raise task-manager parallelism.

**Risk:** Feast entity timestamps disagree with the P2 knowledge-time contract, so the leakage guard
sees the wrong axis. Signal: AC-P5-7 passes when it should raise. Mitigation: run the guard against a
Postgres offline-store fixture before connecting the live store. Response: repoint the Feast
materialization to write `known_from_ts` into `event_timestamp`, per §Feast temporal contract — the
mapping itself is fixed by ADR-017 and is not the thing being decided here.

**Risk:** the two stream-feature jobs are collapsed into one for convenience. Signal: one Deployment
handles both stores. Mitigation: AC-P5-4 counts workloads, not code paths. Response: split them;
the rubric scores two rows and CI/CD is graded per job (ML 35-36, LLM 38-39).

**Risk:** TTL values are written but the rationale is not. Signal: `feature_repo/` has TTLs and the
document does not explain them. Mitigation: AC-P5-6 asserts both. Response: the rationale is the
scored artifact — write it.

## Rubric Citations (phase-03 R-12 closure, appended 2026-09-05)

Every rubric row this phase owns per `docs/rubric-matrix-unified.csv`'s `owning_phase` column, cited so `scripts/verify_rubric_coverage.py` can resolve ownership to an assertion (R-12). Each line names the row's real `rubric_id`, its stated requirement, and its proof artifact/deliverable — the row's own matrix columns, not invented text. Rows whose capability is not yet implemented are forward specs, matching this file's other `AC-P5-*` entries.

- AC-P5-RUBRIC-1: `ML-feature-store-define-ttl-cho-t-ng-b-ng-featu` — ml_engineer -> delivers "Define TTL cho từng bảng feature, giải thích tại sao chọn TTL như thế" -> + Capture màn hình thể hiện các data pipeline và thứ tự các stage trên Airflow; + Capture màn hình thể hiện 2 job đang chạy, và thể hiện out... (evidence: `docs/platform/evidence/ml/ML-feature-store-define-ttl-cho-t-ng-b-ng-featu.md`)
- AC-P5-RUBRIC-2: `mini-20-processing-jobs-flink-job-to-handle-streaming-data` — data_engineer -> delivers "Baseline (without optimization)" -> Document giải thích từng step optimize từ baseline như thế nào, dùng Flink UI như thế nào (với screenshots để thấy rõ vấn đề) (evidence: `docs/submission/rubric-(mini-coursework)/processing_jobs.md`)
- AC-P5-RUBRIC-3: `mini-21-processing-jobs-flink-job-to-handle-streaming-data` — data_engineer -> delivers "Handle burst with explanation" -> Handle burst with explanation (evidence: `docs/submission/rubric-(mini-coursework)/processing_jobs.md`)
- AC-P5-RUBRIC-4: `mini-22-processing-jobs-flink-job-to-handle-streaming-data` — data_engineer -> delivers "Handle late arrival with explanation" -> Handle late arrival with explanation (evidence: `docs/submission/rubric-(mini-coursework)/processing_jobs.md`)
- AC-P5-RUBRIC-5: `mini-23-processing-jobs-flink-job-to-handle-streaming-data` — data_engineer -> delivers "Handle other streaming problem with explanation" -> Handle other streaming problem with explanation (evidence: `docs/submission/rubric-(mini-coursework)/processing_jobs.md`)
- AC-P5-RUBRIC-6: `mini-24-processing-jobs-flink-job-to-handle-streaming-data` — data_engineer -> delivers "Window processing" -> Capture đoạn code thể hiện khả năng xử lý Window trong Flink (evidence: `docs/submission/rubric-(mini-coursework)/processing_jobs.md`)
- AC-P5-RUBRIC-7: `mini-31-data-pipeline-orchestration-pipeline-to-compute-of` — data_engineer -> delivers "Ingest stage" -> Capture màn hình pipeline trên Airflow UI thể hiện các stage và thứ tự trong pipeline (evidence: `docs/submission/rubric-(mini-coursework)/data_pipeline_orchestration.md`)
- AC-P5-RUBRIC-8: `mini-32-data-pipeline-orchestration-pipeline-to-compute-of` — data_engineer -> delivers "Validate stage" -> Validate stage (evidence: `docs/submission/rubric-(mini-coursework)/data_pipeline_orchestration.md`)
- AC-P5-RUBRIC-9: `mini-37-data-governance-dp3-linked-with-related-tables-lin` — data_engineer -> delivers "Lineage between the pipeline and tables" -> Capture màn hình pipeline trên DataHub UI thể hiện lineage, validation và data contract (evidence: `docs/submission/rubric-(mini-coursework)/data_governance.md`)
- AC-P5-RUBRIC-10: `mini-38-data-governance-dp3-linked-with-related-tables-dat` — data_engineer -> delivers "Data validation and data contract" -> Data validation and data contract (evidence: `docs/submission/rubric-(mini-coursework)/data_governance.md`)
