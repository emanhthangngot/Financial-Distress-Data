---
title: "Financial Distress Data — Project File Map"
date: 2026-08-10
status: active-study-guide
scope: "Phase 1 local lakehouse + Phase 2 additive ML/LLM/product plane"
---

# Project File Map — bản đồ để trả lời và mở file ngay

Tài liệu này là “bản đồ tra cứu khi bị hỏi”, không phải danh sách file để học
thuộc lòng. Repo hiện có khoảng 946 file tracked. Cách nhớ hiệu quả là nhớ
luồng dữ liệu, sau đó mở đúng entrypoint, test và documentation liên quan.

## 0. Cách dùng trong 30 giây

Khi được hỏi một chức năng:

1. Xác định **lớp**: collect, stream, transform, quality, metadata, catalog,
   ML/LLM hay product.
2. Mở **entrypoint** trong bảng tra cứu nhanh.
3. Mở **test cùng tên** để chứng minh behavior.
4. Nếu cần nói architecture hoặc contract, mở thêm doc được chỉ ra.

Lệnh mở nhanh:

```bash
# đọc file chính
sed -n '1,240p' src/transforms/silver_to_gold.py

# tìm function/class/DAG trong toàn repo
grep -R -n -E 'def |class |dag_id|@dag' src dags tests scripts

# xem toàn bộ file tracked hiện tại
git ls-files

# xem file theo một layer
git ls-files src/transforms dags tests | sort
```

## 1. Câu chuyện cần nhớ

```text
Source/API/disclosure
        -> Collectors
        -> Bronze raw evidence
        -> Silver normalize + dedupe
        -> Gold facts + features + labels
        -> DQ + metadata + lineage
        -> DuckDB / Analyst / ML / RAG / Product
```

Mnemonic của Phase 1: **C-S-T-Q-M-C**

| Ký tự | Nhớ là | Mở thư mục chính |
|---|---|---|
| C | Collect | `src/collectors/` |
| S | Stream | `src/streaming/` |
| T | Transform | `src/transforms/` + `src/jobs/` |
| Q | Quality | `src/quality/` |
| M | Metadata | `src/metadata/` + `src/governance/` |
| C | Catalog/Consumer | `src/catalog/`, `apps/`, `feature_repo/` |

Phase 2 nhớ là **G-M-L-P**: Generator → ML/Drift → LLM/RAG → Product.

## 2. Trạng thái phải nói chính xác

| Nhãn | Ý nghĩa khi thuyết trình |
|---|---|
| ✅ Phase 1 verified | Local-first pipeline, fixture collectors, Bronze/Silver/Gold, Kafka, DQ, metadata, DuckDB và runtime evidence đã có code/test/evidence. |
| 🟡 Phase 2 additive | ML, drift, RAG, Feast, product web app và contracts được thêm vào; không được nói là thay đổi Phase 1. |
| 🧪 Fixture-backed | `vnstock_adapter.py` hiện re-export fixture adapter; không nói là live production API nếu chưa có runtime proof. |
| 📦 Generated | `docs/evidence/**`, `outputs/**`, `warehouse.db` và report artifacts được tạo lại bằng script; không sửa tay. |
| ⚠️ Separate repo | AWS/EKS/GitOps platform của Phase 2 nằm ở control repo riêng; repo này chỉ có wrappers/evidence cần thiết. |

## 3. Tra cứu nhanh theo câu hỏi

| Nếu bị hỏi… | Mở ngay | File/test chứng minh tiếp theo |
|---|---|---|
| Source adapter ở đâu? | `src/collectors/source_adapters/base.py` | `src/collectors/source_adapters/vnstock_adapter.py`, `tests/test_runtime_adapters.py` |
| Vì sao không gọi live API? | `src/collectors/source_adapters/vnstock_adapter.py` | `src/collectors/source_adapters/vnstock_fixture_adapter.py`, `docs/mini_coursework.md` |
| Thu company master thế nào? | `src/collectors/company_list_collector.py` | `dags/01_collect_company_master_data.py`, `tests/test_dp1_pipeline.py` |
| Thu financial statements thế nào? | `src/collectors/financial_statement_collector.py` | `dags/02_collect_financial_statement_api.py`, `tests/test_schema_contracts.py` |
| Thu market price thế nào? | `src/collectors/market_price_collector.py` | `dags/03_collect_market_price_api.py`, `tests/test_streaming.py` |
| Bronze lưu ở đâu? | `src/io/paths.py`, `src/io/minio_writer.py` | `dags/ingest_source_to_bronze.py`, `docs/data-pipeline-orchestration.md` |
| Silver làm gì? | `src/transforms/bronze_to_silver.py` | `src/transforms/silver/core.py`, `tests/test_bronze_to_silver.py` |
| Dedupe theo rule nào? | `src/transforms/silver/core.py` | `tests/test_bronze_to_silver.py`, `docs/07_data_contracts.md` |
| Gold fact/dimension ở đâu? | `src/transforms/silver_to_gold.py` | `src/transforms/gold/`, `tests/test_silver_to_gold.py` |
| Distress label tính thế nào? | `src/transforms/compute_distress_labels.py` | `tests/test_distress_labels.py`, `docs/02_schema_design.md` |
| OBT company-quarter risk ở đâu? | `src/transforms/gold/obt_company_quarter_risk.py` | `tests/test_obt_company_quarter_risk.py` |
| PIT leakage guard ở đâu? | `src/transforms/features/point_in_time.py` | `src/transforms/features/pit.py`, `tests/test_real_e2e_contracts.py` |
| DQ check nào đang chạy? | `src/quality/dq_checks.py` | `src/quality/dq_runner.py`, `tests/test_dq_checks.py` |
| Critical fail có halt không? | `src/quality/dq_runner.py` | `scripts/run_stage1_dq_failure_probe.py`, `tests/test_stage1_jobs.py` |
| Metadata lưu gì? | `src/metadata/metadata_writer.py` | `sql/init_project_metadata.sql`, `tests/test_stage1_jobs.py` |
| DuckDB inspect Gold thế nào? | `src/catalog/duckdb_catalog.py` | `src/catalog/duckdb_runner.py`, `sql/duckdb_validation_queries.sql` |
| Kafka event contract ở đâu? | `src/streaming/events.py` | `src/streaming/kafka_producer.py`, `tests/test_streaming.py` |
| Kafka vào Bronze thế nào? | `src/streaming/kafka_to_bronze_consumer.py` | `src/jobs/kafka_to_bronze_job.py`, `dags/dag_04_stream_market_events_to_kafka.py` |
| Flink có chạy mặc định không? | `src/streaming/flink_contract.py` | `src/streaming/flink/jobs/price_event_job.py`, `docs/flink-stream-processing.md` |
| DAG DP1/DP2/DP3 là gì? | `docs/data-pipeline-orchestration.md` | `dags/ingest_source_to_bronze.py`, `dags/build_silver_gold.py`, `dags/build_offline_features.py` |
| DataHub lineage ở đâu? | `src/governance/datahub_model.py` | `src/governance/datahub_emitter.py`, `configs/datahub/governance.yaml` |
| Phase 2 ML contract ở đâu? | `src/ml/contracts.py` | `src/ml/label_pipeline.py`, `src/ml/feast/`, `tests/phase2/pipelines/` |
| Drift được tạo/check thế nào? | `src/drift/generator.py` | `configs/drift-config.yaml`, `scripts/run_phase2_drift_report.py` |
| RAG ingest ở đâu? | `src/llm/rag_pipeline.py` | `src/llm/rag/`, `configs/rag-sources.yaml`, `tests/phase2/pipelines/test_rag_*` |
| Product page ở đâu? | `apps/web/src/app/` | `apps/web/src/components/`, `apps/web/e2e/` |
| RBAC/RLS ở đâu? | `supabase/migrations/20260803214600_phase2_rls.sql` | `packages/contracts/src/authorization.ts`, `tests/phase2/product/test_rbac_rls.py` |
| Outbox worker ở đâu? | `apps/web/src/lib/server/outbox-worker.ts` | `apps/web/scripts/phase2/outbox-worker.ts`, `supabase/migrations/20260804150000_phase2_outbox_worker.sql` |
| Chạy quality gate nào? | `scripts/run_stage1_quality_gates.py` | `AGENTS.md`, `.github/workflows/ci.yml` |
| Runtime evidence ở đâu? | `scripts/run_stage1_real_e2e.py` | `scripts/audit_stage1_evidence.py`, `docs/evidence/stage1_runtime_audit_summary.json` |

## 4. Top-level map

| Path | Tác dụng | Trạng thái |
|---|---|---|
| `AGENTS.md` | Quy tắc bất biến, phase boundary, data contract và quality gate. | Source of truth cho cách làm |
| `CLAUDE.md` | Pointer/routing cho Claude Code skills. | Tooling |
| `README.md` | Setup, architecture, evidence snapshot, validation commands. | Entry point cho repo |
| `environment template` | Mẫu biến môi trường local. | Không chứa secret thật |
| `.github/workflows/` | CI Phase 1 và Phase 2. | Automation |
| `configs/` | YAML contracts cho collector, DQ, Spark, Flink, generator, RAG, governance. | Config |
| `dags/` | Airflow workflows Phase 1; `dags/phase2/` là wrapper additive. | Orchestration |
| `src/` | Python business logic và runtime helpers. | Core source |
| `tests/` | Unit, contract, integration, product và rubric tests. | Verification |
| `scripts/` | Runner, auditor, evidence exporter, demo và quality gates. | Operational tooling |
| `sql/` | PostgreSQL metadata DDL và DuckDB views/validation. | Data contract |
| `infra/` | Docker build contexts và Kafka topic bootstrap. | Container tooling |
| `docker-compose.yml` | Local Postgres, MinIO, Kafka, Airflow và optional Flink. | Local platform |
| `apps/web/` | Phase 2 Next.js product plane. | Product |
| `packages/contracts/` | Shared TypeScript domain/UI/auth contracts. | Product boundary |
| `supabase/` | Supabase config, migrations, RLS và outbox schema. | Product backend |
| `feature_repo/` | Feast feature store definitions cho structured/RAG features. | Phase 2 ML |
| `images/` | Architecture/schema source assets và rendered diagrams. | Docs assets |
| `docs/` | Specs, runbooks, ADRs, evidence và onboarding material. | Human/AI docs |
| `plans/` | Historical implementation plans, phases và reports. | Project history |
| `package.json`, `pnpm-workspace.yaml` | JS workspace root. | Phase 2 tooling |
| `pyproject.toml`, `requirements.txt`, `uv.lock` | Python package, tooling và dependency locks. | Python tooling |
| `pnpm-lock.yaml` | JS dependency lock. | Generated lockfile |
| `warehouse.db` | DuckDB local catalog. | Generated, không sửa tay |
| `outputs/` | Local generated pipeline/evidence outputs. | Generated, không commit tùy tiện |

## 5. Python source map — Phase 1

### `src/collectors/` — collect và source boundary

| File | Tác dụng |
|---|---|
| `company_list_collector.py` | Chuẩn hóa company master từ adapter thành batch records. |
| `financial_statement_collector.py` | Thu quarterly financial statements. |
| `market_price_collector.py` | Thu daily price/market records. |
| `fixture_config.py` | Config deterministic fixture collector. |
| `manifest_adapter.py` | Adapter đọc manifest/source evidence. |
| `run_manifest_smoke.py` | Smoke check cho collector manifest. |
| `source_adapters/base.py` | `SourceAdapter` protocol: companies, financials, prices. |
| `source_adapters/vnstock_adapter.py` | Live adapter boundary; hiện re-export fixture adapter. |
| `source_adapters/vnstock_fixture_adapter.py` | Deterministic vnstock-shaped fixture implementation. |
| `__init__.py` | Package boundary. |

### `src/generator/` — tạo dữ liệu offline/streaming

| File | Tác dụng |
|---|---|
| `config.py` | Load/validate generator YAML và profile. |
| `profile.py` | Profile characteristics, seed và runtime knobs. |
| `offline.py` | Sinh financial statements/companies offline. |
| `streaming.py` | Sinh event stream từ generator output. |
| `storage.py` | Lưu/đọc generator output và metadata. |

### `src/streaming/` — Kafka và Flink boundary

| File | Tác dụng |
|---|---|
| `events.py` | Event schema, stable event ID, serialization contract. |
| `kafka_producer.py` | Serialize và publish Kafka events. |
| `kafka_to_bronze_consumer.py` | Micro-batch consumer, dedupe, Bronze write. |
| `problem_factory.py` | Tạo price/news/alert problem events. |
| `flink_contract.py` | Flink variant config và benchmark contract. |
| `flink/client.py` | HTTP/client boundary tới Flink runtime. |
| `flink/jobs/price_event_job.py` | Opt-in Flink price event job. |
| `flink/jobs/README.md` | Hướng dẫn riêng cho Flink job. |
| `__init__.py` | Package boundary. |

### `src/transforms/` — Bronze → Silver → Gold

| File | Tác dụng |
|---|---|
| `bronze_to_silver.py` | Public entrypoint re-export pure Python + Spark transform. |
| `silver/core.py` | Normalize columns, align schema, deduplicate latest record. |
| `silver/bronze_to_silver_spark.py` | Spark DataFrame Bronze-to-Silver path. |
| `silver_to_gold.py` | Public Gold entrypoint: facts, features, OBT, Parquet. |
| `gold/dim_company.py` | Build company/date dimensions và SCD2 history. |
| `gold/fact_financial_statement.py` | Gold financial statement fact. |
| `gold/fact_market_price.py` | Gold market price fact, including Spark path. |
| `gold/fact_market_alert.py` | Gold market alert fact. |
| `gold/fact_news_sentiment.py` | Gold news sentiment fact. |
| `gold/obt_company_quarter_risk.py` | Unified company-quarter risk view/OBT. |
| `gold/parquet.py` | Partition-aware idempotent Parquet write. |
| `features/point_in_time.py` | PIT joins and financial/market/news feature builders. |
| `features/pit.py` | PIT helper variant and feature construction. |
| `compute_distress_labels.py` | Rule-based Z-score-inspired label/proxy. |
| `keys.py` | Canonical company/date/business key functions. |
| `sector_policy.py` | Sector exclusions/policy. |
| `spark_session.py` | Local Spark session/config helper. |
| `__init__.py` + subpackage `__init__.py` | Public package boundaries. |

### `src/quality/`, `src/metadata/`, `src/catalog/`

| Path | Tác dụng |
|---|---|
| `quality/dq_checks.py` | Not-null, unique, referential integrity, freshness, retention và PIT checks. |
| `quality/dq_runner.py` | Chạy check registry, severity semantics và critical halt. |
| `quality/rule_config.py` | Load DQ rule configuration. |
| `quality/contract_checker.py` | Validate dataset/schema contract. |
| `quality/sql_contract_runner.py` | Execute SQL contract macros/queries. |
| `quality/sql_contract_macros.sql` | Reusable SQL contract macros. |
| `metadata/metadata_writer.py` | Ghi pipeline run, DQ, freshness, source request, checkpoint. |
| `metadata/schema_registry.py` | Dataset schema/version registry. |
| `catalog/duckdb_catalog.py` | Register/query local Parquet bằng DuckDB. |
| `catalog/duckdb_runner.py` | Runtime DuckDB validation/evidence runner. |

### `src/io/`, `src/jobs/`, `src/orchestration/`

| Path | Tác dụng |
|---|---|
| `io/paths.py` | Canonical MinIO/local path conventions. |
| `io/minio_writer.py` | Write Parquet/object vào MinIO. |
| `io/minio_publish.py` | Publish/promote MinIO prefixes. |
| `io/atomic_publish.py` | Atomic promotion/rollback helper. |
| `io/optional_input.py` | Optional input/config behavior. |
| `jobs/kafka_to_bronze_job.py` | Evidence/runtime wrapper cho stream-to-Bronze. |
| `jobs/stage1_dq_job.py` | Read objects, run Stage 1 DQ và persist result. |
| `jobs/stage1_publish.py` | Persist failed rows và evidence publish. |
| `jobs/stage1_evidence_job.py` | Build machine-readable evidence payload. |
| `jobs/stage1_spark_lakehouse_job.py` | Spark local lakehouse runtime wrapper. |
| `jobs/spark_baseline_job.py` | Baseline Spark alignment cho benchmark. |
| `jobs/spark_optimized_job.py` | Optimized Spark alignment cho benchmark. |
| `jobs/spark_benchmark_common.py` | Shared benchmark variant config/metrics. |
| `jobs/spark_storage_experiment.py` | Storage/file-size experiment. |
| `orchestration/airflow_tasks.py` | Reusable Airflow task callables. |
| `orchestration/pipeline_contracts.py` | DP1/DP2/DP3 task/result contracts. |

### `src/governance/`, `src/evidence/`, `src/lakehouse/`, `src/security/`

| Path | Tác dụng |
|---|---|
| `governance/datahub_model.py` | Validated datasets, pipelines, contracts và lineage model. |
| `governance/datahub_emitter.py` | Emit governance model sang DataHub. |
| `governance/datahub_graphql.py` | DataHub GraphQL client/query helper. |
| `governance/phase2_lineage.py` | Phase 2 lineage bridge/evidence. |
| `evidence/run_manifest.py` | Machine-readable run manifest. |
| `evidence/rubric_audit.py` | Audit rubric/evidence mapping. |
| `lakehouse/compaction.py` | Compact small Parquet files. |
| `security/secrets.py` | Load secrets từ environment/secret source, không default secret. |

## 6. Python source map — Phase 2 additive

| Path | Tác dụng và mức độ |
|---|---|
| `src/ml/contracts.py` | Signature contracts cho ML services. |
| `src/ml/label_pipeline.py` | Build/persist labels và drift-aware Phase 2 task wrapper. |
| `src/ml/feast/feature_definitions.py` | Feast feature/view definitions. |
| `src/ml/feast/materialization.py` | Online/offline feature materialization service. |
| `src/ml/feast/offline_job.py` | Aggregate/write offline stream features. |
| `src/ml/feast/online_job.py` | Push/read online features. |
| `src/drift/generator.py` | Seeded synthetic drift scenarios và report. |
| `src/drift/generator_config.py` | Drift scenario configuration. |
| `src/llm/contracts.py` | RAG, embedding, MCP, orchestration và release contracts. |
| `src/llm/rag_pipeline.py` | Fixture-backed document fetch → chunk → govern → embed → PGVector. |
| `src/llm/data_governance.py` | Licensing/access/metadata gate cho RAG. |
| `src/llm/rag/chunking.py` | Normalize, hash, chunk và parser version. |
| `src/llm/rag/embedding.py` | Embedding backend protocol/HTTP adapter boundary. |
| `src/llm/rag/pgvector_store.py` | Vector storage/version/idempotency boundary. |
| `src/agents/` | Chưa có package source trong checkout hiện tại; agent behavior nằm ở Phase 2 contracts/evidence/product scope. |

## 7. Airflow DAG map

| DAG file | Vai trò |
|---|---|
| `01_collect_company_master_data.py` | Company master ingestion. |
| `02_collect_financial_statement_api.py` | Financial statement ingestion. |
| `03_collect_market_price_api.py` | Market price ingestion. |
| `dag_04_stream_market_events_to_kafka.py` | Stream price/news/alert events to Kafka. |
| `05_transform_bronze_to_silver.py` | Bronze → Silver normalization. |
| `06_pyspark_silver_to_gold.py` | Spark Silver → Gold materialization. |
| `07_run_data_quality_checks.py` | DQ validation/persist. |
| `08_minio_duckdb_register_tables.py` | Register/query MinIO Parquet in DuckDB. |
| `09_data_governance.py` | DataHub/governance emit. |
| `ingest_source_to_bronze.py` | DP1 reusable source → Bronze pipeline. |
| `build_silver_gold.py` | DP2 reusable Silver/Gold pipeline. |
| `build_offline_features.py` | DP3 offline feature build + PIT validation. |
| `dp1_bronze_ingest.py` | DP1 evidence-oriented wrapper. |
| `stage1_local_evidence_pipeline.py` | Lightweight local evidence DAG. |
| `stage1_real_e2e_pipeline.py` | Connected real local E2E evidence DAG. |
| `_stage1_dag_utils.py` | Shared Stage 1 DAG helper. |
| `utils/stage1_dag_utils.py` | DAG utility package boundary/helper. |
| `phase2/phase2_feature_materialize.py` | Phase 2 feature materialization wrapper. |
| `phase2/phase2_label_drift_build.py` | Drift report + label build wrapper. |
| `phase2/phase2_rag_ingest.py` | RAG ingestion wrapper. |
| `phase2/phase2_stream_feature_offline.py` | Offline stream feature wrapper. |
| `phase2/phase2_stream_feature_online.py` | Online stream feature wrapper. |

DAG rule cần nhớ: Phase 2 wrappers không được có import-time side effect và
không được đổi DAG ID/task của Phase 1.

## 8. Script map — chạy, kiểm tra, xuất evidence

### Quality/evidence/audit

| File | Tác dụng |
|---|---|
| `run_stage1_quality_gates.py` | One-shot pytest + ruff + black + compose config gate. |
| `run_stage1_real_e2e.py` | Chạy local Airflow/Kafka/MinIO/Postgres E2E. |
| `run_stage1_evidence.py` | Stage 1 evidence runner. |
| `run_stage1_dq_failure_probe.py` | Prove critical DQ failure persists then halts. |
| `stage1_readiness_report.py` | Reviewer-facing readiness report. |
| `audit_stage1_evidence.py` | Audit Stage 1 evidence completeness/truth. |
| `audit_mini_coursework_rubric.py` | Audit mini-coursework rubric. |
| `audit_rubric_coverage.py` | Check rubric-to-file/evidence coverage. |
| `audit_phase2_evidence.py` | Audit Phase 2 evidence/matrix. |
| `audit_flink_evidence.py` | Audit Flink runtime/contract evidence. |
| `audit_spark_benchmark.py` | Audit Spark benchmark outputs. |
| `check_stage1_services.py` | Check local service readiness. |
| `check_documentation.py` | Documentation/link/contract checks. |

### Generator, benchmark, storage, schema

| File | Tác dụng |
|---|---|
| `run_generator_and_profile.py` | Generate data + profile characteristics. |
| `run_flink_benchmark.py` | Opt-in Flink benchmark. |
| `run_spark_benchmark.py` | Baseline/optimized Spark benchmark. |
| `demo_duckdb_index.py` | Demonstrate DuckDB indexing/query improvement. |
| `demo_lakehouse_compaction.py` | Demonstrate small-file compaction. |
| `build_schema_evidence.py` | Build schema evidence artifacts. |
| `export_docker_optimization.py` | Export Docker optimization evidence. |
| `export_phase6_airflow_evidence.py` | Export DP1/DP2/DP3 Airflow evidence. |
| `measure_docker_size.sh` | Measure image/storage sizes. |

### Phase 2, UI, governance and rubric generation

| File | Tác dụng |
|---|---|
| `generate_phase2_matrix.py` | Generate Phase 2 rubric matrix. |
| `generate_phase2_requirement_tests.py` | Generate requirement test skeletons/contracts. |
| `run_phase2_drift_report.py` | Run drift scenario and report. |
| `smoke_embedding_endpoint.py` | Smoke test embedding endpoint/math. |
| `sync_datahub_governance.py` | Sync governance YAML/model to DataHub. |
| `capture_ui_screenshots.py` | Capture product evidence screenshots. |
| `export_novel_idea_evidence.py` | Export novel-idea evidence. |
| `run_mini_coursework_submission.py` | Assemble mini-coursework submission evidence. |
| `verify-clean-room-setup.sh` | Verify clean-room/reproducible setup. |
| `_rubric_items.py` | Shared Phase 1 rubric definitions. |
| `_phase2_rubric_items.py` | Shared Phase 2 rubric definitions. |

## 9. Config và SQL map

### `configs/`

| File | Tác dụng |
|---|---|
| `collector_config.yaml` | Collector runtime/source settings. |
| `source_mapping.yaml` | Source field → canonical field mapping. |
| `ingestion_manifest.yaml` | Ingestion dataset/source manifest. |
| `schema-contracts.yaml` | Dataset/schema contracts. |
| `dq_rules.yaml` | DQ checks, thresholds, severity. |
| `sector_exclusion.yaml` | Sector filtering policy. |
| `spark_config.yaml` | Local Spark runtime settings. |
| `spark-benchmark.yaml` | Spark benchmark variants. |
| `flink-streaming.yaml` | Flink streaming settings. |
| `flink-restart-probe.yaml` | Flink restart/checkpoint probe. |
| `generator-config.yaml` | Synthetic data generator parameters. |
| `drift-config.yaml` | Drift scenario/threshold parameters. |
| `datahub/governance.yaml` | DataHub datasets, pipelines, contracts, owners. |
| `embedding-backends.yaml` | Embedding backend/model configuration. |
| `rag-sources.yaml` | RAG fixture sources, license, access class, governance allowlist. |
| `phase2-governance.yaml` | Phase 2 governance settings. |
| `rubric-requirements.yaml` | Phase 2 requirement matrix source. |

### `sql/`

| File | Tác dụng |
|---|---|
| `init_project_metadata.sql` | PostgreSQL `project_metadata` DDL. |
| `init_ml_metadata.sql` | Phase 2 `ml_metadata` DDL; không cross-write với Phase 1. |
| `duckdb_create_views.sql` | DuckDB views cho curated lakehouse. |
| `duckdb_validation_queries.sql` | Counts, duplicate, label, PIT validation queries. |
| `schema_evidence.sql` | Schema/ERD evidence query. |
| `postgres-index-benchmark.sql` | PostgreSQL index benchmark query. |

## 10. Web product và shared contracts

### `apps/web/`

| Nhóm | File chính | Tác dụng |
|---|---|---|
| App shell | `src/app/layout.tsx`, `globals.css`, `page.tsx` | Root layout, styling, dashboard home. |
| Company | `src/app/companies/page.tsx`, `companies/[ticker]/page.tsx` | Company list/detail/risk view. |
| Compare | `src/app/compare/page.tsx` | Compare companies. |
| Reports | `src/app/reports/page.tsx`, `reports/[id]/page.tsx` | Report list/detail. |
| Ops | `src/app/ops/evidence/page.tsx` | Evidence/ops surface. |
| Agents | `src/app/agents/registry/page.tsx` | Agent registry surface. |
| Assistant API | `src/app/api/assistant/stream/route.ts` | SSE assistant request path. |
| Assistant components | `src/components/assistant/*` | Launcher, panel, messages, context/provider. |
| Company components | `src/components/company/*` | Risk table, KPI, trends, SHAP, provenance, source list, export. |
| Dashboard components | `src/components/dashboard/*` | Timeline, metrics, risk/sector charts. |
| Ops components | `src/components/ops/*` | Audit, cost, Git revision, agent registry, pipeline, promotion, session state. |
| Shell components | `src/components/shell/*` | Analyst/admin shell, nav, status, disclaimer, user menu. |
| UI primitives | `src/components/ui/*` | Button, card, risk badge, state/trend panels. |
| Data adapters | `src/lib/data/*` | Fixture adapter, Supabase adapter, data port, fixtures. |
| Assistant libs | `src/lib/assistant/*` | Context, SSE/streaming transport. |
| Server libs | `src/lib/server/*` | Budget, guards, inference, session, Supabase, outbox worker/handlers. |
| State libs | `src/lib/states/*` | Loading/route/view state contracts. |
| E2E | `e2e/*.spec.ts`, `e2e/live-env.ts`, `e2e/fake-upstream.mjs` | Accessibility, analyst, assistant, platform and live smoke tests. |
| Tooling | `package.json`, `playwright*.config.ts`, `vitest.config.ts`, `next.config.ts` | Build/test/browser configuration. |

### `packages/contracts/`

| File family | Tác dụng |
|---|---|
| `agent.ts`, `ops.ts`, `company.ts` | Domain contracts for agent/ops/company. |
| `ai-budget.ts`, `assistant-stream.ts` | AI quota and streaming contracts. |
| `authorization.ts`, `role.ts` | RBAC roles and authorization decisions. |
| `disclaimer.ts` | Product disclaimer contract. |
| `outbox-event.ts` | Outbox event schema. |
| `provenance.ts` | Evidence/source provenance. |
| `session-state.ts`, `ui-state.ts`, `session-transitions.json` | UI/session state machine. |
| `index.ts` | Public package exports. |
| `*.test.ts` | Contract-level Vitest tests for every family. |

## 11. Test map — mở test để chứng minh behavior

### Phase 1 tests

| Test file | Chứng minh |
|---|---|
| `test_bronze_to_silver.py`, `test_silver_to_gold.py` | Transform correctness. |
| `test_distress_labels.py` | Z-score-inspired label rules. |
| `test_obt_company_quarter_risk.py` | OBT grain/columns. |
| `test_keys.py`, `test_sector_exclusion.py` | Key and policy contracts. |
| `test_dq_checks.py`, `test_contract_checker.py`, `test_sql_contract_runner.py` | DQ/schema/SQL contracts. |
| `test_streaming.py`, `test_streaming_problem_factory.py`, `test_flink_integration.py` | Kafka/event/Flink contracts. |
| `test_dp1_pipeline.py`, `test_dags_05_smoke.py`, `test_stage1_jobs.py` | DAG/task/runtime wrappers. |
| `test_real_e2e_contracts.py`, `test_runtime_evidence.py` | E2E/evidence contracts without live stack. |
| `test_stage1_quality_gates.py`, `test_stage1_readiness_report.py`, `test_stage1_service_checks.py` | Operational checks. |
| `test_compaction.py`, `test_duckdb_index_demo.py`, `test_storage_optimization_doc.py` | Storage/benchmark evidence. |
| `test_generator_config.py`, `test_generator_characteristics_evidence.py`, `test_fixture_adapter_knobs.py` | Generator/fixture determinism. |
| `test_manifest_adapter.py`, `test_rows_with_schema.py`, `test_schema_contracts.py` | Input/manifest/schema shape. |
| `test_secrets_loader.py`, `test_secrets_no_defaults.py` | Secret loading/no insecure defaults. |
| `test_documentation.py`, `test_readme_polish.py`, `test_module_docstrings.py`, `test_naming_convention.py` | Docs/maintainability conventions. |
| `test_dag_04_naming.py`, `test_dag_06_compaction.py`, `test_dag_06_staging.py`, `test_silver_to_gold_no_wrapper.py` | Specific DAG/transform regressions. |
| `test_deployment_diagram_assets.py` | Architecture image/source assets. |
| `test_rubric_completion_spec.py`, `test_rubric_coverage.py` | Rubric completeness/coverage. |

### Phase 2 tests

| Folder | File family | Chức năng |
|---|---|---|
| `tests/phase2/pipelines/` | `test_data_governance`, `test_phase2_lineage` | Governance/lineage. |
|  | `test_drift_config`, `test_drift_generator` | Drift configuration/scenario. |
|  | `test_label_pipeline` | Label build/persistence. |
|  | `test_feast_definitions_ttl`, `test_feast_smoke` | Feast definitions/runtime. |
|  | `test_embedding_http` | Embedding endpoint contract. |
|  | `test_rag_chunking`, `test_rag_dedup`, `test_rag_metadata_contract` | RAG chunk/hash/governance metadata. |
|  | `test_pgvector_store` | Vector storage/versioning. |
|  | `test_stream_feature_jobs` | Offline/online stream features. |
|  | `test_phase2_dags_import`, `test_workflows_phase2` | Additive DAG import/workflow contracts. |
| `tests/phase2/product/` | `test_rbac_rls`, `test_outbox_worker` | Supabase security/outbox. |
| `tests/phase2/requirements/` | `test_llm_ac_01`…`test_llm_ac_20` | One executable acceptance family per LLM rubric item. |
| `tests/phase2/test_rubric_matrix.py` | Matrix schema/content. |
| `tests/phase2/test_rubric_row_contracts.py` | Rubric row contract. |

To list every test file immediately:

```bash
git ls-files 'tests/**' | sort
```

## 12. Documentation map

### Docs cần đọc theo thứ tự

| Mục tiêu | File |
|---|---|
| Phase 1 source of truth | `docs/mini_coursework.md` |
| Data generator | `docs/01_data_generator.md`, `docs/data-generator.md` |
| Schema/data model | `docs/02_schema_design.md`, `docs/schema-design.md` |
| Data contracts | `docs/07_data_contracts.md` |
| Architecture | `docs/phase1_architecture.md`, `docs/system-architecture.md`, `docs/architecture/repository-map.md` |
| Orchestration | `docs/data-pipeline-orchestration.md` |
| Storage/Spark | `docs/05_storage_optimization.md`, `docs/spark-and-storage-optimization.md` |
| Flink | `docs/flink-stream-processing.md` |
| Governance | `docs/data-governance.md` |
| Docker | `docs/08_docker_optimization.md`, `docs/docker-optimization.md` |
| Novel ideas/PIT | `docs/09_novel_idea_1.md`, `docs/10_novel_idea_2.md`, `docs/novel-idea-pit-leakage-guard.md` |
| Onboarding | `docs/onboarding-presentation-script.md`, `docs/onboarding-stakeholder-deep-dive.md`, `docs/onboarding-presentation-beamer.pdf` |
| Evidence index | `docs/evidence-index.md`, `docs/evidence/README.md` |

### Phase 2 docs

| File/group | Tác dụng |
|---|---|
| `docs/phase2/architecture.md` | Two-plane product/evidence architecture. |
| `docs/phase2/product.md` | Product plane behavior and UI surfaces. |
| `docs/phase2/acceptance-criteria.md`, `requirements.md` | Phase 2 requirements. |
| `docs/phase2/low-level-design.md` | Class/interface/data-flow design. |
| `docs/phase2/evidence-contract.md` | Evidence file contract. |
| `docs/phase2/rubric-matrix.md` | Rubric mapping. |
| `docs/phase2/security/rbac.md` | RBAC/RLS rules. |
| `docs/phase2/adr/adr-001`…`adr-010` | Architecture decisions: gateways, repos, EKS, KServe, Feast, MLflow, Helm/Kustomize, degradation, Nginx, LLM-only scope. |
| `docs/phase2/evidence/llm/` | LLM implementation/evidence notes. |
| `docs/phase2/evidence/product/` | UI/accessibility/product evidence. |

### Generated evidence

Các nhóm sau không cần học thuộc từng leaf file; cần nhớ producer và cách
refresh:

| Path pattern | Nội dung | Producer |
|---|---|---|
| `docs/evidence/stage1_*` | Runtime counts, offsets, MinIO/Postgres/DuckDB summaries. | `scripts/run_stage1_real_e2e.py`, audit scripts |
| `docs/evidence/final/coursework-final-*` | Snapshot submission packages. | submission/evidence scripts |
| `docs/evidence/airflow/`, `flink/`, `spark/` | Runtime benchmark/evidence by platform. | matching runner/audit scripts |
| `docs/evidence/governance/`, `schema/`, `generator/` | Governance/schema/generator artifacts. | matching build/audit scripts |
| `docs/evidence/screenshots/` | Reviewer screenshots. | `scripts/capture_ui_screenshots.py` or runtime capture |
| `docs/phase2/evidence/product/` | Product state/accessibility screenshots and JSON. | web e2e/evidence tooling |

Không hand-edit evidence. Khi cần biết file cụ thể:

```bash
git ls-files 'docs/evidence/**' | sort
git ls-files 'docs/phase2/evidence/**' | sort
```

## 13. Plans và lịch sử triển khai

| Plan folder | Dùng khi cần biết |
|---|---|
| `plans/260721-1033-achieve-mini-coursework-rubric/` | Các phase hoàn thiện rubric Phase 1. |
| `plans/260802-0113-refresh-mini-coursework-evidence-package/` | Refresh/đóng gói evidence Phase 1. |
| `plans/260802-1037-unified-phase2-ml-llm-gitops/` | Ground truth lớn của Phase 2: product, ML, LLM, GitOps. |
| `plans/260805-0800-phase2-stage2-completion/` | Quota, assistant path, outbox, coverage, accessibility. |
| `plans/260806-2234-architecture-hygiene-before-phase-3/` | Dọn architecture/package/container/test markers. |
| `plans/260809-2039-complete-phase2-llm-submission/` | Hoàn thiện submission LLM. |
| `plans/reports/` | Báo cáo/research độc lập, không phải current source of truth. |

Plan là lịch sử quyết định và execution context. Khi có conflict, ưu tiên
`AGENTS.md`, `docs/mini_coursework.md` cho Phase 1 và unified Phase 2 plan khi
task nói rõ Phase 2.

## 14. Local platform và deployment assets

| Path | Tác dụng |
|---|---|
| `docker-compose.yml` | Services: Postgres, MinIO, Kafka, Airflow; Flink là profile opt-in. |
| `infra/airflow/Dockerfile` | Airflow image production-like/local runtime. |
| `infra/airflow/Dockerfile.baseline` | Baseline image cho Docker optimization comparison. |
| `infra/flink/Dockerfile` | Flink image. |
| `infra/kafka/kafka_init_topics.sh` | Create Kafka topics. |
| `infra/phase2/rag-pipeline/Dockerfile` | RAG pipeline image. |
| `infra/phase2/stream-feature-offline/Dockerfile` | Offline feature image. |
| `infra/phase2/stream-feature-online/Dockerfile` | Online feature image. |
| `supabase/config.toml` | Supabase local/project config. |
| `supabase/migrations/*_phase2_schema.sql` | Phase 2 tables. |
| `supabase/migrations/*_phase2_rls.sql` | RLS policies. |
| `supabase/migrations/*_outbox_worker*.sql` | Outbox worker access/schema. |
| `supabase/migrations/*_ai_usage_audit.sql` | AI usage audit persistence. |
| `supabase/migrations/rollback/` | Down migrations for selected Phase 2 changes. |

## 15. Quality gates và câu lệnh mở khi bị hỏi

```bash
# Full definition of done
.venv/bin/python scripts/run_stage1_quality_gates.py

# Narrow Phase 1 test
.venv/bin/python -m pytest tests/test_distress_labels.py -q

# Full Python tests
.venv/bin/python -m pytest tests

# Static checks
.venv/bin/ruff check src dags tests scripts
.venv/bin/black --check src dags tests scripts

# Compose contract, không start service
docker compose config

# Tìm mọi function trong layer liên quan
grep -R -n -E 'def |class ' src/quality src/metadata src/catalog

# Đọc DAG/task chain
grep -R -n -E 'dag_id|>>|PythonOperator|BashOperator' dags
```

## 16. Mẫu trả lời khi được hỏi

Trả lời theo 4 câu, luôn gắn file:

> “Chức năng này thuộc layer **[layer]**. Entrypoint là
> **[file chính]**, logic chi tiết ở **[module]**. Behavior được kiểm chứng ở
> **[test]**, còn contract/architecture nằm ở **[docs/config/SQL]**. Nếu cần
> chạy lại, dùng **[command]**.”

Ví dụ với distress label:

> “Distress label thuộc Gold transform. Entrypoint là
> `src/transforms/compute_distress_labels.py`, được dùng cùng
> `src/transforms/gold/obt_company_quarter_risk.py`. Test là
> `tests/test_distress_labels.py`; schema/rule nằm ở `docs/02_schema_design.md`.
> Có thể chạy `.venv/bin/python -m pytest tests/test_distress_labels.py -q`.”

Ví dụ với stakeholder research:

> “Stakeholder research là Phase 2/product design, không phải live Phase 1
> source. Mở `docs/onboarding-stakeholder-deep-dive.md` để nói domain model,
> provenance, review và conflict; mở `src/llm/rag_pipeline.py` nếu câu hỏi
> chuyển sang document/RAG ingestion; mở `apps/web/src/components/company/provenance-panel.tsx`
> nếu câu hỏi chuyển sang product UI.”

## 17. Cập nhật bản đồ

Map này được kiểm tra theo file tracked:

```bash
git ls-files | wc -l
git ls-files src dags scripts tests configs sql apps packages supabase | sort
```

Khi thêm module mới, cập nhật đúng ba nơi: **entrypoint lookup**, **file catalog**
và **test/command chứng minh**. Không đưa cache, virtualenv, `node_modules`,
bytecode, `warehouse.db` hay output tạm vào danh sách học thuộc.
