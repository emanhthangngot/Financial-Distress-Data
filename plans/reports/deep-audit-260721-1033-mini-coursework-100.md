# Deep Audit For Mini-Coursework 100/100

---
date: 2026-07-21
status: complete
scope: full repository, 100-point rubric, edge cases, proof integrity
skills: ak-scout, ak-code-review, ak-plan
---

## Executive Decision

The repository has a useful Stage 1 prototype, but it needs substantial new implementation, not only documentation cleanup, to target 100/100.

The previous conservative score of 27/100 remains a reasonable verified baseline. This deeper pass found additional correctness and proof-integrity defects that must be fixed before existing points are considered stable.

Key measurements:

- 89/89 existing tests pass.
- Ruff passes.
- Branch-aware coverage is 58%, not the documented 100%.
- `src/jobs/stage1_spark_lakehouse_job.py` coverage is 11%.
- Eight numbered DAGs have 0% coverage and are smoke stubs rather than rubric pipelines.
- No Flink or DataHub implementation exists.
- No running Docker services were present during this audit.

## New Critical Findings

### C1. SCD2 Cannot Work Through The Actual Pipeline

Silver deduplicates `companies` by `ticker`, retaining only the newest snapshot. Gold then receives one row per ticker, so `build_dim_company_spark()` cannot reconstruct SCD2 history.

The SCD2 unit test bypasses Silver and calls the Python Gold builder directly with two versions. It therefore proves the isolated builder, not Bronze-to-Silver-to-Gold behavior.

Required fix:

- Preserve company snapshots using a versioned business key or build SCD2 before snapshot collapse.
- Persist historical dimension state across runs.
- Test two pipeline runs where a tracked field changes.
- Prove `valid_from_ts`, `valid_to_ts`, and `is_current` in runtime output.

### C2. Spark Publish Is Destructive And Non-Atomic

The Spark job deletes all Silver/Gold prefixes before creating the Spark session. Any later failure can remove the last known-good output.

Required fix:

- Write to run-scoped staging prefixes.
- Validate the complete staged graph.
- Promote only after validation.
- Keep the previous version until promotion succeeds.

### C3. Broad Exceptions Hide Stream Failures

Three broad `except Exception` blocks convert price/news/alert read failures into batch-only or empty results. Corrupt Parquet, credentials, schema errors, and missing paths become indistinguishable.

Required fix:

- Treat only an explicitly optional missing path as empty.
- Fail on corrupt data, credentials, schema, and transport errors.
- Add minimum-row/input-presence DQ policies.

### C4. Configuration Files Are Mostly Dead

Runtime does not consume:

- `configs/collector_config.yaml`
- `configs/source_mapping.yaml`
- `configs/dq_rules.yaml`
- `configs/sector_exclusion.yaml`

`collector_config.yaml` says `source_mode: online`, but collectors always default to `VnstockFixtureAdapter`. `vnstock_adapter.py` only re-exports the fixture adapter.

Required fix:

- Load and validate configuration once.
- Make config select generator/fixture/live adapters explicitly.
- Make DQ runner execute configured rules.
- Make sector exclusion read the configured list.
- Include effective config and seed in every evidence manifest.

### C5. Feature Names Do Not Match Behavior

- `feat_company_market_30d` emits one row per market fact; it does not aggregate 30 days.
- `feat_company_news_30d` emits one row per news fact; it does not aggregate 30 days.
- `feat_company_financial_4q` copies one quarter; it does not aggregate four quarters.
- Feature outputs do not provide the rubric-required `created` column.

Required fix:

- Implement actual point-in-time window aggregations.
- Define feature grain and primary key.
- Add `event_timestamp` and `created_timestamp` or the exact instructor-approved `created` name.
- Validate window boundaries and late-arriving corrections.

### C6. Evidence Can Pass With Mixed Or Stale Runs

The evidence audit checks positive Kafka offsets, existing MinIO prefixes, PostgreSQL text fragments, and DuckDB metrics. It does not require those artifacts to share one run ID.

Examples:

- Any historical positive Kafka offset satisfies the Kafka check.
- MinIO object listing covers the entire bucket and includes stale runs.
- PostgreSQL summaries aggregate all historical rows.
- Artifacts have no shared manifest hash or run correlation.

Required fix:

- Generate a run manifest with run ID, Git SHA, config hash, start/end time, and artifact hashes.
- Filter Kafka, MinIO, PostgreSQL, Airflow, and DuckDB proof by the same run ID.
- Make the audit reject mixed-run packages.

## Reproduced Logic Defects

The following were reproduced with direct executable probes.

| Defect | Observed result | Expected result |
|---|---|---|
| Python alert dedup | Kept `old` row | Keep latest `created_ts` |
| Python news dedup | Kept sentiment `-1` | Keep later sentiment `1` |
| Financial sector detection | `Financials` returned false | Exclude instructor-approved financial sector values |
| Invalid numeric Z-score input | Raised `TypeError` | Reject/quarantine with reason |
| Timezone-aware Silver dedup | Kept chronologically older row | Parse timestamps then compare instants |
| Empty required value | Accepted empty ticker | Reject blank required values |
| Future freshness timestamp | Passed with lag zero | Detect clock skew/future event |
| Null referential integrity | Null fact key passed when dimension set contained null | Null key must fail independently |
| Malformed PIT timestamps | Malformed reference joined malformed feature | Quarantine or fail invalid timestamp |

Additional code inspection findings:

- Spark news fact builder has no event-ID deduplication.
- Alert event IDs use UUIDs, making replay deduplication unreliable.
- Kafka producer does not key events by ticker, so per-ticker partition ordering is not guaranteed.
- Kafka consumer uses a new group, `earliest`, and never commits; scan cost grows with topic history.
- Real micro-batch calls never advance `elapsed_seconds`, so interval flushing is not driven by wall time.
- Spark unified PIT join compares unnormalized event timestamp columns and ignores `report_release_date` in its join predicate.
- Spark and Python OBT differ for negative equity handling.
- Financial statements do not contain sector/industry, so actual label runs cannot apply sector exclusion without a dimension join.
- Spark SCD2 null comparison can create extra versions when a tracked field remains null.
- Rejected Spark Silver DataFrames are assigned but never persisted.

## Schema And DQ Defects

### Registry Drift

- SQL seeds `stream_events`; Python `DEFAULT_CONTRACTS` does not define it.
- Contracts list field names but no data types, formats, ranges, enums, or compatibility policy.
- SQL uses `ON CONFLICT DO NOTHING`; changing schema JSON under version `v1` leaves an existing database stale.
- No automated comparison verifies every SQL contract against Python.

### DQ Configuration Drift

Configured but not executed:

- schema match
- date-key referential integrity
- total-assets nonnegative
- sentiment range
- volume-drop check
- configured retention rule

Runtime hardcodes a subset in Python. The freshness reference is fixed to 2025 instead of Airflow logical time or current monitoring time.

### DQ Semantics

- Missing dataset inputs can become empty facts without guaranteed failure.
- Future event timestamps pass freshness.
- Null foreign keys can pass under a malformed dimension-key set.
- Invalid timestamps are often converted into warnings or minimum dates instead of quarantine.
- DQ results are persisted one connection/transaction at a time, with no batch-level atomicity or manifest link.

## Airflow Findings

### Misleading DAG Names

- `04_stream_market_events_to_kafka` does not connect to Kafka; it runs an in-memory micro-batch.
- `06_pyspark_silver_to_gold` does not run PySpark; it calls Python builders.
- `08_minio_duckdb_register_tables` returns a SQL string; it does not execute registration.
- DAGs 01-08 are independent one-task smoke DAGs, not DP1/DP2/DP3.

### Missing Orchestration Contracts

- No DP1 raw-to-Bronze ingest plus validation DAG.
- No DP2 Bronze-to-Silver/Gold ingest plus validation DAG.
- No DP3 offline-feature ingest plus validation DAG.
- No dataset scheduling or explicit cross-DAG dependencies.
- No retry/backoff policy in `DEFAULT_ARGS`.
- No failure callback or run-manifest finalizer.
- No Airflow UI screenshots for required pipelines.
- Connections are read as generic environment variables rather than rubric-visible Airflow Connections.

Airflow officially supports `AIRFLOW_CONN_*` connection environment variables and `AIRFLOW_VAR_*` variables. Using these preserves environment-based deployment while satisfying the Airflow abstraction, though UI visibility must be considered for grading proof.

## Docker And Reproducibility Findings

- PostgreSQL and MinIO lack persistent named volumes.
- Services lack health checks.
- Scheduler depends on webserver rather than shared initialization/readiness dependencies.
- Runtime script hardcodes generated container names instead of `docker compose exec` service names.
- Service checks hardcode PostgreSQL user/database and MinIO bucket.
- DuckDB SQL hardcodes MinIO credentials; only endpoint substitution is implemented.
- Spark downloads S3A packages at runtime, conflicting with an offline/reproducible local claim.
- No lockfile or hashes pin Python dependency resolution.
- No Docker image before/after size evidence.
- Dockerfile is not multi-stage and has no measured optimization report.
- Default credentials are acceptable only for isolated coursework use and must be labelled as such.

## Documentation And Proof Findings

- README contains no Markdown links to detailed docs, despite the rubric explicitly requiring them.
- README places the table of contents after major content and uses multiple H1 headings.
- 54/54 inspected runtime modules lack module docstrings.
- 233/235 functions/classes lack docstrings.
- `docs/mini_coursework.md` claims 100% coverage; measured branch-aware coverage is 58%.
- `docs/mini_coursework.md` calls the architecture online/production while active ingestion is fixture-backed.
- `docs/mini_coursework.md` is 1,020 lines and `docs/coursework.md` is 2,505 lines, exceeding the configured 800-line documentation limit.
- `.gitignore` ignores PNG/JPG files under `docs/evidence/`, which conflicts with screenshot submission.
- Only two images are tracked: architecture and ERD. Required Spark UI, Flink UI, Airflow DP1/DP2/DP3, DataHub, MinIO, generator metrics, and optimization screenshots are absent.
- ERD provenance is not reproducible: no checked-in script creates `warehouse.db` or its `schema_evidence` tables.
- ERD names and columns do not fully match runtime DuckDB view definitions.
- Architecture diagram mixes logical zones, Python jobs, users, and deployable services; flows are not numbered and collectors are drawn sequentially.

## Coverage Findings

Measured with:

```text
pytest --cov=src --cov=dags --cov=scripts --cov-branch
```

Result: 58% total coverage.

Lowest high-risk areas:

| Area | Coverage |
|---|---:|
| Spark lakehouse runtime job | 11% |
| Spark Silver transform | 7% |
| Kafka-to-Bronze runtime job | 23% |
| Stage 1 DQ runtime job | 20% |
| MinIO writer | 13% |
| Real E2E DAG | 41% |
| Real E2E runner | 43% |
| Numbered DAGs 01-08 | 0% |

100/100 does not require literal 100% code coverage unless the instructor says so. It does require removing the false claim and covering rubric-critical behavior.

## Full Rubric Gap Map

| Rubric block | Points | Current stable proof | Required completion proof |
|---|---:|---|---|
| README/diagram/docstrings | 10 | Partial | Correct deployment diagram, numbered flows, doc links, docstrings |
| Docker/optimization | 2 | Partial | Compose plus measured image optimization before/after |
| Offline generator | 12 | Mostly absent | Skew, cardinality, schema evolution, duplicate, config, stored source data |
| Streaming generator | 8 | Mostly absent | Burst, late/out-of-order, duplicate, config and metrics |
| Spark processing | 12 | Partial | Baseline, four problem handlers, Spark UI, measurements, Airflow integration |
| Flink processing | 10 | Absent | Baseline, burst/late/duplicate handlers, event-time window code/UI |
| Storage optimization | 4 | Partial | Compaction/partition experiment and warehouse index experiment |
| DP1/DP2/DP3 | 12 | Mostly absent | Three DAGs, ingest/validate stages, Airflow UI proof |
| DataHub governance | 12 | Absent | DP1/DP2/DP3 lineage, validation, contract proof in DataHub UI |
| Schema docs | 8 | Partial | Reproducible all-zone ERD, real SCD2, exact feature timestamps, relationships/naming |
| Novel ideas | 10 | Absent as rubric deliverables | Two explicit documents, implementation, proof and evaluation |

## Architecture Required For 100/100

```text
Config-driven deterministic problem generator
  -> source MinIO/PostgreSQL area
  -> DP1 Airflow ingest + validate
  -> Bronze MinIO
  -> DP2 Airflow Spark transform + validate
  -> Silver/Gold MinIO + PostgreSQL metadata
  -> DP3 Airflow PIT feature build + validate
  -> Gold feat_* tables

Streaming generator
  -> Kafka
  -> Flink event-time/watermark/window/dedup
  -> Bronze/Gold streaming outputs + late side output

DP1/DP2/DP3 + datasets + DQ/contracts
  -> OpenLineage/DataHub
  -> DataHub UI evidence

All runs
  -> shared run manifest
  -> reproducible screenshots and machine-readable rubric audit
```

Apache Flink's official documentation confirms the relevant mechanism: event-time watermarks, allowed lateness, and side outputs for late data. DataHub's official documentation provides Docker quickstart plus dataset lineage, assertions, and data contracts suitable for the governance rubric.

## Completion Strategy

Do not start with screenshots. First make runtime behavior correct and deterministic, then build rubric-shaped pipelines, then capture proof from one correlated run.

Execution plan:

1. Lock the rubric matrix and evidence naming.
2. Correct existing runtime contracts and add regression tests.
3. Build the configurable problem generator.
4. Implement Spark baseline/optimized paths and storage experiments.
5. Implement Flink event-time stream processing.
6. Build DP1/DP2/DP3 in Airflow.
7. Emit lineage/contracts/assertions to DataHub.
8. Finish Docker, docs, diagram, schema evidence, and two novel ideas.
9. Run a clean-room submission rehearsal and mock-score every point.

Detailed phase files are stored under:

```text
plans/260721-1033-achieve-mini-coursework-rubric/
```

## External References

- Apache Flink windows: https://nightlies.apache.org/flink/flink-docs-stable/docs/dev/datastream/operators/windows/
- Apache Flink event-time debugging: https://nightlies.apache.org/flink/flink-docs-stable/docs/ops/debugging/debugging_event_time/
- DataHub documentation: https://docs.datahub.com/
- Airflow 2.10 variables: https://airflow.apache.org/docs/apache-airflow/2.10.5/howto/variable.html
- Airflow connections: https://airflow.apache.org/docs/apache-airflow/stable/howto/connection.html

## Unresolved Questions

- Whether Java Flink or PyFlink is preferred by the instructor. Java is usually the lower-risk choice for full DataStream API coverage; PyFlink reduces language count.
- Whether DataHub is strictly mandatory or an instructor-approved OpenLineage UI substitute is allowed. The checked-in rubric explicitly names DataHub, so the plan assumes DataHub.
- Whether `created` must be the literal feature column name or `created_timestamp` is accepted. The plan assumes literal rubric compliance unless clarified.
- Whether the two novel ideas may reuse PIT leakage prevention and automated evidence manifests, or must introduce tools not taught in class.
- Whether screenshots exist outside the repository and should be imported into the final evidence structure.
