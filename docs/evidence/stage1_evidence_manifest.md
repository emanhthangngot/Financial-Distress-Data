# Stage 1 Evidence Manifest

This manifest separates implemented runtime contracts from design-only scope.
Stage 1 is production-inspired and has executable local runtime evidence; it is
not enterprise-ready.

## Implemented

- Fixture-backed collectors through `VnstockFixtureAdapter`.
- Bronze, Silver, and Gold deterministic evidence payload generation.
- Bronze-to-Silver schema alignment and latest-`created_ts` deduplication.
- Gold dimension, fact, OBT, distress-label, and PIT feature helper contracts.
- Kafka stream event contracts and micro-batch Bronze path generation.
- Kafka broker produce/consume path for fixture-backed price, news, and alert events.
- PostgreSQL `project_metadata` DDL and runtime metadata writer.
- DQ helpers plus runtime `DQRunner` with critical halt policy.
- Runtime DQ checks over actual Silver/Gold Parquet, plus a DQ failure probe that
  persists a critical failure before halting.
- Backfill request, dataset freshness, source request, and collector checkpoint
  metadata persistence.
- MinIO Parquet evidence writer.
- MinIO evidence artifact writer under `evidence/stage1/run_id=.../`.
- DuckDB view and validation query runner.
- Gold news sentiment and market alert facts.
- Split Gold feature tables for financial, market, and news features.
- Machine-readable runtime evidence audit summary.
- Primary Airflow evidence DAG: `stage1_local_evidence_pipeline`.
- Connected real E2E DAG: `stage1_real_e2e_pipeline`.
- DP1 Bronze pipeline DAG: `dp1_bronze_ingest` (ingest + validate stages, 3 batch collectors).
- CI-style gates: PyTest, Ruff, Black, and Docker Compose config validation.

## Designed But Not Implemented

- Live online vnstock/SSI/HOSE/HNX ingestion adapter.
- Live news source collector.
- Full lineage table beyond run logs, DQ rows, freshness, backfill metadata, and
  evidence artifacts.
- External schema registry for Kafka events.
- Iceberg/Delta/Hudi table format support.

## Remaining Evidence Work

- Refresh evidence when code changes:
  - `docker compose up -d`
  - `.venv/bin/python scripts/run_stage1_real_e2e.py --execution-date <iso-ts> --export-evidence <dir>`
  - `.venv/bin/python scripts/run_stage1_dq_failure_probe.py --run-id <id> --export-evidence <dir>`
  - `.venv/bin/python scripts/audit_stage1_evidence.py <dir>`
- Capture optional PostgreSQL query exports or DBeaver screenshots for:
  - `project_metadata.pipeline_run_log`
  - `project_metadata.data_quality_result`
  - `project_metadata.dataset_freshness`
  - `project_metadata.backfill_request`
  - `project_metadata.source_request_log`
  - `project_metadata.collector_checkpoint`
  - `project_metadata.schema_version_registry`
- Capture optional MinIO object screenshots for Bronze, Silver, Gold, and
  `evidence/stage1/` prefixes.
- Capture optional DuckDB/DBeaver screenshots for Gold views.
- Capture live Airflow UI screenshots for `dp1_bronze_ingest` (DP1 rubric row):
  the committed `docs/evidence/w20_dp1_airflow_dag_graph.png` and
  `w20_dp1_airflow_task_tree.png` are graphviz-rendered approximations
  of the DAG graph and task tree; refresh from a running Airflow UI when
  Docker daemon access is available locally.

## Out Of Scope For Phase 1

- AWS, cloud object storage, Glue, Athena, RDS, EMR, MSK, Redshift, SageMaker.
- Kubernetes.
- ML training, scoring, model registry, model serving, and drift monitoring.
- LLM assistant or enterprise-scale production claims.
