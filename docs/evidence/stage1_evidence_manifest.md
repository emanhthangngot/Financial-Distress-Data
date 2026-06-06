# Stage 1 Evidence Manifest

This manifest separates implemented runtime contracts from design-only scope.
Stage 1 is production-inspired and ready for local runtime evidence collection;
it is not enterprise-ready.

## Implemented

- Fixture-backed collectors through `VnstockFixtureAdapter`.
- Bronze, Silver, and Gold deterministic evidence payload generation.
- Bronze-to-Silver schema alignment and latest-`created_ts` deduplication.
- Gold dimension, fact, OBT, distress-label, and PIT feature helper contracts.
- Kafka stream event contracts and micro-batch Bronze path generation.
- PostgreSQL `project_metadata` DDL and runtime metadata writer.
- DQ helpers plus runtime `DQRunner` with critical halt policy.
- MinIO Parquet evidence writer.
- MinIO evidence artifact writer under `evidence/stage1/run_id=.../`.
- DuckDB view and validation query runner.
- Primary Airflow evidence DAG: `stage1_local_evidence_pipeline`.
- CI-style gates: PyTest, Ruff, Black, and Docker Compose config validation.

## Designed But Not Implemented

- Live online vnstock/SSI/HOSE/HNX ingestion adapter.
- Live news source collector.
- `fact_news_sentiment` and dedicated `feat_company_news_30d` builder.
- Full Spark-submit Airflow tasks for all Silver and Gold tables.
- Kafka broker producer plus offset-commit-after-Bronze-write runtime path.
- Full lineage table beyond run logs, DQ rows, freshness, and schema registry.

## Remaining Evidence Work

- Run `docker compose up -d` on the local machine.
- Run `.venv/bin/python scripts/run_stage1_evidence.py`.
- Confirm MinIO contains `evidence/stage1/run_id=.../` artifact JSON/text files.
- Capture PostgreSQL query exports or DBeaver screenshots for:
  - `project_metadata.pipeline_run_log`
  - `project_metadata.data_quality_result`
  - `project_metadata.dataset_freshness`
  - `project_metadata.schema_version_registry`
- Capture MinIO object screenshots for Bronze, Silver, and Gold prefixes.
- Capture DuckDB validation query output against Gold views.
- Trigger and capture Airflow evidence for `stage1_local_evidence_pipeline`.
- Capture Kafka topic creation evidence from `init/kafka_init_topics.sh`.

## Out Of Scope For Phase 1

- AWS, cloud object storage, Glue, Athena, RDS, EMR, MSK, Redshift, SageMaker.
- Kubernetes.
- ML training, scoring, model registry, model serving, and drift monitoring.
- LLM assistant or enterprise-scale production claims.
