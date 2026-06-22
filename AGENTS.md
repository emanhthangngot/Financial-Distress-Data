# Financial Distress Data + AI System Constitution

Read this at the start of every Codex session in this repository.

## 1. Core Technology Stack

- Orchestrator: Apache Airflow running locally in Docker.
- Streaming: Apache Kafka single-node KRaft running locally in Docker.
- Optional streaming runtime: Apache Flink 1.19 (jobmanager + taskmanager) gated by the `flink` Docker Compose profile and the `ENABLE_FLINK=1` env var. Used by DAG 04 and the W17/W20 streaming evidence; not started by `docker compose up`.
- Batch processing: PySpark local mode with the S3A connector.
- Operational metadata: PostgreSQL running locally in Docker, schema `project_metadata`.
- Object storage: MinIO local S3-compatible storage, endpoint `http://minio:9000`.
- Local query engine: DuckDB using `httpfs`, usually inspected through DBeaver.

## 2. Spec-Driven Development Rules

`docs/spec.md` defines the Nexlab SDD operating model for this repository. Treat it as mandatory agent law, not background reading.

### Source of Truth Order

1. `AGENTS.md`: non-negotiable constitution and coding boundaries.
2. `docs/spec.md`: Nexlab SDD workflow, phase gates, and agent rules.
3. `docs/mini_coursework.md`: Phase 1 technical spec and implementation source of truth.
4. `docs/coursework.md`: Phase 2/full-coursework vision, used only when explicitly requested.
5. `docs/idea.md` and `docs/coursework_proposal.md`: discovery and PRD background.

If docs conflict, preserve Phase 1 local-first decisions from `AGENTS.md` and `docs/mini_coursework.md`.

### Nexlab SDD Phase Gates

- PH-0 Problem Discovery: understand `docs/idea.md`.
- PH-1 Product Spec: map constraints from `docs/coursework_proposal.md`.
- PH-2 Tech Architecture: use `docs/mini_coursework.md` for Phase 1 and `docs/coursework.md` for Phase 2.
- PH-3 Design: define CLI, database, DBeaver, DuckDB, and evidence-facing contracts.
- PH-4 SDD Setup: maintain `AGENTS.md`, Codex skills, specs, test strategy, and acceptance criteria.
- PH-5 Sprint Implementation: code only after meaningful PyTest test seeds exist and fail first.
- PH-6 Deploy and Go-live: local Docker cluster, Airflow, MinIO, PostgreSQL, DuckDB, and DBeaver evidence must prove the result.

### Implementation Rules

- Spec first: before writing code, read `docs/spec.md` and then `docs/mini_coursework.md` for Phase 1 work or `docs/coursework.md` for explicit Phase 2 work.
- Phase 1 scope is limited to `01_data_generator.md` and `02_schema_design.md`: data generation, schema design, Bronze/Silver/Gold pipelines, metadata, DQ, and evidence.
- Phase 2 ML or drift code must be isolated under `src/ml/` and `src/drift/` and must not modify Phase 1 pipeline behavior unless explicitly requested.
- Acceptance criteria must be written as `WHO -> ACTION -> RESULT`.
- Write PyTest test seeds before implementing core logic. The first run should fail for a meaningful reason.
- If a test fails, compare the test and code against the spec. Do not change expected values just to make tests pass.
- Do not proceed from plan to implementation if acceptance criteria are vague, untestable, or outside the active phase.

### Required Task Start Checklist

Before editing code or pipeline configs, the agent must state:

- Active phase: Phase 1 mini-coursework or explicit Phase 2.
- Spec files read.
- Acceptance criteria in `WHO -> ACTION -> RESULT` form.
- Skill(s) being used from `.codex/skills/`.
- Verification command or evidence target.

## 3. Directory Structure

- `dags/`: Airflow DAG definitions.
- `src/collectors/`: online API/WebSocket collectors and source adapters.
- `src/generator/`: test fixtures and fallback synthetic generators only.
- `src/streaming/`: Kafka producer and consumer logic.
  - `src/streaming/flink/`: opt-in Flink REST client and job artifacts dir (W26).
- `src/transforms/`: Bronze-to-Silver and Silver-to-Gold PySpark transforms.
- `src/quality/`: data quality checks with hard-fail and soft-fail policy.
- `src/catalog/`: MinIO bucket structure and DuckDB view registration.
- `src/metadata/`: PostgreSQL metadata clients and writers.
- `src/ml/`: Phase 2 only.
- `src/drift/`: Phase 2 only.
- `sql/`: PostgreSQL schema and DuckDB view SQL.
- `tests/`: PyTest unit and integration tests.
- `docs/`: coursework specs, design docs, and evidence.
- `.codex/skills/`: project-local Codex skills copied from `agent-skills` plus project-specific skills.

## 4. Local-First Boundaries

- Do not add AWS RDS, AWS S3, AWS Glue, AWS Athena, EMR, MSK, Redshift, SageMaker, or Kubernetes code for Phase 1.
- Do not import cloud-only packages such as `boto3` for Athena/Glue workflows.
- Use MinIO paths through `s3a://financial-distress-lake/...` in PySpark.
- Use DuckDB `httpfs` for Athena-style local SQL over MinIO Parquet.
- Use local PostgreSQL schemas: `project_metadata` for Phase 1 and `ml_metadata` for Phase 2.

## 5. Idempotency and Quality

- Bronze may be append-only.
- Silver and Gold writes must be idempotent and use overwrite on affected partitions.
- Deduplicate by business keys and latest `created_ts`.
- Data quality results must be logged to `project_metadata.data_quality_result`.
- Critical DQ failures halt downstream tasks. Warning-level issues route records to `project_metadata.failed_records` and may allow downstream processing.

## 6. Codex Skill Usage

Use `.codex/skills/using-agent-skills/SKILL.md` for general skill selection.

Always consider these project-specific skills first:

- `financial-distress-sdd`: use before any coursework planning or implementation.
- `local-lakehouse-data-engineering`: use for Airflow, Kafka, PySpark, MinIO, DuckDB, PostgreSQL, DQ, and pipeline evidence work.

For code changes, combine project-specific skills with:

- `spec-driven-development`
- `planning-and-task-breakdown`
- `test-driven-development`
- `incremental-implementation`
- `code-review-and-quality`
- `security-and-hardening`
