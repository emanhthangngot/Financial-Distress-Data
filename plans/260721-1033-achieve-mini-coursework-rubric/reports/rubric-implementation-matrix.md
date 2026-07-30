# Rubric Implementation Matrix

---
plan: ../plan.md
status: pending
total_points: 100
criteria_count: 45
---

## Purpose

Execution-level mapping from every scored row in the checked-in rubric to implementation, automated validation, documentation, and final proof. A criterion is complete only when all four columns are satisfied.

## Completion States

- `missing`: no accepted implementation/proof.
- `implemented`: behavior exists but final proof is incomplete.
- `verified`: automated check passes from the final run.
- `accepted`: proof is linked in the final evidence index and mock-reviewed.

## Matrix

| ID | Criterion | Pts | Phase/task | Implementation | Automated validation | Final proof |
|---|---|---:|---|---|---|---|
| R01 | README, business domain, repo structure, TOC, docstrings, deployment diagram | 10 | P8-T1/T2/T3 | README rewrite, docstrings, deployable-unit diagram | Docs/link/docstring checks | README + numbered architecture image |
| R02 | Docker & Docker Compose usage | 1 | P8-T4 | Complete Compose profiles and documented build | `docker compose config`, service checks | Compose/service screenshot or output |
| R03 | Optimize Dockerfile | 1 | P8-T4 | Measured layer/dependency optimization | Image build and size comparison | Before/after size table and method |
| R04 | Simulate offline skew | 2 | P3-T2 | Configured dominant sector/exchange distribution | Distribution tolerance test | Metrics table/chart screenshot |
| R05 | Simulate high cardinality | 2 | P3-T3 | Configured unique identifiers | Exact/approx distinct check | Cardinality query/profile output |
| R06 | Simulate schema evolution | 2 | P3-T4 | Old/new partitions and nullable additions | Partition schema/null test | Evolution profile screenshot |
| R07 | Simulate another offline problem | 2 | P3-T5 | Configured duplicate injection | Duplicate-rate tolerance test | Before/after dedup report |
| R08 | Use offline generator configuration | 2 | P3-T1 | Typed YAML config + seed | Config validation/replay hash | Config excerpt and effective config |
| R09 | Store simulated offline data for Bronze ingestion | 2 | P3-T6 | Source-area MinIO/PostgreSQL write | Read-back hash/count test | MinIO/source table screenshot |
| R10 | Simulate streaming burst | 2 | P3-T7 | Time-bucket burst schedule | Peak/base throughput test | Burst-rate chart |
| R11 | Simulate late arrivals | 2 | P3-T8 | Event-time/ingest-time delay injection | Lateness-rate tolerance test | Late distribution output |
| R12 | Simulate another streaming problem | 2 | P3-T9 | Duplicate/out-of-order injection | Duplicate-rate tolerance test | Streaming duplicate report |
| R13 | Use streaming generator configuration | 2 | P3-T1 | Stream event/rate/timing config | Same-seed replay test | Effective stream config |
| R14 | Spark baseline | 2 | P4-T2 | Deliberately unoptimized correct job | Output digest and benchmark harness | Spark UI baseline screenshots |
| R15 | Spark handles skew with explanation | 2 | P4-T3 | Evidence-driven skew strategy | Equivalent output + metric improvement | UI/task/runtime comparison |
| R16 | Spark handles high cardinality | 2 | P4-T4 | Evidence-driven aggregation/partition plan | Equivalent output + metric comparison | Shuffle/memory/runtime proof |
| R17 | Spark handles schema evolution | 2 | P4-T5 | Explicit schema alignment/merge | Old/new partition integration test | Code and output proof |
| R18 | Spark handles other offline problem | 2 | P4-T6 | Latest-row dedup/invalid-row handling | Duplicate before/after test | Spark UI/query proof |
| R19 | Spark job integrated into pipelines | 2 | P4-T7/P6-T4 | DP2 invokes optimized Spark job | Airflow integration test | DP2 task/graph screenshot |
| R20 | Flink baseline | 2 | P5-T2 | Baseline Kafka-to-window job | Baseline output/metric test | Flink UI baseline screenshot |
| R21 | Flink handles burst | 2 | P5-T3 | Parallelism/checkpoint/backpressure tuning | Burst benchmark | Flink backpressure comparison |
| R22 | Flink handles late arrival | 2 | P5-T4 | Watermark, allowed lateness, late side output | On-time/late/too-late fixture | Watermark + late output proof |
| R23 | Flink handles other streaming problem | 2 | P5-T5 | Stateful event-ID dedup with TTL | Duplicate/restart test | Duplicate before/after proof |
| R24 | Flink window processing | 2 | P5-T6 | Event-time tumbling/sliding window | Window boundary test | Code capture + result screenshot |
| R25 | Lakehouse storage optimization | 2 | P4-T8 | Partitioning/compaction/target file size | Correctness + file/query metrics | Before/after file/query report |
| R26 | Data warehouse optimization | 2 | P4-T9 | Selective PostgreSQL indexes | `EXPLAIN ANALYZE` comparison | Query plan screenshots/table |
| R27 | DP1 ingest stage | 2 | P6-T2 | Source/Kafka to Bronze tasks | DP1 integration test | Airflow DP1 graph/grid |
| R28 | DP1 validate stage | 2 | P6-T3 | Bronze schema/count/problem validation | Intentional failure blocks publish | Airflow/log/query proof |
| R29 | DP2 ingest stage | 2 | P6-T4 | Bronze to Silver/Gold Spark tasks | DP2 integration test | Airflow DP2 graph/grid |
| R30 | DP2 validate stage | 2 | P6-T5 | Staged DQ and atomic promotion | Intentional failure preserves prior run | Airflow/log/query proof |
| R31 | DP3 ingest stage | 2 | P6-T6 | 4Q/30D PIT feature computation | Golden feature-window tests | Airflow DP3 graph/grid |
| R32 | DP3 validate stage | 2 | P6-T7 | Timestamp/leakage/uniqueness validation | Injected future feature fails | Airflow/log/query proof |
| R33 | DP1 lineage | 2 | P7-T3 | DataHub DP1 source/Bronze lineage | DataHub API graph assertion | DataHub lineage screenshot |
| R34 | DP1 validation and contract | 2 | P7-T4 | Bronze schema contract/assertion | DataHub API assertion status | DataHub contract/assertion tabs |
| R35 | DP2 lineage | 2 | P7-T5 | Bronze/Silver/Gold lineage | DataHub API graph assertion | DataHub lineage screenshot |
| R36 | DP2 validation and contract | 2 | P7-T6 | Silver/Gold contracts/assertions | DataHub API assertion status | DataHub contract/assertion tabs |
| R37 | DP3 lineage | 2 | P7-T7 | Gold facts/features lineage | DataHub API graph assertion | DataHub lineage screenshot |
| R38 | DP3 validation and contract | 2 | P7-T8 | Feature timestamp/leakage contract/assertion | DataHub API assertion status | DataHub contract/assertion tabs |
| R39 | Visualize tables on all zones | 2 | P8-T5 | Reproducible DuckDB schema database | Schema build and table-list test | DBeaver all-zone ERD screenshot |
| R40 | SCD Type 2 dimension | 1 | P2-T4/P8-T6 | Historical version state | Two-run SCD2 integration test | DBeaver SCD2 query screenshot |
| R41 | Feature tables have event timestamp and created | 1 | P6-T6/P8-T7 | Literal approved timestamp columns | Schema contract test | DBeaver feature schema screenshot |
| R42 | Dim/fact relationships | 2 | P8-T8 | Declared keys and reproducible ERD relationships | RI tests/schema audit | DBeaver relationship screenshot |
| R43 | Naming convention | 2 | P8-T8 | Bronze/Silver/Gold naming registry | Naming lint | Table list screenshot |
| R44 | Novel idea 1 | 5 | P8-T9 | Cryptographic run manifest/evidence integrity | Tamper/mixed-run negative tests | Idea doc + proof it worked |
| R45 | Novel idea 2 | 5 | P8-T10 | PIT leakage prevention and audit | Injected leakage negative test | Idea doc + proof it worked |

## Point Reconciliation

| Category | Criteria | Points |
|---|---|---:|
| README/diagram | R01 | 10 |
| Engineering fundamentals | R02-R03 | 2 |
| Generator | R04-R13 | 20 |
| Spark | R14-R19 | 12 |
| Flink | R20-R24 | 10 |
| Storage | R25-R26 | 4 |
| Airflow orchestration | R27-R32 | 12 |
| Governance | R33-R38 | 12 |
| Schema documentation | R39-R43 | 8 |
| Novel ideas | R44-R45 | 10 |
| **Total** | **R01-R45** | **100** |

## Final Review Rules

1. A screenshot without explanatory document context is incomplete.
2. A test without runtime proof does not satisfy a UI-proof criterion.
3. Proof must include the final run ID or be linked through the hashed manifest.
4. Baseline/optimized claims require equal logical output and recorded hardware/config.
5. DataHub screenshots must show the named DP and related datasets, not only service health.
6. Novel ideas require a negative/control case plus successful behavior.

## Unresolved Questions

- Instructor confirmation of proposed novel ideas.
- Literal accepted name for the feature creation timestamp.
- Whether literal Flink UI screenshots are mandatory when equivalent direct
  Flink REST job/checkpoint exports are included.
