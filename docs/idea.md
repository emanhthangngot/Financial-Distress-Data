# Đồ án: Hệ thống Phân tích Rủi ro Tài chính (Financial Distress Data Platform)

## 0. Tổng quan Dự án (Project Overview)
Dự án này thiết kế và xây dựng một Data Platform end-to-end thu gọn (compact) nhằm thu thập, xử lý và phân tích dữ liệu tài chính của các doanh nghiệp niêm yết tại Việt Nam. Mục tiêu cốt lõi là tạo ra một nền tảng dữ liệu đáng tin cậy phục vụ cho việc tính toán rủi ro kiệt quệ tài chính (Financial Distress), ứng dụng vào Dashboard phân tích hoặc làm đầu vào cho các mô hình Machine Learning/AI.

Kiến trúc được thiết kế theo tư duy **Local-first + Cloud-light**, tuân thủ chặt chẽ các tiêu chuẩn Data Engineering thực tế (Medallion Architecture, CI/CD, Data Quality, Observability).

---

## 1. Dữ liệu Đầu vào (Dataset)
**Tuyệt đối KHÔNG sử dụng dữ liệu giả (Synthetic Data).** Hệ thống sử dụng tập dữ liệu thực tế (Real-world dataset) thu thập từ thị trường chứng khoán Việt Nam.

* **Nguồn dữ liệu:** API của các công ty chứng khoán (như TCBS, SSI), thư viện `vnstock`, hoặc dữ liệu Public từ CafeF/Vietstock.
* **Quy mô:** Đảm bảo tải lịch sử dữ liệu đủ lớn (≥ 10 GB raw data hoặc ≥ 20 triệu records).
* **Thực thể (Entities):**
    1.  **Thông tin doanh nghiệp:** Mã cổ phiếu, ngành nghề, sàn niêm yết.
    2.  **Báo cáo tài chính (BCTC):** Cân đối kế toán, Kết quả kinh doanh, Lưu chuyển tiền tệ (theo Quý/Năm).
    3.  **Dữ liệu thị trường (Market Data):** Giá đóng cửa lịch sử, Khối lượng giao dịch.

---

## 2. Thiết kế Kiến trúc Dữ liệu (Data Architecture & Lakehouse)
Hệ thống áp dụng mô hình **Medallion Architecture (Bronze -> Silver -> Gold)**, sử dụng định dạng open columnar format là **Parquet**.

### 2.1. Ingestion & Tầng Bronze (Raw Zone)
* **Cơ chế:** Batch pipeline thu thập dữ liệu qua API, lưu giữ nguyên bản (raw JSON/CSV) dưới định dạng Parquet.
* **Phân vùng (Partitioning):** Dữ liệu được chia theo `fiscal_year` và `fiscal_quarter` để tối ưu truy vấn.
* **Xử lý lỗi Ingestion (Failure Mode):** Hệ thống có cơ chế bắt lỗi timeout từ API, retry tối đa 3 lần, và đưa các mã lỗi vào file `failed_tickers.csv` (Dead-letter queue) để tránh gián đoạn pipeline.

### 2.2. Tầng Silver (Curated/Cleaned Zone)
* **Nhiệm vụ:** Làm sạch, đồng nhất kiểu dữ liệu, đổi tên cột (Schema Standardization), xử lý missing values (loại bỏ các công ty thiếu dữ liệu > 30%), và deduplicate (giữ lại bản ghi có `created_ts` mới nhất).

### 2.3. Tầng Gold (Data Mart)
* Sử dụng mô hình Star Schema kết hợp OBT (One-Big-Table).
* **Dimension Tables:** `dim_company` (Grain: 1 dòng/công ty), `dim_date` (Grain: 1 dòng/ngày).
* **Fact Tables:** `fact_financial_statement`, `fact_market_price` (Grain: 1 dòng/công ty/kỳ báo cáo).
* **OBT Table:** `obt_company_quarter_risk` chứa các chỉ số tài chính đã tính toán (ROA, ROE, Debt/Asset) và điểm Z-Score/Label rủi ro.

---

## 3. Tech Stack & Distributed Processing Engine
* **Storage & Metadata:** AWS S3 (Data Lake), AWS Glue Catalog, Athena (Query engine).
* **Database (Metadata & DQ Logs):** PostgreSQL (chạy local trên Docker) dùng để track pipeline run, data quality result và schemas. Tool DBeaver để query trực tiếp.
* **Distributed Processing Engine:** **Apache Spark (PySpark)**.
    * *Rationale:* PySpark được chạy ở chế độ local mode (`--master local[*]`) cho các transform non-trivial từ Silver sang Gold (join nhiều bảng, tính window functions, aggregations).
* **Orchestration:** **Apache Airflow** (Local Docker).
    * Pipeline được thiết kế theo dạng DAG end-to-end. Đảm bảo tính **Idempotent** (ghi đè partition thay vì append mù quáng) và có cấu hình **Retry Policy**.

---

## 4. Serving Layer & Application
Dữ liệu từ tầng Gold (truy xuất qua Athena hoặc export ra Postgres) được phục vụ cho lớp ứng dụng.

* **Track: Dashboard / BI:**
    * Sử dụng **Apache Superset**, **Metabase** hoặc **Streamlit** (tích hợp trong Docker Compose).
    * **Nội dung:** Trả lời ít nhất 3 câu hỏi nghiệp vụ (VD: Top 10 công ty có rủi ro cao nhất theo ngành? Xu hướng Z-score của ngành Bất động sản trong 5 năm qua?). Có ít nhất 1 biểu đồ Time-series cho phép drill-down từ Năm xuống Quý.

---

## 5. Đảm bảo Chất lượng Dữ liệu (Data Quality)
Thực thi kiểm tra chất lượng dữ liệu (sử dụng Great Expectations hoặc custom Python script), log kết quả vào bảng `data_quality_result` trên Postgres. Các checks bao gồm:
1.  **Not Null:** Ticker và report_period không được null.
2.  **Uniqueness:** Ticker + report_period phải là duy nhất trong bảng Fact.
3.  **Range/Value:** Total Assets >= 0, Z-score nằm trong ngưỡng lý thuyết hợp lý.
4.  **Referential Integrity:** Ticker trong Fact phải tồn tại trong bảng `dim_company`.
5.  **Row Count/Volume:** Cảnh báo nếu số lượng bản ghi drop > 50% so với lần run trước.

*Hành vi khi Fail:* Gửi cảnh báo (Alert) vào log, nếu là lỗi nghiêm trọng (Schema sai lệch), block các downstream task.

---

## 6. Tiêu chuẩn Kỹ thuật (Engineering Practices)

### 6.1. Source Control, CI/CD & Code Quality
* **Source Control:** Sử dụng Git, có PR và commit message có ý nghĩa.
* **Code Quality:** Cấu hình **Ruff** (Linter) và **Black** (Formatter) để chuẩn hóa code Python.
* **CI/CD:** Sử dụng **GitHub Actions** chạy tự động Linting và Testing mỗi khi có Push/PR lên nhánh main. Có step build Docker image.
* **Secret Management:** Sử dụng file `.env`. Không bao giờ hard-code credentials vào source code. Cung cấp file `.env.example` trong repo.

### 6.2. Testing Strategy
* **Unit Tests:** Có ít nhất 5 unit tests (dùng `pytest`) kiểm tra các logic transform lõi của PySpark (vd: tính Z-score, đổi tên schema).
* **Integration Test:** Có 1 test chạy toàn bộ mini-pipeline từ raw đến gold trên tập dữ liệu mẫu (sample data ~100 records).

### 6.3. Observability
* Sử dụng **Structured Logging** (định dạng JSON log) cho các script Python thay vì lệnh `print()`.
* Log các metrics quan trọng vào Postgres: `job_duration`, `records_processed`, và `data_freshness_lag`.

---

## 7. Cẩm nang Vận hành & Khắc phục sự cố (Runbook)
| Failure Mode (Lỗi thường gặp) | Triệu chứng (Symptoms) | Recovery Steps (Các bước xử lý) |
| :--- | :--- | :--- |
| **1. Source API thay đổi Schema/Bị Down** | Task `ingest_bronze` báo lỗi timeout liên tục hoặc lỗi KeyError khi parse JSON. | 1. Tạm dừng DAG trên Airflow.<br>2. Kiểm tra log Ingestion. Cập nhật URL/Mapping config nếu API đổi tên trường.<br>3. Chạy lại (Clear state) task bị lỗi. |
| **2. Local DB (Postgres) mất kết nối** | Airflow Scheduler báo lỗi kết nối DB, hoặc task không ghi được Data Quality log. | 1. Kiểm tra trạng thái container: `docker ps`.<br>2. Khởi động lại DB: `docker-compose restart postgres`.<br>3. Kiểm tra thông số bộ nhớ/Disk space của Docker. |
| **3. Trùng lặp dữ liệu ở tầng Gold (Duplicate Data)** | Truy vấn trên Athena hiển thị nhiều dòng cho cùng 1 công ty trong cùng 1 quý. | 1. Kiểm tra lại mode ghi của PySpark (phải là `overwrite` partition, không phải `append`).<br>2. Xóa thủ công partition bị lỗi trên S3.<br>3. Kích hoạt lại bước `silver_to_gold` trên Airflow. |

---

## 8. Cấu trúc Thư mục Dự án (Project Structure)
```text
financial-distress-data-system/
├── .github/workflows/          # CI/CD pipelines (GitHub Actions)
├── configs/                    # Các file config (YAML, mapping rules)
├── dags/                       # Airflow DAGs
├── src/
│   ├── ingestion/              # Code gọi API lấy dữ liệu thực tế
│   ├── transformations/        # PySpark jobs (Bronze -> Silver -> Gold)
│   ├── quality/                # Data Quality checks scripts
│   └── dashboard/              # Code Streamlit/App (nếu dùng code-based dashboard)
├── sql/                        # Init scripts cho Postgres & DDL cho Athena
├── tests/                      # Unit tests & Integration tests
├── docker-compose.yml          # Container orchestration (Airflow, Postgres, Superset...)
├── requirements.txt            # Python dependencies
├── .env.example                # Template bảo mật biến môi trường
├── README.md                   # Hướng dẫn chạy dự án
└── runbook.md                  # Hướng dẫn xử lý sự cố
