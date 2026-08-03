# Phase 1 Architecture Overview: Financial Distress Data Engineering System

Tài liệu này là bản tả chi tiết (As-Built Specification) về toàn bộ kiến trúc, hạ tầng, luồng xử lý dữ liệu, Data Contracts, kiểm soát chất lượng (DQ), và quản trị Operational Metadata của **Phase 1 (Stage 1 Local-First Lakehouse)** thuộc hệ thống phân tích kiệt quệ tài chính (Financial Distress Analytics System) cho các doanh nghiệp niêm yết tại Việt Nam, đồng thời trình bày **Định hướng Kiến trúc Tổng thể của Phase 2** (Machine Learning, Agentic RAG & Cloud Evidence Plane).

---

## 1. Nguồn Gốc Quy Chuẩn & Tài Liệu Tham Chiếu (Source of Truth)

Mọi thiết kế và mã nguồn trong Phase 1 tuân thủ thứ tự ưu tiên pháp lý hệ thống sau đây:

1. [AGENTS.md](../AGENTS.md): Hiến pháp nguyên tắc hoạt động và ranh giới local-first.
2. [mini_coursework.md](mini_coursework.md): Spec kỹ thuật chi tiết làm căn cứ hiện thực hóa Phase 1.
3. [01_data_generator.md](01_data_generator.md): Spec chi tiết về nguồn thu thập dữ liệu batch/streaming và bộ sinh dữ liệu mẫu.
4. [02_schema_design.md](02_schema_design.md): Spec chi tiết về thiết kế Schema Medallion (Bronze/Silver/Gold), Data Quality rules, Metadata schema và DuckDB SQL contracts.
5. [05_storage_optimization.md](05_storage_optimization.md): Chiến lược định dạng dữ liệu Parquet, phân vùng (Partitioning) và tối ưu hóa bộ nhớ Lakehouse.
6. [07_data_contracts.md](07_data_contracts.md): Quy ước chi tiết Data Contracts giữa các tầng dữ liệu.
7. [08_docker_optimization.md](08_docker_optimization.md): Cấu hình cụm Docker local tối ưu tài nguyên CPU/RAM.
8. [11_rubric_completion_spec.md](11_rubric_completion_spec.md): Tiêu chí hoàn thành 100% yêu cầu đồ án Phase 1.

---

## 2. Triết Lý Thiết Kế Cốt Lõi (Architecture Principles)

### 2.1. Local-First & Cloud-Free Boundary
Phase 1 được giới hạn nghiêm ngặt trong môi trường **Local-First**, không sử dụng bất kỳ dịch vụ đám mây tính phí nào (như AWS S3, RDS, Glue, Athena, Redshift, EMR, MSK hay Kubernetes):
* Sử dụng **MinIO** thay thế cho AWS S3 với S3A connector (`s3a://financial-distress-lake/`).
* Sử dụng **PostgreSQL** chạy trong Docker làm cơ sở dữ liệu Operational Metadata (schema `project_metadata`).
* Sử dụng **Apache Kafka** (single-node KRaft) làm Streaming Broker local.
* Sử dụng **PySpark Local Mode** làm engine xử lý dữ liệu lớn (Spark DataFrame API).
* Sử dụng **DuckDB `httpfs`** làm SQL engine truy vấn trực tiếp file Parquet trên MinIO thông qua **DBeaver**.

### 2.2. Kiến Trúc Kép Dual-Mode (Dual-Mode Architecture)
Hệ thống được thiết kế độc đáo với 2 chế độ vận hành độc lập nhưng dùng chung toàn bộ mã nguồn xử lý logic:

```text
                               +---------------------------------------+
                               |     Dual-Mode System Architecture     |
                               +-------------------+-------------------+
                                                   |
                     +-----------------------------+-----------------------------+
                     |                                                           |
                     v                                                           v
  +-------------------------------------+                     +-------------------------------------+
  |   1. IN-MEMORY VALIDATION MODE      |                     |   2. LIVE LOCAL LAKEHOUSE MODE      |
  |  (Offline / CI Test Execution)      |                     |  (Local Docker Services Cluster)    |
  | - Fast execution (< 3s)             |                     | - Airflow DAG Orchestration         |
  | - Pure Python & Deterministic       |                     | - Kafka KRaft Event Streaming       |
  | - VnstockFixtureAdapter             |                     | - MinIO S3 Parquet Bronze/Silver/Gold|
  | - PostgresMetadataWriter RAM mock   |                     | - PySpark DataFrame Distributed Jobs|
  | - 100% PyTest Contract Coverage     |                     | - Postgres project_metadata Schema  |
  | - Zero External Dependencies        |                     | - DuckDB httpfs & DBeaver Inspection|
  +-------------------------------------+                     +-------------------------------------+
```

1. **In-Memory Validation Mode (Fast CI/CD)**:
   * Cho phép chạy toàn bộ logic kiểm tra hợp đồng, chuyển đổi dữ liệu, tính chỉ số Z-score, khử trùng lặp và gán nhãn trong bộ nhớ RAM mà không cần khởi động bất kỳ Docker container nào.
   * Đạt 100% test coverage với **464 PyTest tests** hoàn thành chỉ trong ~2.3 giây.
2. **Live Local Lakehouse Mode (Docker Execution)**:
   * Khởi chạy cụm container thực tế định nghĩa trong [docker-compose.yml](../docker-compose.yml).
   * Airflow điều phối các tác vụ batch và stream end-to-end, ghi nhận toàn bộ log thực thi vào PostgreSQL và sinh dữ liệu Parquet chuẩn trên MinIO.

---

## 3. Sơ Đồ Kiến Trúc Luồng Dữ Liệu Chi Tiết (Detailed Data Pipeline Architecture)

Below is the execution flow map from raw sources to reviewer inspection:

```text
+-------------------------------------------------------------------------------------------------------+
|                                        1. SOURCE ADAPTERS & GENERATOR                                 |
|                                                                                                       |
|  [Source Protocol] -------------> [VnstockFixtureAdapter] -----------> [Rubric Problem Generator]     |
|  (base.py)                        (vnstock_fixture_adapter.py)         (problem_factory.py)           |
|                                                                                                       |
|  Generates: Company Master | Financial Statements | Market Prices Daily | Trading News & Alert Events |
+------------------------------------+------------------------------------+-----------------------------+
                                     |                                    |
            +------------------------+                                    +------------------------+
            | (Batch Records)                                                                          | (Streaming Events)
            v                                                                                          v
+----------------------------------------+                                +----------------------------------------+
| 2A. BATCH INGESTION (AIRFLOW DAGS)     |                                | 2B. STREAMING INGESTION (KAFKA KRAFT)  |
| - 01_collect_company_master_data.py    |                                | - Kafka Producer (kafka_producer.py)   |
| - 02_collect_financial_statement_api.py|                                |   Topics: financial.price_events       |
| - 03_collect_market_price_api.py       |                                |           news_events, alert_events    |
| - stage1_real_e2e_pipeline.py          |                                | - MicroBatchConsumer                   |
+-------------------+--------------------+                                |   (kafka_to_bronze_consumer.py)        |
                    |                                                     +-------------------+--------------------+
                    |                                                                         |
                    +----------------------------------+--------------------------------------+
                                                       |
                                                       v
+-------------------------------------------------------------------------------------------------------+
|                                3. MINIO LOCAL S3 LAKEHOUSE STORAGE                                    |
|                                 s3a://financial-distress-lake/                                        |
|                                                                                                       |
|  ├── raw/   (BRONZE)  : raw_companies/ | raw_financial_statements/ | raw_market_prices/ | events/    |
|  │          Metadata  : ingest_ts, batch_id, raw_payload (Parquet)                                    |
|  │                                                                                                    |
|  ├── silver/(SILVER)  : dim_company/ | fact_financial_statement/ | fact_market_price/               |
|  │          Metadata  : Cleaned, typed, deduplicated by business_key + max(created_ts)               |
|  │                                                                                                    |
|  └── gold/  (GOLD)    : dim_company_gold/ | fact_financial_ratios/ | fact_distress_labels/         |
|             Metadata  : Altman Z''-Score, 5 Warning Rules, One Big Table (OBT), Feature Tables        |
+------------------------------------------------------+------------------------------------------------+
                                                       |
                                                       v
+-------------------------------------------------------------------------------------------------------+
|                              4. PYSPARK PROCESSING & TRANSFORMATION ENGINE                            |
|                                         (spark_session.py)                                            |
|                                                                                                       |
|  - Bronze -> Silver Transform (bronze_to_silver.py):                                                  |
|    Schema Enforcement + Data Cleaning + Window Deduplication                                          |
|  - Silver -> Gold Transform (silver_to_gold.py & compute_distress_labels.py):                          |
|    Partitioned Fact/Dim Construction + Idempotent Overwrite + Altman Z''-Score + Financial Exclusion  |
+------------------------------------+------------------------------------+-----------------------------+
                                     |                                    |
        +----------------------------+                                    +----------------------------+
        |                                                                                              |
        v                                                                                              v
+--------------------------------------------------+       +--------------------------------------------------+
| 5. OPERATIONAL METADATA GOVERNANCE (POSTGRESQL)  |       | 6. DUCKDB & DBEAVER LOCAL INSPECTION SURFACE     |
| Database: postgres | Schema: project_metadata     |       | Engine: DuckDB httpfs Direct MinIO Reader        |
| File DDL: init_project_metadata.sql              |       | File SQL: duckdb_create_views.sql                |
| Client  : postgres_writer.py                     |       | Runner  : duckdb_runner.py                       |
|                                                  |       |                                                  |
| Tables:                                          |       | Registered Views:                                |
|  - pipeline_run_log     (DAG Run Metrics)        |       |  - v_gold_company_dim                            |
|  - data_quality_result  (DQ Check Results)       |       |  - v_gold_financial_ratios                       |
|  - failed_records       (Soft-Fail Isolation)    |       |  - v_gold_distress_labels                        |
|  - schema_version_log   (Schema Contracts)       |       |  - v_gold_obt_financial_distress                 |
+--------------------------------------------------+       +--------------------------------------------------+
```

---

## 4. Chi Tiết Các Component Và File Mã Nguồn (Detailed Component Breakdown)

### 4.1. Tầng Thu Nhập Dữ Liệu & Source Adapters (Data Collectors)

Nằm trong thư mục `src/collectors/`:

* [base.py](../src/collectors/source_adapters/base.py): Định nghĩa lớp cơ sở `BaseSourceAdapter` quy định giao thức chuẩn cho mọi adapter (phương thức `fetch_companies`, `fetch_financial_statements`, `fetch_market_prices`).
* [vnstock_fixture_adapter.py](../src/collectors/source_adapters/vnstock_fixture_adapter.py): Adapter chính của Phase 1. Sinh dữ liệu giả lập có tính toán toán học chính xác (deterministic) cho các công ty niêm yết (VNM, VIC, HPG, FPT, TCB, VCB, MSN, VHM...). Đảm bảo dữ liệu nhất quán qua mỗi lần chạy test mà không cần truy cập internet.
* [company_list_collector.py](../src/collectors/company_list_collector.py): Collector chịu trách nhiệm thu thập thông tin danh sách doanh nghiệp (Ticker, Company Name, Exchange, Industry, Sector, Listing Date).
* [financial_statement_collector.py](../src/collectors/financial_statement_collector.py): Collector thu thập Báo cáo tài chính hợp nhất theo quý (Bảng cân đối kế toán, Báo cáo kết quả kinh doanh, Báo cáo lưu chuyển tiền tệ).
* [market_price_collector.py](../src/collectors/market_price_collector.py): Collector thu thập dữ liệu giá và khối lượng giao dịch hàng ngày (OHLCV, Market Cap, Shares Outstanding).
* [streaming_problem_factory.py](../src/generators/streaming_problem_factory.py): Bộ sinh dữ liệu kiểm thử theo rubric bài tập, hỗ trợ tạo các kịch bản lỗi dữ liệu ngẫu nhiên để kiểm tra sức chịu đựng của Data Quality Engine.

Cấu hình nguồn thu thập được lưu trữ tại [collector_config.yaml](../configs/collector_config.yaml) và [source_mapping.yaml](../configs/source_mapping.yaml).

---

### 4.2. Tầng Real-Time Streaming & Kafka Consumer

Nằm trong thư mục `src/streaming/`:

* [events.py](../src/streaming/events.py): Định nghĩa các Dataclass hợp đồng sự kiện real-time:
  * `MarketPriceEvent`: Sự kiện giá cổ phiếu nhảy theo từng tick.
  * `NewsEvent`: Sự kiện tin tức doanh nghiệp (tiêu đề, nội dung, sentiment, timestamp).
  * `AlertEvent`: Sự kiện cảnh báo rủi ro (giao dịch bất thường, biến động giá mạnh).
* [kafka_producer.py](../src/streaming/kafka_producer.py): Wrapper đẩy các sự kiện dữ liệu vào Kafka Broker (`localhost:9092`).
* [kafka_to_bronze_consumer.py](../src/streaming/kafka_to_bronze_consumer.py): Micro-batch Consumer đệm (buffer) các sự kiện từ Kafka topic, thực hiện gom nhóm theo giờ/ngày và ghi xuống tầng Bronze Parquet trên MinIO.

---

### 4.3. Tầng Xử Lý & Biến Đổi Dữ Liệu Medallion (PySpark Transformation Engine)

Nằm trong thư mục `src/transforms/`:

* [spark_session.py](../src/transforms/spark_session.py): Đảm bảo khởi tạo `SparkSession` tối ưu với các tham số S3A client kết nối MinIO local (`http://minio:9000`), cài đặt các cấu hình lưu trữ Parquet tại [spark_config.yaml](../configs/spark_config.yaml).
* [keys.py](../src/transforms/keys.py): Định nghĩa các Business Keys duy nhất cho từng Dataset (VD: `['ticker']` cho Company, `['ticker', 'fiscal_year', 'fiscal_quarter']` cho Financial Statements).
* [sector_policy.py](../src/transforms/sector_policy.py): Quy định danh sách các mã ngành tài chính đặc thù (Bank, Insurance, Securities) bị loại trừ khỏi mô hình tính Altman Z''-Score.

#### A. Bronze to Silver Transformation
File mã nguồn: [bronze_to_silver.py](../src/transforms/bronze_to_silver.py).
* Thực hiện ép kiểu dữ liệu chặt chẽ theo Data Schema Registry tại [schema_registry.py](../src/metadata/schema_registry.py).
* Thuật toán Khử trùng lặp (Deduplication):
  ```python
  window_spec = Window.partitionBy(business_keys).orderBy(col("created_ts").desc())
  silver_df = bronze_df.withColumn("row_num", row_number().over(window_spec)) \
                       .filter(col("row_num") == 1) \
                       .drop("row_num")
  ```

#### B. Silver to Gold Transformation & Distress Label Calculation
File mã nguồn: [silver_to_gold.py](../src/transforms/silver_to_gold.py) và [compute_distress_labels.py](../src/transforms/compute_distress_labels.py).

* **Công thức chỉ số Altman Z''-Score (Non-Manufacturing & Emerging Markets)**:
  $$\text{Working Capital} = \text{Current Assets} - \text{Current Liabilities}$$
  $$X_1 = \frac{\text{Working Capital}}{\text{Total Assets}}, \quad X_2 = \frac{\text{Retained Earnings}}{\text{Total Assets}}$$
  $$X_3 = \frac{\text{EBIT}}{\text{Total Assets}}, \quad X_4 = \frac{\text{Book Value of Equity}}{\text{Total Liabilities}}$$
  $$Z'' = 6.56 X_1 + 3.26 X_2 + 6.72 X_3 + 1.05 X_4$$

* **Phân loại Vùng Rủi ro Z''-Score**:
  * $Z'' > 2.90$: Safe Zone (An toàn).
  * $1.23 \le Z'' \le 2.90$: Grey Zone (Cảnh báo / Vùng xám).
  * $Z'' < 1.23$: Distress Zone (Rủi ro kiệt quệ tài chính cao).

* **5 Quy tắc Proxy Warning Rules**:
  1. `high_debt_to_asset`: $\frac{\text{Total Liabilities}}{\text{Total Assets}} > 0.8$.
  2. `low_current_ratio`: $\frac{\text{Current Assets}}{\text{Current Liabilities}} < 1.0$.
  3. `two_quarter_net_loss`: Lợi nhuận ròng $\text{Net Income} < 0$ trong cả 2 quý liên tiếp.
  4. `negative_equity`: Vốn chủ sở hữu $\text{Equity} < 0$.
  5. `weak_interest_coverage`: $\frac{\text{EBIT}}{\text{Interest Expense}} < 1.0$.

* **Tính Idempotent (Idempotent Write Helper)**:
  Ghi file Parquet ở tầng Gold sử dụng PySpark mode `overwrite` cho các partition liên quan, đảm bảo nếu chạy lại DAG nhiều lần kết quả vẫn hoàn toàn nhất quán mà không bị nhân bản bản ghi.

---

### 4.4. Tầng Kiểm Soát Chất Lượng Dữ Liệu (Data Quality Engine)

Nằm trong thư mục `src/quality/`:

* [contract_checker.py](../src/quality/contract_checker.py): Engine kiểm tra hợp đồng cấu trúc cột và kiểu dữ liệu của các DataFrame đầu vào.
* [dq_checks.py](../src/quality/dq_checks.py): Thực thi các quy tắc kiểm tra Data Quality theo định nghĩa YAML [dq_rules.yaml](../configs/dq_rules.yaml).
* [dq_runner.py](../src/quality/dq_runner.py): Runner tổng hợp chạy toàn bộ kiểm tra DQ cho một batch và trả về danh sách kết quả.

**Cơ chế Phân loại Lỗi**:
* **Hard-Fail**: Lỗi vi phạm nghiêm trọng (VD: `null` ở khóa chính `ticker`, thiếu cột bắt buộc, lỗi kiểu dữ liệu). Xử lý: **Ngắt pipeline ngay lập tức**, báo lỗi lên Airflow.
* **Soft-Fail**: Lỗi bất thường dữ liệu (VD: `total_assets < 0`, `current_ratio` bất thường). Xử lý: Tách các dòng vi phạm ghi vào bảng `project_metadata.failed_records` trên PostgreSQL, các dòng hợp lệ tiếp tục chảy sang tầng Gold.

---

### 4.5. Tầng Quản Trị Operational Metadata & Governance (PostgreSQL)

Nằm trong thư mục `src/metadata/` và `sql/`:

* [schema_registry.py](../src/metadata/schema_registry.py): Registry tập trung chứa Data Schemas (PySpark StructType & Python Dict) cho toàn bộ các bảng trong hệ thống.
* [metadata_writer.py](../src/metadata/metadata_writer.py): Client ghi log hoạt động hệ thống. Hỗ trợ cả `PostgresMetadataWriter` (kết nối PostgreSQL thật qua `psycopg2`) và `InMemoryMetadataWriter` (RAM mock cho unit tests).
* [init_project_metadata.sql](../sql/init_project_metadata.sql): DDL khởi tạo schema `project_metadata` trên PostgreSQL local.

#### Các Bảng Metadata Chính trên PostgreSQL:
```sql
-- 1. Bảng ghi log các lần chạy Pipeline / Airflow DAG
CREATE TABLE project_metadata.pipeline_run_log (
    run_id VARCHAR(64) PRIMARY KEY,
    dag_id VARCHAR(128) NOT NULL,
    execution_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(32) NOT NULL,
    records_processed INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Bảng ghi kết quả Data Quality Checks
CREATE TABLE project_metadata.data_quality_result (
    check_id VARCHAR(64) PRIMARY KEY,
    run_id VARCHAR(64) REFERENCES project_metadata.pipeline_run_log(run_id),
    table_name VARCHAR(128) NOT NULL,
    rule_name VARCHAR(128) NOT NULL,
    status VARCHAR(16) NOT NULL, -- PASSED, WARN, FAILED
    failed_count INT DEFAULT 0,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Bảng cách ly các bản ghi lỗi (Soft-fail Isolation)
CREATE TABLE project_metadata.failed_records (
    record_id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) REFERENCES project_metadata.pipeline_run_log(run_id),
    table_name VARCHAR(128) NOT NULL,
    rule_name VARCHAR(128) NOT NULL,
    raw_payload JSONB NOT NULL,
    failed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

### 4.6. Tầng DuckDB & DBeaver Inspection Surface

Nằm trong thư mục `src/catalog/` và `sql/`:

* [duckdb_catalog.py](../src/catalog/duckdb_catalog.py): Helper tạo mã SQL đăng ký các view DuckDB đọc trực tiếp Parquet từ MinIO local.
* [duckdb_runner.py](../src/catalog/duckdb_runner.py): Runner kết nối DuckDB, load extension `httpfs`, cài đặt S3 credentials của MinIO và thực thi file DDL view.
* [duckdb_create_views.sql](../sql/duckdb_create_views.sql): DDL tạo các View SQL phản chiếu tầng Gold dữ liệu.
* [duckdb_validation_queries.sql](../sql/duckdb_validation_queries.sql): Các câu lệnh SQL mẫu phục vụ kiểm tra và chụp ảnh minh chứng trên DBeaver.

---

### 4.7. Danh Sách Các Airflow DAGs (Orchestration Layer)

Nằm trong thư mục `dags/`:

* [01_collect_company_master_data.py](../dags/01_collect_company_master_data.py): DAG thu thập thông tin danh sách doanh nghiệp niêm yết.
* [02_collect_financial_statement_api.py](../dags/02_collect_financial_statement_api.py): DAG thu thập Báo cáo tài chính theo quý.
* [03_collect_market_price_api.py](../dags/03_collect_market_price_api.py): DAG thu thập giá thị trường hàng ngày.
* [dag_04_stream_market_events_to_kafka.py](../dags/dag_04_stream_market_events_to_kafka.py): DAG mô phỏng stream sự kiện giá/tin tức vào Kafka topic.
* [05_transform_bronze_to_silver.py](../dags/05_transform_bronze_to_silver.py): DAG khởi chạy Spark job làm sạch và khử trùng lặp dữ liệu Bronze -> Silver.
* [06_pyspark_silver_to_gold.py](../dags/06_pyspark_silver_to_gold.py): DAG khởi chạy Spark job tính chỉ số Z-score, rủi ro kiệt quệ và tạo bảng Gold.
* [07_run_data_quality_checks.py](../dags/07_run_data_quality_checks.py): DAG kiểm tra chất lượng DQ toàn hệ thống.
* [08_minio_duckdb_register_tables.py](../dags/08_minio_duckdb_register_tables.py): DAG tự động cập nhật SQL views trên DuckDB.
* [09_data_governance.py](../dags/09_data_governance.py): DAG đồng bộ dữ liệu quản trị metadata.
* [stage1_local_evidence_pipeline.py](../dags/stage1_local_evidence_pipeline.py): DAG kiểm thử nhẹ sinh evidence nhanh cho môi trường CI.
* [stage1_real_e2e_pipeline.py](../dags/stage1_real_e2e_pipeline.py): **DAG E2E Cốt Lõi**, kết nối toàn bộ luồng thu thập $\rightarrow$ Kafka $\rightarrow$ MinIO $\rightarrow$ PySpark $\rightarrow$ Postgres $\rightarrow$ DuckDB.

---

### 4.8. Các Script Kiểm Tra & Audit Hệ Thống (Audit & Readiness Scripts)

Nằm trong thư mục `scripts/`:

* [run_stage1_real_e2e.py](../scripts/run_stage1_real_e2e.py): Script kích hoạt và theo dõi việc chạy DAG E2E thực tế trên Airflow Docker.
* [check_stage1_services.py](../scripts/check_stage1_services.py): Kiểm tra độ sẵn sàng (Healthcheck) của các dịch vụ Docker (Airflow, MinIO, Postgres, Kafka).
* [run_stage1_quality_gates.py](../scripts/run_stage1_quality_gates.py): Chạy Quality Gate kiểm tra 100% hợp đồng dữ liệu trước khi xuất bằng chứng.
* [run_stage1_dq_failure_probe.py](../scripts/run_stage1_dq_failure_probe.py): Script cố tình bơm dữ liệu lỗi để kiểm chứng tính năng Soft-fail cách ly vào `failed_records`.
* [stage1_readiness_report.py](../scripts/stage1_readiness_report.py): Xuất báo cáo tổng quan độ sẵn sàng của Phase 1 cho Reviewer.
* [audit_stage1_evidence.py](../scripts/audit_stage1_evidence.py): Đọc và thẩm định toàn bộ file minh chứng trong thư mục [docs/evidence/](evidence/).

---

## 5. Quy Trình Chống Rò Rỉ Dữ Liệu Theo Thời Gian (Point-In-Time Leakage Guard)

Trong bài toán kiệt quệ tài chính, rò rỉ dữ liệu tương lai (Look-ahead Bias / Point-In-Time Leakage) là lỗi nghiêm trọng làm hỏng mô hình Machine Learning. Hệ thống Phase 1 áp dụng quy tắc quản lý mốc thời gian nghiêm ngặt:

```text
  [Biến động thị trường / Tin tức] -------------> event_timestamp (Timestamp sự kiện)
  [Báo cáo tài chính Quý N] --------------------> report_release_date (Ngày công bố)

  QUY TẮC JOIN TÍNH NĂNG (FEATURE JOIN RULE):
  Feature_Market_Price.event_timestamp <= Financial_Statement.report_release_date
```

* **Không dùng ngày kết thúc quý**: Báo cáo tài chính quý 4 kết thúc ngày 31/12, nhưng thường chỉ được công bố công khai vào ngày 30/01 năm sau (`report_release_date`).
* Khi kết nối dữ liệu thị trường (như giá đóng cửa, vốn hóa) để giải thích cho Báo cáo tài chính đó, PySpark tuyệt đối không lấy dữ liệu thị trường phát sinh **sau** ngày `report_release_date`.

---

## 6. Ma Trận Nghiệm Thu & Minh Chứng Hoàn Thành (Acceptance & Evidence Matrix)

Toàn bộ minh chứng thực thi Phase 1 được lưu trữ tại [docs/evidence/](evidence/) và tài liệu chỉ mục [evidence-index.md](evidence-index.md).

| Hạng mục kiểm tra | Định dạng Evidence | Tiêu chí nghiệm thu (WHO -> ACTION -> RESULT) |
|---|---|---|
| **PyTest Test Suite** | 464 Passed Tests | `Developer -> runs pytest -> 464 tests pass in < 3s` |
| **Local Services** | Healthcheck Logs | `Airflow/Kafka/MinIO/Postgres -> startup -> All services healthy` |
| **Real E2E Pipeline** | `stage1_real_airflow_dag_test.txt` | `Airflow -> triggers E2E DAG -> Execution SUCCESS` |
| **Bronze/Silver/Gold Parquet**| `stage1_real_minio_objects.json` | `PySpark -> writes to MinIO -> Parquet files partitioned correctly` |
| **PostgreSQL Metadata** | `stage1_real_postgres_summary.json`| `PostgresMetadataWriter -> writes run logs & DQ -> PostgreSQL populated` |
| **DQ Failure Probe** | `stage1_dq_failure_probe.json` | `DQ Engine -> catches invalid row -> Isolates row to failed_records` |
| **DuckDB Validation** | `stage1_real_duckdb_validation.json`| `DuckDB -> queries MinIO Parquet -> Views yield correct query results` |

---

## 7. Kết Luận Sẵn Sàng Cho Phase 2

Hệ thống Phase 1 đã hoàn thành xuất sắc 100% các tiêu chí Data Engineering Lakehouse. Kiến trúc Phase 1 là một nền tảng **bất biến và đáng tin cậy** (Immutable Data Foundation). 

Nền tảng Gold Parquet trên MinIO sẽ đóng vai trò là nguồn cấp Feature Store đạt chuẩn cho việc huấn luyện mô hình Machine Learning, Agentic RAG và Drift Monitoring ở Phase 2.

---

## 8. Định Hướng Kiến Trúc Tổng Thể Phase 2 (Phase 2 Architectural Vision & Intent)

Tài liệu thiết kế gốc cho Phase 2 được lưu trữ tại [phase2/architecture.md](phase2/architecture.md) và [phase2/requirements.md](phase2/requirements.md). Phase 2 xây dựng một hệ thống Machine Learning, Agentic RAG Assistant và Drift Monitoring hoàn chỉnh dựa trên nền tảng Lakehouse Phase 1.

### 8.1. Mô Hình Kiến Trúc 2 Mặt Phẳng (Two-Plane Architecture Model)

Nhằm tối ưu hóa chi phí vận hành đám mây, Phase 2 áp dụng mô hình thiết kế **Two-Plane Architecture**:

```text
+-------------------------------------------------------------------------------------------------------+
|                                    1. PRODUCT PLANE (PERSISTENT & LOW-COST)                           |
|   - Always Available | Cost: ~0 USD/month | Free Tier Services                                        |
|                                                                                                       |
|   ┌───────────────────────────┐         ┌───────────────────────────┐         ┌────────────────────┐ │
|   │ Next.js Web App (Vercel)  │ <-----> │ Supabase Auth & PostgreSQL│ <-----> │ Evidence Worker    │ │
|   │ (Persisted Analyst UI)    │         │ (RLS & State Machine OFF) │         │ (Outbox Consumer)  │ │
|   └───────────────────────────┘         └───────────────────────────┘         └────────────────────┘ │
+---------------------------------------------------+---------------------------------------------------+
                                                    |
                                                    | (Operator triggers Provision Session via GitOps)
                                                    v
+-------------------------------------------------------------------------------------------------------+
|                                  2. EVIDENCE PLANE (DISPOSABLE & BOUNDED BUDGET)                      |
|   - Ephemeral AWS EKS Cluster (ap-southeast-1) | Spot Instances | Hard TTL: 8 Hours                      |
|   - Strict Budget Envelope: <= 25 USD/session | <= 10 USD/month persistent | <= 3 sessions/month        |
|                                                                                                       |
|  [NGINX Ingress Edge] -> [Istio Service Mesh] -> [agentgateway] -> [Envoy AI Gateway & KServe]        |
|                                                                                                       |
|  ├── Feature Store    : Feast (Offline: S3 Parquet | Online: Valkey / PGVector)                      |
|  ├── Model Training   : Kubeflow Pipelines + Kubeflow Trainer (XGBoost Distributed)                   |
|  ├── Model Registry   : MLflow Registry (Owned Helm Chart + S3 Artifacts + Postgres Backend)           |
|  ├── Model Serving    : KServe 0.18 (InferenceService for ML | LLMInferenceService for Qwen3-4B)        |
|  ├── Agentic RAG      : Coordinator Agent + Specialist Agents (Feature Analyst & Drift Analyst)       |
|  ├── Data Drift API   : drift-api (FastAPI + Evidently AI Metrics)                                    |
|  ├── GitOps CD        : Argo CD + Terraform + CodeBuild (Auto-Teardown via EventBridge Hard TTL)     |
|  └── Observability    : Prometheus / Grafana + OpenTelemetry / Jaeger + ECK Kibana                    |
+-------------------------------------------------------------------------------------------------------+
```

---

### 8.2. Bốn Tầng Điều Phối Giao Thông (Four Traffic Layers)

1. **NGINX Ingress Controller**: Cổng rìa public tiếp nhận kết nối TLS Termination từ người dùng bên ngoài.
2. **Istio Service Mesh**: Tầng bảo mật mạng nội bộ East-West với chứng chỉ mTLS tự động và phân quyền Authorization Policy giữa các Microservices trong Kubernetes.
3. **agentgateway**: Tầng trung gian điều phối và định tuyến các giao thức giao tiếp giữa các AI Agent (Agent-to-Agent - A2A) và giao thức công cụ mô hình (Model Context Protocol - MCP).
4. **Envoy Gateway + Envoy AI Gateway**: Cổng AI chuyên dụng xử lý định tuyến, giới hạn tốc độ (rate limiting), và retry cho các yêu cầu sinh ngôn ngữ gửi tới `LLMInferenceService` của KServe.

---

### 8.3. Mô Tả Chi Tiết Chức Năng Từng Thành Phần Trong Phase 2

#### A. Tầng Quản Lý Tính Năng & Feature Store (Feast Feature Store)
* **Chức năng**: Quản lý nhất quán các tính năng (features) từ khâu huấn luyện đến suy luận online, ngăn ngừa Feature Drift.
* **Offline Store (MinIO/S3 Parquet)**: Trích xuất lịch sử tính năng từ bảng Gold của Phase 1 để tạo các tập dữ liệu huấn luyện (Training Datasets) có kiểm soát Point-in-Time.
* **Online Store (Valkey / PostgreSQL PGVector)**: Lưu giữ các tính năng mới nhất theo mã `ticker` với độ trễ truy vấn cực thấp ($< 10\text{ms}$) phục vụ KServe suy luận real-time.

#### B. Tầng Huấn Luyện & Quản Lý Mô Hình (Kubeflow + MLflow)
* **Kubeflow Pipelines & Kubeflow Trainer**: Tự động hóa pipeline huấn luyện các mô hình Machine Learning (phân loại rủi ro kiệt quệ tài chính bằng thuật toán XGBoost/LightGBM phân tán).
* **MLflow Model Registry**: Lưu trữ các phiên bản mô hình (Model Versioning), chỉ số đánh giá (ROC-AUC, F1-Score, Confusion Matrix), artifact weights, và phát tín hiệu cho Promotion Bot mở PR tự động nâng cấp mô hình.

#### C. Tầng Phục Vụ Mô Hình & Suy Luận (KServe 0.18 Inference Engine)
* **KServe `InferenceService`**: Phục vụ mô hình ML XGBoost dự báo điểm rủi ro kiệt quệ tài chính (Distress Risk Score). Hỗ trợ tự động co giãn Pods (Autoscaling) qua KEDA/HPA.
* **KServe `LLMInferenceService`**: Phục vụ mô hình ngôn ngữ lớn tùy chỉnh (như Qwen3-4B) cho tác vụ phân tích tài chính sâu và giải thích nguyên nhân rủi ro.

#### D. Tầng Trợ Lý AI Multi-Agent & RAG (Agentic AI System)
Hệ thống AI Assistant phân tích tài chính được thiết kế theo kiến trúc Multi-Agent phối hợp:
* **Coordinator Agent**: Agent điều phối trung tâm tiếp nhận yêu cầu (Prompt) của nhà phân tích, chia nhỏ bài toán và giao việc cho các Agent chuyên môn.
* **Feature Analyst Agent**: Agent chuyên sâu phân tích báo cáo tài chính và chỉ số Z-score. Nhận việc từ Coordinator và gọi công cụ **MCP Feast Tool** để lấy dữ liệu tính năng từ Feature Store.
* **Drift Analyst Agent**: Agent chuyên sâu kiểm tra biến động dữ liệu. Nhận việc từ Coordinator và gọi công cụ **MCP Drift Tool** để truy vấn thông số trôi dạt từ `drift-api`.
* **Model Context Protocol (MCP) Tools**: Đóng vai trò là cổng nối bảo mật giữa các Specialist Agents và hệ thống dữ liệu. Tools truy vấn dữ liệu từ Feast/RAG vector DB và `drift-api`, tuyệt đối không gọi ngược lại Agent.

#### E. Tầng Theo Dõi Trôi Dạt Dữ Liệu & Mô Hình (`drift-api`)
* **Chức năng**: Xây dựng dưới dạng FastAPI service (`src/drift/`), theo dõi sự trôi dạt phân phối dữ liệu đầu vào (Data Drift) và sự sụt giảm hiệu năng mô hình theo thời gian (Concept Drift) dựa trên các thuật toán Kolmogorov-Smirnov test và PSI (Population Stability Index).

#### F. Tầng Quản Trị Triển Khai GitOps & Tự Hủy Chi Phí (GitOps & Auto-Teardown)
* **Repository GitOps riêng biệt (`financial-distress-gitops`)**: Chứa toàn bộ khai báo hạ tầng IaC (Terraform, Helm, Kustomize, Argo CD).
* **Argo CD**: Tự động đồng bộ cấu hình từ GitOps repo lên EKS Evidence Plane.
* **EventBridge Scheduler & CodeBuild (Hard-TTL Auto-Teardown)**: 
  * Để đảm bảo không vượt quá ngân sách ($\le 25\text{ USD/phiên}$), EventBridge Scheduler thiết lập đếm ngược Hard TTL (tối đa 8 tiếng).
  * Khi hết giờ, EventBridge kích hoạt CodeBuild chạy `terraform destroy` xóa sạch toàn bộ cụm EKS và tài nguyên AWS.
  * Cập nhật trạng thái `State = OFF` về Supabase để Product Plane hiển thị thông báo cho người dùng "Môi trường Live AI đang tạm tắt".

#### G. Tầng Giám Sát Hệ Thống (Observability Stack)
* **Prometheus & Grafana**: Thu thập và trực quan hóa các chỉ số kỹ thuật (Latency, QPS, Memory, GPU/CPU Usage).
* **OpenTelemetry & Jaeger**: Theo dõi vết giao tiếp distributed tracing giữa người dùng $\rightarrow$ Gateway $\rightarrow$ Agents $\rightarrow$ MCP Tools $\rightarrow$ KServe.
* **ECK (Elasticsearch, Fluentbit, Kibana)**: Quản lý và truy vết log tập trung của toàn bộ các Microservices trên EKS.

---

### 8.4. Tám Luồng Dữ Liệu Vận Hành Của Phase 2 (8 Numbered Data Flows)

1. **Flow 1 (Analyst Request - Product Plane OFF Mode)**:
   Analyst $\rightarrow$ Next.js Web App $\rightarrow$ RLS Query $\rightarrow$ Supabase $\rightarrow$ Persisted Report (Khi Evidence Plane đang tắt, giao diện hiển thị báo cáo tĩnh).
2. **Flow 2 (ML Training Flow)**:
   Feast (Offline Store) $\rightarrow$ Kubeflow Pipelines $\rightarrow$ Kubeflow Trainer $\rightarrow$ MLflow Registry $\rightarrow$ GitOps PR $\rightarrow$ Argo CD $\rightarrow$ KServe.
3. **Flow 3 (ML Inference Flow)**:
   Analyst $\rightarrow$ NGINX $\rightarrow$ Istio mTLS $\rightarrow$ `feature-api` $\rightarrow$ Feast (Online Store) $\rightarrow$ KServe `InferenceService` $\rightarrow$ Prediction Result.
4. **Flow 4 (Agent + RAG LLM Flow)**:
   Analyst Prompt $\rightarrow$ Agent Chat UI $\rightarrow$ `agentgateway` $\rightarrow$ Coordinator Agent $\rightarrow$ Specialist Agents (Feature/Drift) $\rightarrow$ MCP Tools $\rightarrow$ Envoy AI Gateway $\rightarrow$ KServe `LLMInferenceService` $\rightarrow$ Cited Answer.
5. **Flow 5 (Platform Operator Provisioning)**:
   Operator $\rightarrow$ Admin UI $\rightarrow$ Outbox Queue $\rightarrow$ Evidence Session Worker $\rightarrow$ Terraform Apply $\rightarrow$ EKS Provisioning $\rightarrow$ EventBridge Schedule Teardown.
6. **Flow 6 (CI/GitOps Continuous Deployment)**:
   Source CI $\rightarrow$ ECR Immutable Image Digest $\rightarrow$ Promotion Bot PR $\rightarrow$ GitOps Repo Merge $\rightarrow$ Argo CD Rollout $\rightarrow$ Evidence Plane.
7. **Flow 7 (Observability Flow)**:
   Microservices $\rightarrow$ OpenTelemetry Collector $\rightarrow$ Prometheus / Jaeger / Kibana $\rightarrow$ Grafana Dashboards.
8. **Flow 8 (Auto-Teardown & Cost Guard Flow)**:
   EventBridge Scheduler (Hard TTL 8h) $\rightarrow$ CodeBuild Destroy Job $\rightarrow$ Terraform Destroy EKS $\rightarrow$ Session Worker State OFF $\rightarrow$ Supabase Status Update.

---

### 8.5. Nguyên Tắc Bất Biến Bảo Vệ Phase 1 (Phase 1 Non-Mutation Principle)

* Mã nguồn triển khai Phase 2 được cô lập hoàn toàn trong các thư mục riêng biệt: `src/ml/`, `src/drift/`, `src/llm/`, `src/agents/`, `apps/web/`.
* Phase 2 **tuyệt đối không làm thay đổi hay ảnh hưởng** đến bất kỳ mã nguồn Data Ingestion, PySpark Transforms, Data Quality rules hay Metadata schema nào của Phase 1.
* Phase 1 tiếp tục vận hành độc lập, cung cấp nguồn dữ liệu sạch bất biến (Immutable Lakehouse Data Foundation) cho Phase 2 tiêu thụ.

---

## 9. Class Contracts & Design Patterns của Phase 2 (Low-Level Design)

Bản thiết kế class contracts được khoá trước khi bắt đầu hiện thực. File contract stubs sống tại [src/ml/contracts.py](file:///home/pearspringmind/Studying/FSDS/Financial-Distress-Data/src/ml/contracts.py) và [src/llm/contracts.py](file:///home/pearspringmind/Studying/FSDS/Financial-Distress-Data/src/llm/contracts.py). Spec đầy đủ tại [phase2/low-level-design.md](file:///home/pearspringmind/Studying/FSDS/Financial-Distress-Data/docs/phase2/low-level-design.md).

### 9.1. Năm ML Class Contracts (ML Track)

| # | Class | Design Pattern | Trách nhiệm Cốt Lõi | Phương thức Chính |
|---|---|---|---|---|
| ML-1 | `TrainingDataService` | Repository + Facade | Đọc lịch sử tính năng từ Feast Offline Store, join nhãn kiệt quệ theo quy tắc PIT, kiểm tra training schema, trả về snapshot lineage | `read_historical_features`, `join_labels`, `validate_schema`, `snapshot_lineage` |
| ML-2 | `PointInTimeSplitService` | Strategy | Tính toán ranh giới thời gian non-overlapping, chia train/validation/test không bị rò rỉ dữ liệu tương lai | `get_split_boundaries`, `split_by_time`, `assert_no_leakage` |
| ML-3 | `FeatureMaterializationService` | Repository + Idempotency | Quản lý checkpoint vật liệu hóa tính năng từ Offline Store sang Online Store (Valkey), stream push idempotent, TTL policy | `materialize_offline_to_online`, `push_stream_features_offline`, `push_stream_features_online`, `ttl_policy` |
| ML-4 | `ModelTrainingService` | Strategy + Template Method | Huấn luyện mô hình phân loại rủi ro (Logistic Regression / XGBoost phân tán qua Kubeflow Trainer), log run tái tạo được lên MLflow | `train`, `evaluate`, `log_run` |
| ML-5 | `ModelPromotionService` | Command + Factory | Kiểm tra promotion gates, giải quyết artifact URI bất biến, mở GitOps PR tự động, canary deploy, emit rollback metadata | `check_gates`, `resolve_immutable_uri`, `open_gitops_pr`, `rollback_metadata` |

#### Luồng Tuần Tự Huấn Luyện & Triển Khai Mô Hình ML:
```text
  1. TrainingDataService.read_historical_features(Feast)
       └─> 2. PointInTimeSplitService.split_by_time() + assert_no_leakage()
               └─> 3. FeatureMaterializationService.materialize_offline_to_online()
                       └─> 4. ModelTrainingService.train() + evaluate() + log_run(MLflow)
                               └─> 5. ModelPromotionService.open_gitops_pr() -> Argo CD -> KServe
```

---

### 9.2. Năm LLM Class Contracts (LLM Track)

| # | Class | Design Pattern | Trách nhiệm Cốt Lõi | Phương thức Chính |
|---|---|---|---|---|
| LLM-1 | `RagIngestionService` | Pipeline + Repository | Lấy tài liệu đáng tin cậy (báo cáo tài chính, distress labels), parse/chunk/deduplicate, kiểm tra giấy phép (licensing), ghi vector lên Feast/PGVector | `fetch_documents`, `parse_and_chunk`, `deduplicate_chunks`, `enforce_licensing_and_metadata`, `write_vectors` |
| LLM-2 | `EmbeddingRegistryService` | Registry + Strategy | Quản lý phiên bản embedding model, thực hiện hot-swap không downtime giữa 2 phiên bản embedding, kiểm tra tương thích chiều vector | `register_version`, `hot_swap`, `resolve_active`, `compatibility_check` |
| LLM-3 | `McpToolService` | Facade + Guard | Xác thực (authorize) và gọi (invoke) MCP tools có giới hạn timeout/budget, kiểm tra yêu cầu scoped, phát trace OpenTelemetry | `authorize`, `invoke`, `validate_request`, `emit_trace` |
| LLM-4 | `AgentOrchestrationService` | Mediator + Circuit Breaker | Điều phối Coordinator Agent với các Specialist Agents (Feature/Drift) trong giới hạn hops tối đa, kiểm tra citation, áp dụng deterministic failure policy khi circuit breaker mở | `coordinate`, `check_citations`, `failure_policy` |
| LLM-5 | `AgentReleaseService` | Command + Canary | Đăng ký, canary deploy, warmup, promote hoặc rollback cấu hình Agent/Model qua GitOps một cách an toàn | `register`, `canary`, `warm_up`, `promote_or_rollback` |

#### Luồng Tuần Tự Agentic RAG (Flow 4):
```text
  Analyst Prompt
   └─> AgentOrchestrationService.coordinate()
         ├─> Feature Analyst Agent
         │     └─> McpToolService.invoke("feast-tool") -> RagIngestionService (PGVector)
         │           └─> EmbeddingRegistryService.resolve_active() [hot-swap safe]
         └─> Drift Analyst Agent
               └─> McpToolService.invoke("drift-tool") -> drift-api FastAPI
                     └─> Check Citations + PII Guard
                           └─> AgentOrchestrationService.check_citations()
                                 └─> KServe LLMInferenceService (Qwen3-4B)
```

---

## 10. Bốn Ý Tưởng Độc Đáo (Novel Ideas) của Phase 2

Bốn ý tưởng sáng tạo này được định nghĩa từ trước khi bắt đầu hiện thực theo quy định SDD. Chi tiết đầy đủ tại [phase2/novel-ideas.md](file:///home/pearspringmind/Studying/FSDS/Financial-Distress-Data/docs/phase2/novel-ideas.md).

### ML Idea 1: Point-in-Time Leakage Guard (Bảo Vệ Rò Rỉ Dữ Liệu Tương Lai)
* **Tuyên bố**: Bất kỳ training frame nào được tạo từ Feast đều không được chứa giá trị tính năng được tạo ra **sau** `label_timestamp` (thời điểm dán nhãn kiệt quệ).
* **Cơ chế**: `PointInTimeSplitService.assert_no_leakage()` kiểm tra mọi feature join và báo lỗi nếu `future_feature_leakage_rows > 0`. Kết hợp với Hypothesis property-based testing để kiểm tra ngẫu nhiên nhiều tập dữ liệu.
* **Tại sao quan trọng**: Nếu bỏ qua bước này, mô hình XGBoost có thể học được thông tin từ tương lai (ví dụ: giá cổ phiếu đã sập SAU khi báo cáo tài chính xấu được công bố), dẫn đến độ chính xác ảo (Overly Optimistic Accuracy) khi kiểm tra nhưng thất bại thực tế (Production Failure).
* **Đường dẫn bằng chứng**: `docs/phase2/evidence/ml/pit-leakage-guard.md`.

### ML Idea 2: Cost-Governed Reproducibility Manifest (Bản Ghi Tái Tạo Bị Kiểm Soát Chi Phí)
* **Tuyên bố**: Mỗi lần chạy huấn luyện/RAG đều ghi một **Reproducibility Manifest** gắn liền với delta dữ liệu và model digest, kèm theo giới hạn chi phí cứng.
* **Cơ chế**: Manifest ghi đầy đủ: `snapshot_id`, `parent_id`, danh sách partition đã thay đổi, mã hash, `code_sha`, `env_digest`, `image_digest`, và `projected_cost_usd`. Nếu `projected_cost > cap`, provisioning bị từ chối trước khi khởi chạy.
* **Tại sao quan trọng**: Đảm bảo mọi kết quả thực nghiệm đều có thể tái tạo 100% và chi phí đám mây không bao giờ vượt ngân sách cho phép ($\le 25\text{ USD/phiên}$).
* **Đường dẫn bằng chứng**: `docs/phase2/evidence/ml/reproducibility-manifest.md`.

### LLM Idea 1: Embedding-Version Hot Swap (Hoán Đổi Phiên Bản Embedding Không Gián Đoạn)
* **Tuyên bố**: Việc nâng cấp phiên bản mô hình embedding (từ V1 sang V2) không gây downtime và không tạo ra truy vấn vector hỗn hợp giữa 2 phiên bản.
* **Cơ chế**: `EmbeddingRegistryService.hot_swap()` thực hiện dual-read validation (cả V1 và V2 trả lời song song để so sánh chất lượng), sau đó đổi alias atomically sang V2. `compatibility_check()` từ chối mọi truy vấn có chiều vector khác nhau giữa 2 phiên bản.
* **Tại sao quan trọng**: Trong hệ thống sản xuất, việc nâng cấp embedding model không thể gây ra gián đoạn dịch vụ hay kết quả RAG không nhất quán.
* **Đường dẫn bằng chứng**: `docs/phase2/evidence/llm/embedding-hot-swap.md`.

### LLM Idea 2: Citation / PII Guard with Trace-Linked Decisions (Bộ Bảo Vệ Trích Dẫn & Dữ Liệu Nhạy Cảm)
* **Tuyên bố**: Output không có nguồn trích dẫn hoặc chứa thông tin cá nhân nhạy cảm (PII) phải bị chặn hoặc được viết lại, và mọi quyết định liên kết tới trace OpenTelemetry để kiểm tra.
* **Cơ chế**:
  * **Citation Check**: Mỗi tuyên bố trong câu trả lời của LLM phải có nguồn tài liệu truy xuất được từ Feast/PGVector RAG pipeline.
  * **PII Guard**: Quét prompt, tài liệu và tool arguments để phát hiện và biên tập (redact) thông tin nhạy cảm (CMND, CCCD, số điện thoại, email) trước khi gửi tới LLM.
  * Mỗi quyết định (block/rewrite/allow) được ghi lại với `trace_id` OpenTelemetry.
* **Tại sao quan trọng**: Trong phân tích rủi ro tài chính, LLM tuyệt đối không được bịa đặt thông tin hoặc rò rỉ dữ liệu nhạy cảm của nhà đầu tư.
* **Đường dẫn bằng chứng**: `docs/phase2/evidence/llm/citation-pii-guard.md`.
