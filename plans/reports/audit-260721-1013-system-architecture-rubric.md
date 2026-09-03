# System Architecture And Mini-Coursework Rubric Audit

---
date: 2026-07-21
scope: repository architecture, runtime coordination, quality gates, mini-coursework rubric
status: complete
method: ak-scout, static inspection, contract tests, committed evidence audit
---

## Summary

The repository is a coherent Stage 1 lakehouse prototype, but it is not a complete submission for the checked-in 100-point mini-coursework rubric.

- Code organization: generally sound for a Python data engineering repository.
- Stage 1 contracts: well covered by tests; 89 tests passed.
- Checked-in runtime evidence: internally consistent; evidence audit passed.
- Full rubric: major mandatory areas are absent, especially generator problem simulation, Flink, Spark optimization evidence, three separate Airflow pipelines, DataHub lineage, and novel-idea documentation.
- Conservative rubric estimate: **27/100 verified**. A generous reviewer may award roughly **30-35/100**, but the current repository does not support a defensible completion claim.

The strongest distinction is:

```text
Stage 1 E2E evidence passed != full mini-coursework rubric completed
```

## Evidence Reviewed

- Rubric: `docs/Coursework Tracking (Public) - rubic (mini-coursework).csv`
- Main docs: `README.md`, `docs/mini_coursework.md`, `docs/01_data_generator.md`, `docs/02_schema_design.md`, `docs/spec.md`
- Runtime code: `src/`, `dags/`, `scripts/`, `sql/`, `configs/`
- Platform: `docker-compose.yml`, `infra/airflow/Dockerfile`
- Tests: 15 files under `tests/`
- Evidence: `docs/evidence/`
- Images: architecture and ERD PNGs

## Verification Results

| Gate | Result | Notes |
|---|---|---|
| PyTest | Pass | 89/89 tests passed in 0.43s using a temporary environment |
| Ruff | Pass | No reported lint errors |
| Docker Compose config | Pass | Compose configuration parses successfully |
| Evidence audit | Pass | All committed Stage 1 audit checks passed; 436 MinIO objects reported |
| Black | Inconclusive | Process stalled in this environment; terminated rather than claiming pass |
| Live service E2E | Not rerun | No claim that Docker services were recreated and exercised during this audit |

The README command `.venv/bin/python scripts/run_stage1_quality_gates.py` did not work from the checkout because `.venv/` was absent. Dependencies were installed into `/tmp/financial-distress-audit-venv` for non-destructive verification.

## Architecture Map

### Implemented Runtime Flow

```text
VnstockFixtureAdapter
  -> batch collectors
  -> Airflow real E2E DAG
  -> batch Bronze Parquet in MinIO

fixture stream events
  -> Kafka producer
  -> Kafka broker
  -> micro-batch consumer
  -> streaming Bronze Parquet in MinIO

Bronze
  -> local PySpark Silver normalization/dedup
  -> local PySpark Gold facts/dimensions/features/labels
  -> DQRunner
  -> PostgreSQL operational metadata
  -> DuckDB httpfs validation
  -> evidence artifacts
```

### Module Boundaries

| Path | Responsibility | Assessment |
|---|---|---|
| `src/collectors/` | Source adapter boundary and fixture-backed collectors | Correct boundary; actual online source not implemented |
| `src/streaming/` | Event contracts, Kafka producer, micro-batching | Reasonable boundary; no Flink processing |
| `src/transforms/silver/` | Schema alignment and deduplication | Correct boundary; rejected rows not integrated with persistence |
| `src/transforms/gold/` | Dimensions, facts, OBT, Parquet helpers | Good separation |
| `src/transforms/features/` | Point-in-time feature logic | Good separation |
| `src/jobs/` | Runtime adapters joining storage, Spark, DQ, Kafka | Appropriate orchestration boundary; one file is oversized |
| `src/quality/` | DQ checks and execution | Clear separation; freshness contract is not runtime-safe |
| `src/metadata/` | Schema contracts and operational metadata | Clear separation |
| `src/catalog/` | DuckDB view/validation execution | Clear separation |
| `dags/` | Airflow definitions | Mixed: eight smoke DAGs plus two evidence DAGs, not rubric DP1/DP2/DP3 |
| `scripts/` | Reviewer/evidence commands | Appropriate placement |
| `configs/`, `sql/`, `tests/` | Configuration, DDL/views, verification | Appropriate placement |

## Directory Organization Assessment

### What Is Good

- Conventional top-level split between source, DAGs, tests, configs, SQL, docs, infrastructure, and scripts.
- Domain code is mostly separated from Airflow definitions.
- Gold builders are split by table instead of being placed in one generic transform file.
- Runtime adapters under `src/jobs/` keep most service calls out of the core transform modules.
- Tests are centralized and cover keys, transforms, labels, DQ, DAG contracts, evidence audit, and service-check behavior.
- SQL and YAML are not embedded broadly in Python.

### What Should Change

1. `src/jobs/stage1_spark_lakehouse_job.py` is about 700 lines and owns session setup, cleanup, Silver, all Gold builders, features, schema coercion, and writes. Split by real runtime responsibility only when implementing fixes: Silver materialization, Gold materialization, and atomic publish.
2. Eight numbered DAGs are mostly isolated smoke tasks. Their names imply deployable pipelines, but they do not coordinate into DP1, DP2, and DP3.
3. `docs/coursework.md` describes a much larger future architecture and paths that do not exist. It is easy for a reviewer to confuse planned work with as-built work.
4. Image assets are under `images/`, while docs and proof requirements expect evidence to be explained from `docs/`. This is acceptable technically, but each proof image needs a linked narrative document.
5. No top-level license or contribution guidance is present. These are not rubric blockers.

The current directory structure does not need a wholesale reorganization. The priority is to correct runtime boundaries and align DAG/document names with real behavior.

## Critical And High-Risk Findings

### 1. Destructive Publish Before Successful Build

`run_stage1_spark_lakehouse()` calls `_clear_output_prefixes(bucket)` before creating the Spark session or building replacement datasets.

Impact:

- Spark startup, dependency download, read, transform, or write failure can remove the last good Silver/Gold snapshot.
- The pipeline has no staging prefix, manifest swap, transaction, or rollback.
- `overwrite` is not an atomic multi-table publish.

Recommendation:

- Write to `staging/run_id=.../` prefixes.
- Validate row counts, schemas, keys, and DQ against staging.
- Promote or swap only after all required datasets pass.
- Preserve the previous successful run until promotion completes.

### 2. Broad Exception Handling Converts Failures Into Missing Data

The Spark job catches `Exception` when reading streaming price, news, and alert Parquet. Price falls back to batch-only data; news and alerts become empty DataFrames.

Impact:

- Authentication, corrupt Parquet, S3A, schema, and programming failures can look like a successful no-data run.
- DQ may not detect missing optional facts because no minimum-count check is defined for every stream dataset.

Recommendation:

- Catch only a verified “path not found” condition when optional input is intentional.
- Fail for corrupt data, schema mismatch, credentials, and connectivity errors.
- Add explicit input-availability policy and row-count checks.

### 3. Rejected Silver Rows Are Not Persisted

`bronze_to_silver_spark()` returns `(silver, failed)`. `run_stage1_spark_lakehouse()` assigns `failed_companies`, `failed_statements`, and `failed_prices`, but does not persist these DataFrames.

Impact:

- Documentation says failed records are persisted, but the actual Spark path drops them.
- Reviewer cannot trace rejected source rows from the live job.
- DQ failure-probe evidence is separate and does not prove transform rejection persistence.

Recommendation:

- Persist failed rows with dataset, reason, raw payload, run ID, and timestamp.
- Add an integration test verifying rejected Bronze input appears in `ops.failed_records` before the task completes.

### 4. Freshness Check Uses A Fixed Historical Reference

`build_actual_dq_checks()` sets `reference_timestamp` to `2025-03-01T00:00:00+00:00`.

Impact:

- The check can pass indefinitely even when a current production feed is stale.
- It proves fixture consistency, not runtime freshness.

Recommendation:

- Use Airflow logical time/data interval for replayable pipeline checks.
- Use current UTC only for real-time monitoring mode.
- Store both reference time and latest event time in evidence.

### 5. Docker Storage Is Ephemeral

PostgreSQL and MinIO do not define persistent named volumes. Container recreation can remove operational metadata and lakehouse objects.

Impact:

- Evidence is not durable across `docker compose down` followed by container recreation.
- The design is weaker than the “data storage” wording suggests.

Recommendation:

- Add named volumes for PostgreSQL and MinIO.
- Document reset and backup behavior.

## Medium Findings

### Airflow Configuration Does Not Match Rubric Contract

The rubric says reusable connections and variables should be in Airflow. The implementation injects DSNs, Kafka servers, MinIO endpoint, and credentials through container environment variables and reads them with `os.getenv()`.

Environment injection is valid engineering, but it does not meet the stated grading proof. Use Airflow Connections/Variables or document an accepted equivalent with screenshots.

### DAG Model Does Not Implement DP1, DP2, DP3

- `stage1_real_e2e_pipeline` is one serial seven-task evidence DAG.
- Numbered DAGs `01` through `08` are mostly single-task smoke DAGs.
- There is no independently reviewable DP1 raw-to-Bronze pipeline with validation.
- There is no independently reviewable DP2 Bronze-to-Silver/Gold pipeline with validation.
- There is no independently reviewable DP3 offline-feature pipeline with validation.
- There are no Airflow UI screenshots for those three pipelines.

### Deployment Diagram Is Not Rubric-Compliant

The image is useful as a conceptual overview, but:

- Company, financial statement, and market collectors are drawn sequentially even though they are separate collection concerns.
- Logical data zones and Python jobs are mixed with deployable services.
- Flows are mostly unnumbered.
- Several arrows lack a precise payload/operation label.
- Dotted lines are used heavily.
- The image claims online APIs/WebSocket architecture while the evidence run uses fixtures.

### Docstring Requirement Is Almost Entirely Unmet

AST inspection of `src/`, `dags/`, and `scripts/` found:

- 54 modules missing module docstrings.
- 233 of 235 functions/classes missing docstrings.

This is an explicit README/rubric requirement. Ruff does not enforce it because no docstring rules are configured.

### “100% Test Coverage” Is Unsupported

`docs/mini_coursework.md` claims 100% test coverage, but CI runs PyTest without coverage measurement. Passing 89 tests is not equivalent to 100% line, branch, or behavior coverage.

### Docker Optimization Proof Is Missing

The Dockerfile uses `--no-install-recommends`, cleans apt lists, and avoids pip cache, which is good. However:

- No before/after image sizes are documented.
- No optimization experiment is documented.
- No multi-stage build is used.

### SCD2 Spark Logic Has A Null-Comparison Edge Case

The Spark `changed` predicate treats a previous null tracked field as a change. Consecutive snapshots where a tracked field remains null may create unnecessary versions. Add null-safe equality (`eqNullSafe`) tests for repeated null values.

### Runtime Dependencies Are Split Across Install Paths

`requirements.txt` supports CI gates but omits Kafka, MinIO, PyArrow, Psycopg, and PySpark. README requires an additional editable install with runtime extras. This works if followed precisely, but a single locked reproducible setup is absent.

## Rubric Assessment

Scoring is conservative and requires code plus the proof requested in the rubric. Partial implementation without the requested screenshot/analysis receives limited credit.

| Rubric area | Max | Verified estimate | Assessment |
|---|---:|---:|---|
| README + deployment diagram + docstrings | 10 | 5 | README/TOC/structure exist; diagram and docstrings fail explicit requirements |
| Docker and Dockerfile optimization | 2 | 1 | Compose and Dockerfile exist; no measured optimization proof |
| Data generator: offline + streaming problems | 20 | 4 | Config and MinIO persistence exist; no real skew/cardinality/evolution/burst/late/duplicate simulation package or metrics |
| Spark processing jobs | 12 | 4 | Spark integrated and handles schema alignment/dedup; no baseline, Spark UI, skew/cardinality optimization experiment |
| Flink streaming processing | 10 | 0 | Flink code, UI evidence, watermark/window processing absent |
| Storage optimization | 4 | 2 | Some Parquet paths are partitioned and PostgreSQL primary keys create implicit indexes; no designed index benchmark, before/after analysis, or compaction proof |
| DP1/DP2/DP3 orchestration | 12 | 2 | One real E2E DAG exists; required three pipelines, validation stages, Airflow proof absent |
| Data governance and lineage | 12 | 3 | Contracts and DQ exist; DataHub/OpenLineage and DP-linked lineage proof absent |
| Schema documentation | 8 | 6 | ERD, SCD2, features, relationships, naming mostly present; DBeaver/all-zone proof and exact feature timestamp contract need confirmation |
| Two novel ideas | 10 | 0 | No two explicitly documented ideas with proof and rubric mapping |
| **Total** | **100** | **27** | **Not complete** |

### Generator Gap Details

The current fixture adapter generates two tickers and deterministic values. It does not provide:

- configurable skew percentage
- high-cardinality identifier population
- old/new schema partitions
- configured offline duplicate rate
- configured burst periods
- configured late/out-of-order event rate
- configured streaming duplicate rate
- summary metrics such as `approx_count_distinct`, duplicate before/after, burst rate, and late rate
- screenshots or benchmark outputs describing those characteristics

Deduplication support in Silver is useful, but it is not proof that the generator simulated the required problem.

### Processing Gap Details

The repository has Spark DataFrame transforms, but the rubric expects an experimental narrative:

```text
baseline -> observed Spark UI problem -> chosen optimization -> measured result -> Airflow integration
```

None of the baseline/optimized measurements or Spark UI screenshots are present. Flink is completely absent.

### Governance Gap Details

Schema registry, PostgreSQL metadata, DQ, and failed-record interfaces are good foundations. The rubric specifically asks for DP1/DP2/DP3 lineage, validation, and data contracts visible in DataHub UI. The as-built documentation explicitly states that no OpenLineage/DataHub/Marquez platform exists.

## Recommended Completion Order

### P0: Make Existing Runtime Trustworthy

1. Implement staging plus atomic promotion for Silver/Gold outputs.
2. Replace broad stream-read exceptions with typed failure handling.
3. Persist rejected Silver rows.
4. Make freshness reference time runtime-aware.
5. Add MinIO/PostgreSQL volumes.
6. Add tests for failed publish, corrupt stream input, failed-row persistence, and SCD2 null-safe comparison.

### P1: Build Rubric-Shaped Pipelines

1. DP1: generator/source storage -> Bronze -> Bronze validation.
2. DP2: Bronze -> Silver -> Gold -> DQ validation.
3. DP3: Gold facts -> offline feature tables -> PIT/leakage validation.
4. Put reusable service definitions into Airflow Connections/Variables where grading requires them.
5. Capture Airflow UI proof for each pipeline.

### P2: Implement Generator Requirements

1. Add one configuration-driven generator boundary.
2. Simulate skew, high cardinality, schema evolution, and duplicates offline.
3. Simulate burst, late/out-of-order, and duplicate events for streaming.
4. Persist generated source datasets for DP1 ingestion.
5. Produce a repeatable metrics report and screenshots.

### P3: Add Required Engines And Optimization Evidence

1. Create Spark baseline and optimized jobs against generator output.
2. Capture Spark UI and measured before/after results.
3. Add Flink job with event-time watermark, late-event handling, deduplication, and windows.
4. Capture Flink UI and measured before/after results.
5. Add lakehouse compaction/partition experiment and warehouse index experiment.

### P4: Governance And Submission Proof

1. Add DataHub/OpenLineage integration for DP1/DP2/DP3.
2. Publish lineage, validation, and contract screenshots.
3. Fix deployment diagram semantics and number the flows.
4. Add module/function/class docstrings or obtain an explicit rubric exemption.
5. Document two novel ideas separately with executable proof.
6. Replace unsupported “100% coverage” wording with measured coverage output.

## Completion Decision

The project is **complete enough as a tested Stage 1 fixture-backed lakehouse prototype**, with committed evidence for Kafka, MinIO, Spark, PostgreSQL, DuckDB, DQ, and Airflow.

The project is **not complete against the checked-in mini-coursework rubric**. Missing mandatory domains represent more than half of the available points, and several existing features lack the exact proof format required by the rubric.

## Unresolved Questions

- Does the instructor still require all 100 rubric points, or was an officially accepted Phase 1 subset issued outside this repository?
- Is Flink mandatory for this submission date, or deferred by an instructor decision?
- Is DataHub mandatory, or can PostgreSQL metadata plus an ERD substitute with explicit approval?
- Will fixture-backed generation be accepted, or must the generator expose configurable problem rates and summary metrics exactly as written?
- Are screenshots stored outside the repository and therefore unavailable to this audit?
