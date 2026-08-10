# 11. Rubric Completion Spec - 100/100 Submission Plan

## Objective

This document is the final Phase 1 mini-coursework completion spec. It maps
every row in `docs/Coursework Tracking (Public) - rubic (mini-coursework).csv`
to concrete repository work, checked-in proof, and a verification command.

Target score: **100/100**.

The goal is not to claim enterprise production readiness. The goal is to make
the local-first Phase 1 submission easy to grade: a reviewer can open the
README, specs, evidence JSON, screenshots, and tests, then confirm each rubric
row without reverse-engineering the repository.

## Active Phase

```text
PHASE: Phase 1 mini-coursework
SCOPE: 01_data_generator.md and 02_schema_design.md plus rubric evidence
```

Out of scope:

- Live external market API dependency.
- Managed cloud services.
- Phase 2 ML training, drift monitoring, serving, or model registry.
- Claims that require a live DataHub, Spark UI, or Flink UI service when the
  checked-in evidence is a local evidence view generated from artifacts.

## Source Specs

- `AGENTS.md`
- `docs/mini_coursework.md`
- `docs/01_data_generator.md`
- `docs/02_schema_design.md`
- `docs/Coursework Tracking (Public) - rubic (mini-coursework).csv`

## Commands

```bash
.venv/bin/python -m pytest tests
.venv/bin/python -m ruff check src dags tests scripts
.venv/bin/python -m black --check src dags tests scripts
docker compose config
.venv/bin/python scripts/audit_rubric_coverage.py
.venv/bin/python scripts/audit_stage1_evidence.py docs/evidence --check
.venv/bin/python scripts/stage1_readiness_report.py
```

Screenshot verification:

```bash
# Open each HTML file under docs/evidence/reviewer_screenshots/
# and capture the corresponding PNG with Chrome DevTools / Puppeteer.
```

## Acceptance Criteria

All acceptance criteria in this document use the required `WHO -> ACTION -> RESULT`
format.

```text
Reviewer -> opens this spec -> sees every rubric section mapped to work, proof, and commands.
Reviewer -> opens docs/evidence/reviewer_screenshots/*.png -> sees visual proof for the previously weak UI-heavy rubric rows.
Rubric audit runner -> runs scripts/audit_rubric_coverage.py -> reports 100 covered points.
Quality gate runner -> runs scripts/run_stage1_quality_gates.py -> tests, lint, formatting, Docker Compose config, and evidence audit pass.
Student -> submits repository -> can truthfully claim Phase 1 local-first evidence, not enterprise/live-service evidence.
```

## Engineering Fundamentals - 2 Points

### Docker and Docker Compose - 1 Point

Work completed:

- Define local deployable services in `docker-compose.yml`.
- Include PostgreSQL, MinIO, Kafka KRaft, Airflow webserver, Airflow scheduler,
  and optional Flink services behind the `flink` profile.

Proof:

- `docker-compose.yml`
- `docker compose config`
- `docs/evidence/README.md`

Acceptance:

```text
Reviewer -> runs docker compose config -> compose stack resolves without syntax errors.
```

### Optimized Dockerfile - 1 Point

Work completed:

- Use `infra/airflow/Dockerfile` for the Airflow image.
- Document optimization method and before/after evidence in
  `docs/08_docker_optimization.md`.

Proof:

- `infra/airflow/Dockerfile`
- `docs/08_docker_optimization.md`

Acceptance:

```text
Reviewer -> opens docker optimization doc -> sees the image-size reduction method and evidence target.
```

## Implement Data Generator - 20 Points

The CSV rubric contains 10 generator rows worth 2 points each. The internal
audit previously counted 18 points because it omitted the standalone streaming
generator configuration row. This spec treats the rubric CSV as source of truth
and maps all 20 points.

### Offline Skew - 2 Points

Work completed:

- Fixture generator creates ticker skew with a dominant ticker share.
- Evidence exports the observed distribution.

Proof:

- `configs/collector_config.yaml`
- `docs/evidence/stage1_generator_characteristics.json`
- `tests/test_generator_characteristics_evidence.py`

Acceptance:

```text
Generator evidence -> records skew distribution -> includes top_ticker and top_share.
```

### Offline High Cardinality - 2 Points

Work completed:

- Generator config exposes industry/sector pools and company count knobs.
- Evidence records distinct ticker, industry, and sector counts.

Proof:

- `configs/collector_config.yaml`
- `docs/evidence/stage1_generator_characteristics.json`

Acceptance:

```text
Generator evidence -> records cardinality metrics -> includes distinct_tickers, distinct_industries, and distinct_sectors.
```

### Offline Schema Evolution - 2 Points

Work completed:

- Legacy partitions simulate nulls for later-added financial columns.
- The evolution policy is documented for reviewer inspection.

Proof:

- `docs/01_data_generator.md`
- `configs/collector_config.yaml`

Acceptance:

```text
Generator config -> defines legacy_null_columns -> schema evolution behavior is reproducible.
```

### Offline Duplicate Rate - 2 Points

Work completed:

- Config defines a 2% offline duplicate rate.
- Bronze-to-Silver dedup keeps the latest `created_ts`.

Proof:

- `configs/collector_config.yaml`
- `tests/test_bronze_to_silver.py`
- `docs/evidence/stage1_generator_characteristics.json`

Acceptance:

```text
Bronze-to-Silver helper -> receives duplicate business keys -> keeps only the latest created_ts.
```

### Offline Generator Configuration - 2 Points

Work completed:

- Generator knobs live in `configs/collector_config.yaml`.
- Loader behavior is covered by `src/collectors/fixture_config.py`.

Proof:

- `configs/collector_config.yaml`
- `src/collectors/fixture_config.py`
- `tests/test_generator_config.py`

Acceptance:

```text
Generator config loader -> reads collector_config.yaml -> returns deterministic generator knobs.
```

### Bronze Landing - 2 Points

Work completed:

- Runtime evidence writes generated rows to Bronze paths before Silver/Gold.
- MinIO object inventory proves Bronze prefixes exist.

Proof:

- `docs/evidence/stage1_real_minio_objects.json`
- `docs/evidence/stage1_minio_objects.txt`

Acceptance:

```text
Evidence audit -> checks MinIO objects -> finds required Bronze, Silver, and Gold prefixes.
```

### Streaming Burst - 2 Points

Work completed:

- Streaming factory simulates burst windows.
- Micro-batch consumer flushes by count and time.

Proof:

- `src/streaming/problem_factory.py`
- `src/streaming/kafka_to_bronze_consumer.py`
- `docs/evidence/stage1_generator_characteristics.json`

Acceptance:

```text
Streaming generator -> creates burst records -> evidence records burst_count.
```

### Streaming Late Arrivals - 2 Points

Work completed:

- Streaming factory simulates late events with configurable lag.

Proof:

- `configs/collector_config.yaml`
- `src/streaming/problem_factory.py`
- `tests/test_streaming_problem_factory.py`

Acceptance:

```text
Streaming generator -> creates late-arrival records -> event_timestamp is earlier than created_ts by configured lag.
```

### Streaming Duplicate Rate - 2 Points

Work completed:

- Config defines `streaming_rate: 0.015`.
- Evidence records duplicate streaming events.

Proof:

- `configs/collector_config.yaml`
- `docs/evidence/stage1_generator_characteristics.json`

Acceptance:

```text
Streaming generator -> applies duplicate rate -> evidence records duplicate_count.
```

### Streaming Generator Configuration - 2 Points

Work completed:

- The streaming generator configuration is explicit in `collector_config.yaml`.
- Required knobs include `stream_flush_interval_seconds`,
  `stream_flush_record_count`, topic names, partitions, burst window, burst
  count, late-arrival lag, and duplicate rate.

Proof:

- `configs/collector_config.yaml`
- `tests/test_generator_config.py`
- `tests/test_streaming_problem_factory.py`

Acceptance:

```text
Reviewer -> opens collector_config.yaml -> sees stream_flush_record_count and stream_flush_interval_seconds controlling streaming evidence.
```

## Processing Jobs - 29 Points

The current CSV assigns 16 points to Spark and 13 points to Flink. The package
auditor reads those weights from `configs/rubric-requirements.yaml`; the old
20-point split is not valid for submission.

### Spark Baseline and Optimization - 16 Points

Work completed:

- Bronze-to-Silver and Silver-to-Gold Spark-compatible jobs exist.
- Optimizations cover skew handling, high-cardinality key handling, schema
  evolution, duplicate/dedup behavior, and Airflow integration.
- A reviewer-facing screenshot summarizes the Spark optimization evidence.

Proof:

- `dags/05_transform_bronze_to_silver.py`
- `dags/06_pyspark_silver_to_gold.py`
- `src/jobs/stage1_spark_lakehouse_job.py`
- `docs/05_storage_optimization.md`
- `docs/evidence/reviewer_screenshots/spark_optimization_evidence.png`

Acceptance:

```text
Reviewer -> opens Spark evidence screenshot -> sees baseline, optimization actions, and Airflow integration proof.
```

### Flink Streaming Processing - 13 Points

Work completed:

- Flink is opt-in via Docker Compose profile and `ENABLE_FLINK=1`.
- DAG 04 and Flink REST client wire the submission path.
- Streaming burst, late arrival, duplicate handling, and window behavior are
  documented through the local evidence view.

Proof:

- `docker-compose.yml`
- `dags/dag_04_stream_market_events_to_kafka.py`
- `src/streaming/flink/client.py`
- `src/streaming/flink/jobs/README.md`
- `docs/evidence/reviewer_screenshots/flink_streaming_evidence.png`

Acceptance:

```text
Reviewer -> opens Flink evidence screenshot -> sees opt-in runtime wiring and window-processing contract.
```

## Data Storage - 4 Points

### Lakehouse Optimization - 2 Points

Work completed:

- Small-file compaction helper and benchmark exist.
- Gold partitioning and Z-order policy are documented.

Proof:

- `src/lakehouse/compaction.py`
- `docs/05_storage_optimization.md`
- `docs/evidence/lakehouse_compaction_benchmark.json`

Acceptance:

```text
Reviewer -> opens compaction benchmark -> sees before/after file-count and size evidence.
```

### Data Warehouse Indexing - 2 Points

Work completed:

- DuckDB index benchmark demonstrates analytical query improvement.

Proof:

- `scripts/demo_duckdb_index.py`
- `docs/evidence/duckdb_index_benchmark.json`

Acceptance:

```text
Reviewer -> opens DuckDB benchmark -> sees indexed query speedup evidence.
```

## Data Pipeline Orchestration - 12 Points

### DP1 Bronze Ingest - 4 Points

Work completed:

- DP1 DAG graph and task-tree evidence are checked in.

Proof:

- `dags/dp1_bronze_ingest.py`
- `docs/evidence/w20_dp1_airflow_dag_graph.png`
- `docs/evidence/w20_dp1_airflow_task_tree.png`

Acceptance:

```text
Reviewer -> opens DP1 screenshot -> sees ingest and validate stages in order.
```

### DP2 Bronze to Silver/Gold - 4 Points

Work completed:

- Bronze-to-Silver and Silver-to-Gold DAGs define ingest/transform/validate
  work.
- Reviewer-facing screenshot summarizes the DP2 task order.

Proof:

- `dags/05_transform_bronze_to_silver.py`
- `dags/06_pyspark_silver_to_gold.py`
- `dags/07_run_data_quality_checks.py`
- `docs/evidence/reviewer_screenshots/airflow_dp2_dp3_evidence.png`

Acceptance:

```text
Reviewer -> opens Airflow DP2/DP3 evidence screenshot -> sees DP2 ingest and validate stages.
```

### DP3 Offline Feature Table - 4 Points

Work completed:

- Gold feature builders produce financial, market, news, and unified feature
  tables.
- DQ validation confirms downstream safety.

Proof:

- `src/transforms/silver_to_gold.py`
- `src/jobs/stage1_spark_lakehouse_job.py`
- `docs/evidence/stage1_real_duckdb_validation.json`
- `docs/evidence/reviewer_screenshots/airflow_dp2_dp3_evidence.png`

Acceptance:

```text
Reviewer -> opens DP3 evidence -> sees feature build and validation stages.
```

## Data Governance - 12 Points

Work completed:

- DP1, DP2, and DP3 each have lineage JSON and validation/contract JSON.
- A reviewer-facing screenshot presents the lineage and validation contracts in
  a DataHub-style local evidence view.

Proof:

- `docs/evidence/governance/dp1_lineage.json`
- `docs/evidence/governance/dp1_validation.json`
- `docs/evidence/governance/dp2_lineage.json`
- `docs/evidence/governance/dp2_validation.json`
- `docs/evidence/governance/dp3_lineage.json`
- `docs/evidence/governance/dp3_validation.json`
- `docs/evidence/reviewer_screenshots/governance_lineage_contracts_evidence.png`

Acceptance:

```text
Reviewer -> opens governance evidence screenshot -> sees DP1, DP2, and DP3 lineage plus contract validation.
```

## Documentation - 10 Points

Work completed:

- Schema design is documented with Bronze, Silver, and Gold views.
- DBeaver ERD screenshot is checked in.
- Dimensional SCD2 fields and feature-table timestamp fields are documented.
- Naming convention is locked by tests.

Proof:

- `docs/02_schema_design.md`
- `images/schema/schema_evidence_erd.png`
- `tests/test_naming_convention.py`

Acceptance:

```text
Reviewer -> opens schema design doc -> sees SCD2 fields, feature timestamp fields, relationships, and naming conventions.
```

## README + Deployment Diagram - Mandatory, Unscored

Work completed:

- README contains business domain, project structure, table of contents, and
  deployment diagrams.
- Source files and functions are guarded by docstring tests.
- Deployment diagram uses deployable units and numbered data-flow labels.

Proof:

- `README.md`
- `images/architecture/system_deployment_diagram.png`
- `images/architecture/system_deployment_diagram.dot`
- `tests/test_readme_polish.py`
- `tests/test_module_docstrings.py`
- `tests/test_deployment_diagram_assets.py`

Acceptance:

```text
Reviewer -> opens README -> sees business domain, ToC, repo structure, and deployable-unit diagrams.
```

## Novel Ideas - 10 Points

### Novel Idea 1 - 5 Points

Work completed:

- dbt-style SQL contract macros validate core schema behavior.

Proof:

- `docs/09_novel_idea_1.md`
- `docs/evidence/dbt_macro_check.json`

Acceptance:

```text
Reviewer -> opens idea 1 doc and proof -> sees the idea and a successful local evidence artifact.
```

### Novel Idea 2 - 5 Points

Work completed:

- Airbyte-style declarative ingestion manifest documents future adapter wiring.

Proof:

- `docs/10_novel_idea_2.md`
- `configs/ingestion_manifest.yaml`
- `docs/evidence/airbyte_manifest_run.json`

Acceptance:

```text
Reviewer -> opens idea 2 doc and proof -> sees the manifest-driven ingestion idea and a successful local evidence artifact.
```

## Reviewer Screenshot Pack

The screenshot pack lives under:

```text
docs/evidence/reviewer_screenshots/
```

- `airflow_dp2_dp3_evidence.html`
- `airflow_dp2_dp3_evidence.png`
- `spark_optimization_evidence.html`
- `spark_optimization_evidence.png`
- `flink_streaming_evidence.html`
- `flink_streaming_evidence.png`
- `governance_lineage_contracts_evidence.html`
- `governance_lineage_contracts_evidence.png`

Each HTML file states:

```text
Generated from checked-in Stage 1 evidence
```

That wording is deliberate. These are reproducible reviewer evidence screens
rendered from repository artifacts. They are not a false claim that live Spark
UI, Flink UI, or DataHub was running during grading.

For the strongest submission, replace these with **genuine UI screenshots**
captured from the running local stack. `docs/ui-screenshot-runbook.md` and
`scripts/capture_ui_screenshots.py` automate that capture:

```text
Reviewer -> runs scripts/capture_ui_screenshots.py against the running stack -> gets real Airflow/DataHub/Flink UI captures in docs/evidence/screenshots/.
```

## Final Verification Matrix

| Check | Command | Expected |
|---|---|---|
| Unit/contract tests | `.venv/bin/python -m pytest tests` | pass |
| Lint | `.venv/bin/python -m ruff check src dags tests scripts` | pass |
| Formatting | `.venv/bin/python -m black --check src dags tests scripts` | pass |
| Compose syntax | `docker compose config` | pass |
| Rubric coverage | `.venv/bin/python scripts/audit_rubric_coverage.py` | 100 covered points |
| Runtime evidence | `.venv/bin/python scripts/audit_stage1_evidence.py docs/evidence --check` | pass |
| Readiness | `.venv/bin/python scripts/stage1_readiness_report.py` | coursework ready |
