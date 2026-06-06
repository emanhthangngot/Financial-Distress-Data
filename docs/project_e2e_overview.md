# TÀI LIỆU KIẾN TRÚC VÀ LUỒNG DỮ LIỆU CHI TIẾT (END-TO-END)
## HỆ THỐNG PHÂN TÍCH KHỦNG HOẢNG TÀI CHÍNH (FINANCIAL DISTRESS DATA SYSTEM)

Tài liệu này đặc tả chi tiết và toàn diện luồng dữ liệu end-to-end của hệ thống, phân tích vai trò của từng tác nhân, thành phần hạ tầng, cấu trúc schema và logic xử lý nghiệp vụ của Giai đoạn 1 (Phase 1).

---

## 1. Bản đồ Kiến trúc Tổng thể (Architecture Map)

Kiến trúc hệ thống được xây dựng trên mô hình **Dual-Mode** nhằm giải quyết hai nhu cầu:
1.  **In-Memory Validation Mode (Chế độ Kiểm thử nhanh):** Phục vụ kiểm thử logic nghiệp vụ tự động (CI/CD) trong vài mili-giây, không phụ thuộc vào hạ tầng Docker/Database.
2.  **Live Local Lakehouse Mode (Chế độ Chạy thực tế):** Vận hành trên Docker Cluster với đầy đủ các thành phần phân tán (Airflow, Kafka, MinIO, Spark, Postgres, DuckDB).

```mermaid
flowchart TD
    subgraph Lớp Thu thập & Ingestion (Bronze Layer)
        A1[Source APIs / Fixtures] -->|Sync/Polling| B1[Airflow DAGs 01, 02, 03]
        A2[Market Price Streams] -->|Publish| C1[Kafka Topic: financial.price_events]
        A3[News/Alert Streams] -->|Publish| C2[Kafka Topic: financial.alert_events / news_events]
        
        B1 -->|Write Parquet| D1[(MinIO Bronze Lakehouse)]
        C1 & C2 -->|Consume & Batch| E1[MicroBatchConsumer]
        E1 -->|Partitioned Parquet| D1
    end

    subgraph Lớp Chuẩn hóa & Làm sạch (Silver Layer)
        D1 -->|PySpark Job / DAG 05| F1[Bronze-to-Silver Spark Transform]
        F1 -->|Deduplicated Parquet| G1[(MinIO Silver Lakehouse)]
        F1 -->|Invalid Records| H1[Postgres failed_records Table]
        F1 -->|Audit Logs| H2[Postgres pipeline_run_log Table]
    end

    subgraph Lớp Phân tích & Gán nhãn (Gold Layer)
        G1 -->|PySpark Job / DAG 06| I1[Silver-to-Gold Spark Transform]
        I1 -->|Altman Z'' Logic| J1[compute_distress_labels.py]
        I1 -->|PIT Join Logic| J2[Point-in-Time Joiner]
        
        I1 -->|Parquet Facts/Dims| K1[(MinIO Gold Lakehouse)]
        K1 -->|dim_company / dim_date| K1
        K1 -->|fact_financial / fact_market| K1
        K1 -->|obt_company_quarter_risk| K1
    end

    subgraph Lớp Truy vấn & Kiểm định (Serving Layer)
        K1 -->|httpfs read| L1[DuckDB Engine]
        H2 & H1 -->|Query Metadata| M1[DBeaver Client / User]
        L1 -->|Create Views| M1
    end
    
    subgraph Data Quality Guard
        F1 & I1 -->|DQ check| N1[dq_checks.py]
        N1 -->|Log Results| H3[Postgres data_quality_result Table]
    end
```

---

## 2. Đặc tả Chi tiết Vai trò & Nhiệm vụ của Từng Cấu phần

### 2.1. Vai trò: Bộ điều phối (Orchestrator - Apache Airflow)
*   **Vị trí file:** `dags/01_collect_company_master_data.py`, `dags/02_collect_financial_statement_api.py`, `dags/03_collect_market_price_api.py`, `dags/05_transform_bronze_to_silver.py`, `dags/06_pyspark_silver_to_gold.py`, `dags/07_run_data_quality_checks.py`, `dags/08_minio_duckdb_register_tables.py`.
*   **Nhiệm vụ:**
    *   Lập lịch (Scheduling), điều phối thứ tự chạy và quản lý vòng đời của các tác vụ xử lý dữ liệu.
    *   Quản lý tham số và biến môi trường (ví dụ: `PROJECT_METADATA_DSN` kết nối Postgres).
*   **Luồng xử lý chi tiết từng bước:**
    1.  **DAG 01, 02, 03 (Batch Ingestion):** Khởi chạy theo chu kỳ hoặc kích hoạt thủ công, gọi các hàm Python trong `src/collectors/` để lấy dữ liệu từ nguồn thông qua Adapter.
    2.  **DAG 04 (Streaming Ingestion):** Khởi chạy tác vụ gom cụm dòng sự kiện từ Kafka và ghi nhận xuống MinIO Bronze.
    3.  **DAG 05 (Bronze to Silver):** Đọc dữ liệu thô từ lớp Bronze, thực hiện chuẩn hóa, ép schema, khử trùng lặp và lưu trữ vào lớp Silver.
    4.  **DAG 06 (Silver to Gold):** Khởi động PySpark Engine chạy các job tính toán phân phối chiều (dimensions), sự kiện giá trị (facts), thực hiện gán nhãn rủi ro khủng hoảng tài chính (Z''-score) và lưu trữ lớp Gold.
    5.  **DAG 07 (Data Quality):** Kích hoạt các hàm kiểm tra DQ (null, unique, referential, freshness, retention), lưu kết quả vào Postgres và quyết định có chặn dòng chảy hạ nguồn hay không (Hard Fail vs Soft Fail).
    6.  **DAG 08 (DuckDB Catalog Register):** Tự động gửi các câu lệnh DDL lên DuckDB để cập nhật View dựa trên các tệp Parquet mới ghi đè ở Gold.

---

### 2.2. Vai trò: Nguồn dữ liệu & Adapter (Data Source & Adapters)
*   **Vị trí file:** `src/collectors/source_adapters/base.py`, `src/collectors/source_adapters/vnstock_adapter.py`.
*   **Nhiệm vụ:** 
    *   Đóng vai trò là cổng giao tiếp (Gateway) cách ly mã nguồn hệ thống với các biến động từ các API bên ngoài (SSI, Vnstock, sàn HOSE/HNX).
*   **Luồng xử lý chi tiết từng bước:**
    1.  Khởi tạo class `VnstockFixtureAdapter` tuân thủ interface `SourceAdapter` (được định nghĩa bằng Python `Protocol`).
    2.  Hàm `fetch_companies()` sinh ra danh sách dữ liệu master của doanh nghiệp (`ticker`, `company_name`, `exchange`, `industry`, `sector`, `listing_date`, `created_ts`).
    3.  Hàm `fetch_financial_statements(ticker, start_year, end_year)` sinh dữ liệu báo cáo tài chính quý. Để kiểm tra tính chính xác của thuật toán gán nhãn, adapter thiết lập logic: nếu `ticker == "BBB"` và `year` nằm ở năm kết thúc, dữ liệu tài chính sẽ tự động chuyển sang trạng thái "stressed" (Ví dụ: tổng tài sản giảm, nợ tăng, vốn chủ sở hữu âm, lợi nhuận giữ lại âm).
    4.  Hàm `fetch_market_prices(ticker, start_year, end_year)` sinh dữ liệu giá giao dịch ngày với các trường cơ bản như giá đóng cửa (`close_price`), khối lượng (`volume`), vốn hóa (`market_cap`).

---

### 2.3. Vai trò: Xử lý Streaming (Kafka Producer & Consumer)
*   **Vị trí file:** `src/streaming/events.py`, `src/streaming/kafka_to_bronze_consumer.py`.
*   **Nhiệm vụ:**
    *   Xử lý dòng dữ liệu thời gian thực có tần suất cao (giá khớp lệnh từng giây, tin tức khẩn cấp, cảnh báo từ thị trường).
*   **Luồng xử lý chi tiết từng bước:**
    1.  **Sinh Sự Kiện (Events Creation):** Lớp `StreamEvent` cung cấp các factory method:
        *   `price_update()`: Tạo sự kiện biến động giá. `event_id` được sinh ra bằng cách băm SHA256 các trường payload đã được sắp xếp khóa nhằm đảm bảo tính duy nhất và không trùng lặp (Idempotency).
        *   `alert()`: Tạo sự kiện cảnh báo giao dịch bất thường (ví dụ: khối lượng giao dịch đột biến). `event_id` sinh bằng UUIDv4 ngẫu nhiên.
        *   `news_sentiment()`: Tạo sự kiện tin tức kèm điểm số cảm xúc (sentiment score), cờ từ khóa rủi ro và điểm số mức độ nghiêm trọng.
    2.  **Gom Cụm Sự Kiện (Micro-batching):** `MicroBatchConsumer` nhận các bản ghi sự kiện thời gian thực và đẩy vào bộ đệm lưu trữ tạm thời (`_buffer`).
    3.  **Điều kiện Xả đệm (Flush Trigger):** Đệm sẽ được xả khi:
        *   Số lượng bản ghi trong đệm vượt ngưỡng `flush_record_count` (mặc định: 1000).
        *   Hoặc thời gian chờ vượt ngưỡng `flush_interval_seconds` (mặc định: 60 giây).
    4.  **Phân vùng & Lưu trữ (Partitioning):** Khi xả đệm, `MicroBatchConsumer` phân nhóm dữ liệu trong bộ đệm theo bộ ba `(topic, event_date, event_hour)`.
    5.  Mỗi nhóm được cấp một `batch_id` duy nhất dạng UUIDv4 và được ghi xuống MinIO Bronze theo đường dẫn chuẩn hóa:
        `s3a://financial-distress-lake/bronze/kafka/{topic}/event_date={YYYY-MM-DD}/event_hour={HH}/batch_id={batch_id}/`

---

### 2.4. Vai trò: Công cụ Biến đổi dữ liệu (Processing Engine - PySpark)
*   **Vị trí file:** `src/transforms/bronze_to_silver.py`, `src/transforms/silver_to_gold.py`, `src/transforms/keys.py`, `src/transforms/spark_session.py`.
*   **Nhiệm vụ:**
    *   Đọc/Ghi dữ liệu hàng loạt trên MinIO Object Storage dưới dạng tệp Parquet.
    *   Tính toán song song các phép toán biến đổi từ Bronze sang Silver và Silver sang Gold.
*   **Luồng xử lý chi tiết từng bước:**
    1.  **Khởi tạo Session:** `build_spark_session()` đọc cấu hình từ `configs/spark_config.yaml`, thiết lập các tham số kết nối MinIO S3A (endpoint, credentials, path-style access) và cấu hình chế độ ghi đè phân vùng động (`spark.sql.sources.partitionOverwriteMode = dynamic`).
    2.  **Xử lý Lớp Bronze -> Silver (`bronze_to_silver_spark`):**
        *   Đổi tên toàn bộ cột thành chữ thường và cắt bỏ khoảng trắng đầu cuối (`strip().lower()`).
        *   Thêm các cột tùy chọn (nullable) bị thiếu trong nguồn cấp về giá trị `NULL`.
        *   Kiểm tra tính toàn vẹn của các cột bắt buộc (`required`). Nếu thiếu, bản ghi sẽ bị đẩy sang dataframe `failed` kèm lý do lỗi, đồng thời mã hóa JSON toàn bộ payload gốc lưu vào trường `raw_payload`.
        *   Thực hiện lọc các bản ghi hợp lệ sang dataframe `valid`.
        *   Dùng Window function chia nhóm dữ liệu theo khóa chính (ví dụ: `ticker`, `report_period`) sắp xếp theo `created_ts` giảm dần, đánh số dòng (`row_number()`) và chỉ giữ lại bản ghi có số dòng bằng 1. Đây là cách khử trùng lặp dữ liệu triệt để nhất.
    3.  **Xử lý Lớp Silver -> Gold (`silver_to_gold`):**
        *   `build_fact_financial_statement_spark()`: Băm SHA256 của ticker viết hoa để lấy 16 ký tự đầu làm `company_key`. Chuyển đổi ngày công bố báo cáo thành khóa số nguyên `date_key` định dạng `YYYYMMDD`.
        *   `build_fact_market_price_spark()`: Sử dụng hàm `lag()` tính toán tỷ suất sinh lời hàng ngày (`daily_return = (close_price - lag(close_price)) / lag(close_price)`). Thiết lập cờ biến động mạnh `volatility_signal` nếu tỷ suất sinh lời tuyệt đối vượt quá 7% (`abs(daily_return) > 0.07`).
        *   `write_partitioned_parquet()`: Thực hiện ghi đè dữ liệu ra MinIO Gold theo chế độ `overwrite` kèm cấu hình phân vùng (partition).

---

### 2.5. Vai trò: Quản trị Metadata vận hành (PostgreSQL Metadata Client)
*   **Vị trí file:** `src/metadata/metadata_writer.py`, `src/metadata/schema_registry.py`, `sql/init_project_metadata.sql`.
*   **Nhiệm vụ:**
    *   Quản lý lịch sử chạy (Lineage/Audit trail) của toàn bộ hệ thống.
    *   Lưu vết dữ liệu lỗi phục vụ công tác rà soát lỗi (Debugging/Tracing) và kiểm tra chất lượng dữ liệu.
*   **Luồng xử lý chi tiết từng bước:**
    1.  **Đăng ký Schema:** `InMemorySchemaRegistry` quản lý các hợp đồng dữ liệu chuẩn hóa của hệ thống. Các bảng thô muốn vào Silver phải tuân thủ nghiêm ngặt mô tả trường bắt buộc/tùy chọn định nghĩa tại đây.
    2.  **Ghi nhật ký chạy (Run Logging):** `PostgresMetadataWriter.log_run()` chèn một bản ghi vào bảng `project_metadata.pipeline_run_log` bao gồm: mã chạy (`run_id` tự sinh dạng UUID), tên DAG, tên Task, tên bảng đích, trạng thái, thời gian chạy và số lượng dòng dữ liệu đầu vào/đầu ra.
    3.  **Lưu bản ghi lỗi (Failed Records Logging):** Khi lớp Silver phát hiện bản ghi lỗi cấu trúc, `log_failed_record()` được gọi để ghi nhận bản ghi lỗi vào bảng `project_metadata.failed_records` dưới dạng cột `jsonb` để có thể truy vấn động bằng SQL trong Postgres.
    4.  **Cập nhật Độ tươi mới dữ liệu (Freshness Updates):** Cập nhật thời gian xuất hiện sự kiện trễ nhất và tính toán độ trễ thời gian so với thời điểm kiểm tra, lưu trữ vào bảng `project_metadata.dataset_freshness`.

---

### 2.6. Vai trò: Người gác cổng chất lượng (Data Quality Engine)
*   **Vị trí file:** `src/quality/dq_checks.py`, `configs/dq_rules.yaml`.
*   **Nhiệm vụ:**
    *   Phát hiện các sự cố bất thường về dữ liệu trước khi cung cấp cho các ứng dụng downstream hoặc mô hình AI học máy.
*   **Quy tắc kiểm tra chất lượng & Xử lý lỗi:**
    *   **Quy tắc 1: Kiểm tra Not Null (`check_not_null`):** Duyệt qua cột chỉ định (ví dụ: `ticker`). Nếu phát hiện có giá trị Null, đánh dấu trạng thái `"fail"`, độ nghiêm trọng `"critical"`.
    *   **Quy tắc 2: Kiểm tra Unique Key (`check_unique`):** Kiểm tra tính duy nhất của khóa tổ hợp (ví dụ: `ticker` + `report_period`). Nếu phát hiện bản ghi trùng lặp, trả về trạng thái `"fail"`, độ nghiêm trọng `"critical"`.
    *   **Quy tắc 3: Kiểm tra Khóa ngoại (`check_referential_integrity`):** Đối chiếu tập hợp giá trị cột của Fact với tập hợp khóa Dimension (ví dụ: `company_key` trong Fact tài chính phải tồn tại trong chiều `dim_company`). Nếu có dòng vi phạm, trả về trạng thái `"fail"`, độ nghiêm trọng `"critical"`.
    *   **Quy tắc 4: Kiểm tra Tỷ lệ giữ lại (`check_retention`):** So sánh số lượng dòng dữ liệu ở Silver so với Bronze. Nếu tỷ lệ này rơi xuống dưới ngưỡng cài đặt (ví dụ: dưới 80% do quá nhiều bản ghi lỗi bị Silver loại bỏ), hệ thống trả về trạng thái `"warning"`, độ nghiêm trọng `"warning"`.
    *   **Quy tắc 5: Kiểm tra Độ tươi mới dữ liệu (`check_freshness`):** So sánh timestamp lớn nhất của dữ liệu nhận được với thời gian hiện tại. Nếu độ trễ vượt quá ngưỡng SLA quy định trong `dq_rules.yaml` (ví dụ: 60 phút đối với giá cổ phiếu giao dịch), trả về trạng thái `"warning"`, mức độ `"warning"`.
    *   **Logic Rẽ nhánh:** Các lỗi ghi nhận mức `"critical"` (Hard Fail) sẽ lập tức dừng pipeline (raise Exception để Airflow đánh dấu Task thất bại), ngăn chặn ô nhiễm dữ liệu hạ nguồn. Các lỗi mức `"warning"` (Soft Fail) chỉ ghi nhận cảnh báo và cho phép pipeline tiếp tục vận hành.

---

### 2.7. Vai trò: Động cơ truy vấn phục vụ phân tích (Serving Engine - DuckDB & DBeaver)
*   **Vị trí file:** `src/catalog/duckdb_catalog.py`, `sql/duckdb_create_views.sql`, `sql/duckdb_validation_queries.sql`.
*   **Nhiệm vụ:**
    *   Cung cấp một cổng truy xuất dữ liệu hiệu năng cao trên nền tảng hồ dữ liệu (MinIO Parquet files) mà không cần cấu hình cụ thể các máy chủ truy vấn phức tạp.
*   **Luồng xử lý chi tiết từng bước:**
    1.  **Thiết lập kết nối S3 (`duckdb_httpfs_setup_sql`):** Sử dụng thư viện `httpfs` của DuckDB để kết nối trực tiếp với cổng MinIO S3 bằng cách thực thi cấu hình các thuộc tính: `s3_endpoint`, `s3_access_key_id`, `s3_secret_access_key`, tắt SSL (`s3_use_ssl = false`) và bật chế độ đường dẫn (`s3_url_style = 'path'`).
    2.  **Đăng ký View ảo (Virtual Views Registration):** Tạo các View ảo trên DuckDB map với các tệp Parquet phân vùng tại Gold:
        ```sql
        CREATE OR REPLACE VIEW gold_fact_financial_statement AS 
        SELECT * FROM read_parquet('s://financial-distress-lake/gold/fact_financial_statement/**/*.parquet');
        ```
    3.  **Truy vấn báo cáo kiểm định (Validation Queries):**
        *   Truy xuất tổng số dòng báo cáo tài chính.
        *   Kiểm tra xem có bản ghi nào bị trùng lặp tổ hợp `ticker` + `report_period` trong view vàng hay không.
        *   Thống kê phân bổ nhãn rủi ro khủng hoảng tài chính (`distress_label`).
        *   Trình diễn dữ liệu tổng hợp của 20 dòng đầu tiên trong One-Big-Table (`gold_feat_company_unified`).
    4.  **Tương tác phía người dùng (User Interface):** Kỹ sư dữ liệu / Chuyên viên phân tích sử dụng phần mềm DBeaver kết nối vào DuckDB thông qua JDBC driver để thực hiện trực tiếp các truy vấn SQL nghiệp vụ lên hồ dữ liệu mà không cần tải thủ công các tệp tin Parquet về máy tính cá nhân.

---

## 3. Đặc tả Logic Nghiệp vụ Phức tạp (Core Business Algorithms)

### 3.1. Thuật toán Tính điểm Altman Z'' (Z Double Prime)
Công thức Altman Z'' được thiết kế riêng cho nhóm doanh nghiệp phi sản xuất và dịch vụ để tính toán chỉ số sức khỏe tài chính.
Quy trình tính toán tại `z_double_prime(row)` diễn ra như sau:

$$WC = \text{Current Assets} - \text{Current Liabilities}$$

$$\text{Term 1} = 6.56 \times \left( \frac{WC}{\text{Total Assets}} \right)$$

$$\text{Term 2} = 3.26 \times \left( \frac{\text{Retained Earnings}}{\text{Total Assets}} \right)$$

$$\text{Term 3} = 6.72 \times \left( \frac{\text{EBIT}}{\text{Total Assets}} \right)$$

$$\text{Term 4} = 1.05 \times \left( \frac{\text{Equity}}{\text{Total Liabilities}} \right)$$

$$Z'' = \text{Term 1} + \text{Term 2} + \text{Term 3} + \text{Term 4}$$

#### Xử lý các điều kiện biên và giá trị biên của thuật toán:
1.  **Nếu doanh nghiệp không có nợ phải trả (`total_liabilities = 0`):** Phép chia tại `Term 4` sẽ bị lỗi chia cho 0. Logic nghiệp vụ xử lý bằng cách gán cứng tỷ lệ này bằng hằng số trần `99.0` (được định nghĩa bởi hằng số `ZERO_LIABILITIES_X4_CAP`), đồng thời bổ sung cờ cảnh báo `"zero_liabilities_x4_capped"` vào trường lý do rủi ro (`distress_reason`).
2.  **Doanh nghiệp thuộc nhóm ngành Tài chính (Ngân hàng, Chứng khoán, Bảo hiểm):** Các chỉ số bảng cân đối kế toán của nhóm này có tính chất đặc thù nên điểm Altman Z'' không phản ánh đúng thực tế. Hàm `is_financial_sector()` sẽ kiểm tra các trường mô tả ngành, nếu phát hiện thuộc nhóm ngành tài chính (GICS sector 40), bản ghi lập tức bị loại trừ khỏi quy trình gán nhãn (`distress_label = NULL`, lý do `"financial_sector_excluded"`, không đủ điều kiện huấn luyện mô hình ML `training_eligible = False`).
3.  **Lỗ hai quý liên tiếp (`two_quarter_net_loss`):** Thuật toán yêu cầu phải đối chiếu với báo cáo quý trước đó. Hàm `_is_immediately_previous_quarter` sẽ kiểm tra tính liên tục của quý kế toán (ví dụ: `2025Q2` liên tục với `2025Q1`). Nếu phát hiện cả quý hiện tại và quý trước đều có lợi nhuận ròng nhỏ hơn 0 (`net_income < 0`), cờ cảnh báo rủi ro này mới được kích hoạt.

---

### 3.2. Thuật toán Ghép cặp Dữ liệu Point-In-Time (PIT Join)
Nhằm ngăn chặn lỗi rò rỉ thông tin tương lai vào mô hình huấn luyện ML (Look-ahead bias), phép join đặc trưng thị trường vào báo cáo tài chính bắt buộc phải dùng cơ chế PIT join:

```
[Mốc Báo Cáo Tài Chính] (Report Release Date: 2026-01-30)
          |
          v
<---------|----------------------- [Trục Thời Gian]
          |  (Chỉ lấy các sự kiện giá có timestamp <= 2026-01-30)
     *---------*----*----*
     P1        P2   P3   P4 (Bị loại vì xảy ra vào 2026-02-02)
     
     ===> Hệ thống tự động chọn sự kiện P3 (Sự kiện giá mới nhất tính đến ngày 2026-01-30)
```

**Mã nguồn thuật toán xử lý:**
```python
def pit_join_features(references: list[dict], features: list[dict]) -> list[dict]:
    output = []
    # 1. Nhóm các sự kiện thị trường theo ticker
    by_ticker = {}
    for feature in features:
        by_ticker.setdefault(feature["ticker"].upper(), []).append(feature)
    
    # 2. Sắp xếp chuỗi thời gian của sự kiện giảm dần (từ mới nhất về cũ nhất)
    for ticker_features in by_ticker.values():
        ticker_features.sort(key=lambda item: item["event_timestamp"], reverse=True)
        
    # 3. Với mỗi báo cáo tài chính (reference row), tìm sự kiện khớp mốc thời gian đầu tiên
    for reference in references:
        ticker = reference["ticker"].upper()
        ref_ts = reference["event_timestamp"]
        
        # Lấy bản ghi sự kiện có timestamp nhỏ hơn hoặc bằng mốc của báo cáo tài chính
        candidate = next(
            (f for f in by_ticker.get(ticker, []) if str(f["event_timestamp"]) <= str(ref_ts)),
            {}
        )
        
        # Hợp nhất dữ liệu đặc trưng vào bản ghi gốc dưới tiền tố 'feature_'
        output.append({
            **reference,
            **{f"feature_{k}": v for k, v in candidate.items()}
        })
    return output
```

---

## 4. Bảng Tra cứu Cấu trúc Hồ Dữ liệu (Lakehouse Schema Contracts)

Dưới đây là đặc tả chi tiết của 3 lớp dữ liệu chính trong Medallion Lakehouse:

| Lớp Hồ Dữ liệu | Đường dẫn thư mục lưu trữ (MinIO / Local Mock) | Khóa Chính (Primary Key) | Danh sách Cột Bắt buộc (Required Fields) | Ý nghĩa nghiệp vụ |
| :--- | :--- | :--- | :--- | :--- |
| **Bronze (Thô)** | `s3a://financial-distress-lake/bronze/` | `ticker` + `report_period` (hoặc `trading_date`) | Tùy thuộc vào đầu vào của API nguồn cung cấp | Chứa dữ liệu gốc, chưa loại bỏ trùng lặp, chưa chuẩn hóa định dạng cột |
| **Silver (Làm sạch)** | `s3a://financial-distress-lake/silver/` | `ticker` + `report_period` | `ticker`, `report_period`, `fiscal_year`, `fiscal_quarter`, `total_assets`, `total_liabilities`, `equity`, `created_ts` | Dữ liệu đã chuẩn hóa tên cột về chữ thường, lọc bỏ các bản ghi hỏng cấu trúc và loại bỏ trùng lặp |
| **Gold (Kimball)** | `s3a://financial-distress-lake/gold/dim_company` | `company_key` | `company_key`, `ticker`, `company_name`, `exchange`, `valid_from_ts`, `is_current` | Chiều thông tin doanh nghiệp SCD Type 2 |
| **Gold (Kimball)** | `s3a://financial-distress-lake/gold/fact_financial_statement` | `company_key` + `date_key` | `company_key`, `date_key`, `ticker`, `report_period`, `total_assets`, `total_liabilities` | Bảng sự kiện báo cáo tài chính định kỳ của doanh nghiệp |
| **Gold (Kimball)** | `s3a://financial-distress-lake/gold/obt_company_quarter_risk` | `ticker` + `report_period` | Các trường từ Fact tài chính kèm nhãn rủi ro `distress_label` và điểm `z_score` | Bảng phẳng tích hợp toàn bộ chỉ số tài chính phục vụ trực tiếp cho huấn luyện mô hình ML ở Phase 2 |

---

## 5. Hướng dẫn Vận hành và Chạy Thử nghiệm (Runbook & Verification)

Để xác minh toàn bộ các cấu phần trên vận hành đúng chức năng, kỹ sư dữ liệu thực thi tuần tự các bước sau:

### Bước 1: Kiểm thử mã nguồn cục bộ (Unit Tests)
Đảm bảo logic toán học và các quy tắc xử lý biên của Altman Z'', Khử trùng lặp và PIT join hoạt động hoàn hảo trước khi cấu hình lên hạ tầng:
```bash
pytest tests/
```

### Bước 2: Kiểm tra cấu hình Docker Compose
Xác minh tệp mô tả hạ tầng cục bộ Docker Compose không gặp lỗi cú pháp:
```bash
docker compose config
```

### Bước 3: Khởi động hệ thống dịch vụ
```bash
# Khởi động các dịch vụ lưu trữ dữ liệu và thông điệp
docker compose up -d postgres minio kafka

# Khởi động công cụ điều phối Airflow sau khi các thành phần trên đã sẵn sàng
docker compose up -d airflow-webserver airflow-scheduler
```

### Bước 4: Tạo chủ đề trên Kafka (Topics)
```bash
# Chạy script tạo các topic trên Kafka broker
docker compose exec kafka bash /opt/financial-distress-init/kafka_init_topics.sh
```

### Bước 5: Truy vấn dữ liệu kiểm định bằng DuckDB
Khởi động DuckDB CLI hoặc DBeaver truy cập vào DuckDB, nạp các View dữ liệu Gold và chạy validation:
```sql
-- Thiết lập kết nối
INSTALL httpfs;
LOAD httpfs;
SET s3_endpoint='localhost:9000';
SET s3_access_key_id='minioadmin';
SET s3_secret_access_key='minioadmin';
SET s3_use_ssl=false;
SET s3_url_style='path';

-- Đọc trực tiếp phân bổ nhãn rủi ro khủng hoảng tài chính từ hồ Parquet
SELECT distress_label, COUNT(*) AS so_luong_doanh_nghiep
FROM read_parquet('s3://financial-distress-lake/gold/obt_company_quarter_risk/**/*.parquet')
GROUP BY distress_label;
```
