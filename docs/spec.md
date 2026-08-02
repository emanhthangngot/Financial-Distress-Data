# NEXLAB Spec-Driven Development (SDD) Guide & Spec Setup

Tài liệu này hướng dẫn áp dụng phương pháp **Spec-Driven Development (SDD)** của Nexlab vào dự án **Financial Distress Data + AI Engineering System**. Tài liệu được biên soạn dựa trên *Nexlab SDD Playbook for Intern Candidates (v1.1, Q2 2026)* và tham khảo tiêu chuẩn *GitHub Spec-Kit*, nhằm kết nối bốn tài liệu hiện tại:
* [idea.md](./idea.md) (PH-0: Problem Discovery)
* [coursework_proposal.md](./coursework_proposal.md) (PRD Constraints & Phase Gates)
* [mini_coursework.md](./mini_coursework.md) (Phase 1: Data Pipeline Foundation Spec)
* [coursework.md](./coursework.md) (Phase 2: ML + LLM + GitOps Spec)

---

## 1. Quy trình SDD 7 Phase của Nexlab áp dụng cho Đồ án

Dự án Financial Distress được ánh xạ chặt chẽ vào quy trình 7 Phase của Nexlab như sau:

```mermaid
flowchart TD
    subgraph Spec Work (Không viết code)
        PH0[PH-0: Problem Discovery<br>idea.md] -->|Gate Pass: 6/10 Users confirm| PH1[PH-1: Product Spec<br>coursework_proposal.md]
        PH1 -->|Gate Pass: Must-stories & AC defined| PH2[PH-2: Tech Architecture<br>mini_coursework.md / coursework.md]
        PH2 -->|Gate Pass: Stack & Medallion Schema set| PH3[PH-3: UI/UX Design<br>DBeaver Views & CLI specs]
        PH3 -->|Gate Pass: CLI/Database specs ready| PH4[PH-4: SDD Setup<br>AGENTS.md / CLAUDE.md]
    end
    subgraph Implementation (Code & Deploy)
        PH4 -->|Gate Pass: Test seeds FAIL| PH5[PH-5: Sprint Implementation<br>Airflow / Kafka / PySpark code]
        PH5 -->|Gate Pass: All tests PASS| PH6[PH-6: Deploy & Go-live<br>Local Docker cluster & DBeaver proof]
    end
```

### Các Gate chuyển phase cụ thể của Dự án:
1. **PH-0 ➔ PH-1 Gate**: Đạt được sau khi khảo sát [idea.md](./idea.md) và xác nhận vấn đề "Dự báo sớm khủng hoảng tài chính dựa trên dữ liệu phi cấu trúc và chỉ số kế toán" là một vấn đề thực tế, tốn kém tài nguyên nếu xử lý thủ công.
2. **PH-1 ➔ PH-2 Gate**: Chuyển đổi các ràng buộc trong [coursework_proposal.md](./coursework_proposal.md) thành bộ tính năng cụ thể.
3. **PH-4 ➔ PH-5 Gate**: Viết các kiểm thử đơn vị (**Unit Test Seeds**) dựa trên tiêu chí nghiệm thu (Acceptance Criteria) của `mini_coursework.md` và chạy thử để đảm bảo các kiểm thử này **FAIL có ý nghĩa** trước khi Coding Agent bắt đầu tự động hóa viết code.

---

## 2. Chiến lược mở rộng từ Phase 1 sang Phase 2 (Extensibility Strategy)

Hiện tại dự án đang tập trung vào **Giai đoạn 1 (mini_coursework.md)**. Để sau này có thể dễ dàng mở rộng sang **Giai đoạn 2 (coursework.md)** mà không phải đập đi xây lại hệ thống, chúng ta áp dụng các nguyên tắc thiết kế mở rộng sau:

### A. Tách biệt Module Code (Loose Coupling)
Cấu trúc thư mục được thiết kế theo dạng Module độc lập, phân rõ nhiệm vụ của từng Phase:
* `src/collectors/`:
  * `company_list_collector.py`, `financial_statement_collector.py`, `market_price_collector.py` (Phase 1) ➔ Gọi API/thư viện/WebSocket qua source adapters, độc lập với `drift_generator.py` (Phase 2).
* `src/generator/`:
  * Chỉ giữ fixture/synthetic generators cho test hoặc fallback demo, không còn là nguồn dữ liệu chính của Phase 1.
* `src/transforms/`:
  * `silver_to_gold.py` (Phase 1) ➔ Chỉ tính toán chỉ số tài chính cơ bản.
  * `gold_to_features.py` (Phase 2) ➔ Chịu trách nhiệm tính toán các cột đặc trưng (features) và nhãn (labels) phục vụ ML mà không can thiệp vào logic làm sạch ở Silver.
* `src/ml/`, `src/drift/`, `src/llm/`, `src/agents/`, `apps/` (Phase 2):
  chứa logic ML, drift, LLM/agent và các deployable API/UI; tách biệt khỏi
  pipeline dữ liệu lõi. Airflow chỉ có thin wrappers tại `dags/phase2/`, còn
  business logic luôn nằm trong các Phase 2 roots trên.

### B. Tách biệt Schema Cơ sở dữ liệu (Database Isolation)
Trong PostgreSQL cục bộ, chúng ta phân chia dữ liệu thành hai Schema độc lập:
1. `project_metadata`: Chứa các bảng quản trị của Phase 1 (`pipeline_run_log`, `data_quality_result`, `failed_records`, `schema_version_registry`).
2. `ml_metadata`: Sẽ được khởi tạo ở Phase 2 để lưu trữ thông tin huấn luyện (`ml_model_runs`, `feature_drift_metrics`, `batch_prediction_history`).
Điều này đảm bảo Phase 2 không làm thay đổi hoặc ảnh hưởng tới các bảng kiểm định chất lượng dữ liệu của Giai đoạn 1.

### C. Ghi đè Phân vùng động (Dynamic Partition Overwrite)
Khi viết dữ liệu Parquet ra local MinIO, PySpark luôn sử dụng phương thức ghi đè theo phân vùng (`overwrite` mode):
```python
df.write.mode("overwrite").parquet("s3a://financial-distress-lake/gold/fact_financial_statement/")
```
Giúp việc chạy lại hoặc bổ sung thêm dữ liệu huấn luyện lịch sử (Backfill) của Phase 2 không sinh ra dữ liệu trùng lặp trong kho lưu trữ Gold.

---

## 3. Quy tắc prompt Spec-Driven Development cho Coding Agent

Để tránh lỗi **Vibe-prompting** (prompt mơ hồ làm agent tự diễn dịch sai business rules), bạn phải tuân thủ nghiêm ngặt quy tắc giao tiếp sau với Agent:

1. **Cung cấp Spec trước**: Luôn đính kèm file `mini_coursework.md` (hoặc `coursework.md` ở Phase 2) vào Context của Agent ở mỗi Session mới.
2. **Acceptance Criteria (AC) dạng Testable**: Mọi tính năng phải được đặc tả theo định dạng bắt buộc của Nexlab:
   $$\text{WHO} \longrightarrow \text{ACTION} \longrightarrow \text{RESULT}$$
   * *Ví dụ đúng*: "Khi PySpark job chạy `silver_to_gold` ➔ Cột `debt_to_asset` phải được tính bằng `total_liabilities / total_assets`, định dạng Float, làm tròn 4 chữ số thập phân."
   * *Ví dụ sai*: "Hệ thống phải tự động tính toán tỷ lệ nợ chính xác."
3. **Quy tắc sửa Test**: Nếu test FAIL, tuyệt đối không được yêu cầu agent sửa expected value trong file test để pass. Phải đối chiếu lại Spec. Nếu Spec đúng ➔ bắt buộc agent sửa code logic cho đến khi test pass.

---

## 4. Nexlab AGENTS.md (Hiến pháp dự án - Constitution File)

Khối bên dưới là ví dụ lịch sử dành cho Phase 1 local-first, không phải bản
constitution hiện hành. Tệp [`../AGENTS.md`](../AGENTS.md) ở repository root là
nguồn có thẩm quyền và đã mở rộng rõ ràng cho explicit Phase 2.

Dưới đây là nội dung tệp `AGENTS.md` (hoặc `CLAUDE.md` / `.cursorrules` tương đương) được tối ưu hóa dưới 150 dòng. Hãy commit file này vào thư mục gốc của repository để Coding Agent đọc ở mỗi đầu session:

```markdown
# Financial Distress Data + AI System Constitution (AGENTS.md)

This is the project constitution. Read this at the start of every session.
Strictly adhere to the Spec-Driven Development (SDD) principles defined herein.

## 1. Core Technology Stack
- Orchestrator: Apache Airflow (Local Docker)
- Streaming: Apache Kafka (Single-node KRaft in Docker)
- Batch Processing: PySpark (Local mode with S3A connector)
- Operational Metadata: PostgreSQL (Local in Docker, schema: 'project_metadata')
- Object Storage: MinIO (Local S3-compatible, endpoint: http://minio:9000, credentials: minioadmin/minioadmin)
- Local Query Engine: DuckDB (via DBeaver using httpfs extension)

## 2. Directory Structure Conventions
- dags/: Airflow DAG definition files
- src/: Core Python modules
  - src/collectors/: Online API/WebSocket collectors and source adapters
  - src/generator/: Test fixtures and fallback synthetic generators only
  - src/streaming/: Kafka consumer and producer logic
  - src/transforms/: PySpark Bronze-to-Silver and Silver-to-Gold transform logic
  - src/quality/: Data quality check scripts (Severity policy: Hard vs Soft fail)
  - src/catalog/: MinIO bucket structure and DuckDB view registrations
  - src/ml/: [Phase 2 Only] ML Model training, inference, and drift monitoring
- sql/: Initialization SQL files for PostgreSQL schema and DuckDB views
- tests/: Automated PyTest suite (Unit and Integration tests)

## 3. Extensibility & Coding Rules
- Spec First: Never write code without checking docs/mini_coursework.md (Phase 1) or docs/coursework.md (Phase 2).
- Loose Coupling: Phase 2 ML code must exist solely inside 'src/ml/' and not modify Phase 1 pipelines.
- Database Separation: Maintain clean distinction between 'project_metadata' schema (Phase 1) and 'ml_metadata' schema (Phase 2).
- Local-first & Free: Never write code importing cloud-only packages (AWS Athena Boto3, AWS Glue APIs). Use local DuckDB & local Postgres schemas.
- Idempotency: All PySpark writes to MinIO must use .mode("overwrite") on partition boundaries.
- Test Seeds: Write unit tests with PyTest before implementing core logic. Test seeds must fail before writing code.
- Acceptance Criteria Format: Ensure all behaviors adhere to: WHO -> ACTION -> RESULT.
```

---

## 5. Bản ánh xạ nâng cao: Nexlab Playbook ➔ GitHub Spec-Kit

Để đảm bảo khả năng tương thích tối đa với bộ công cụ của **GitHub Spec-Kit**, bảng dưới đây ánh xạ chi tiết các tài liệu của dự án và các phase của Nexlab vào quy trình 5 bước tiêu chuẩn của Spec-Kit:

| Spec-Kit Step | Ý nghĩa / Phạm vi | Tài liệu dự án tương ứng | Phase Nexlab tương ứng |
|---|---|---|---|
| **1. Constitution** | Quy định bất di bất dịch, coding rules, stack | [AGENTS.md](../AGENTS.md) / `CLAUDE.md` | **PH-4: SDD Setup** |
| **2. Spec** | Đặc tả mức cao: Cái gì (What) & Tại sao (Why) | [idea.md](./idea.md) & [coursework_proposal.md](./coursework_proposal.md) | **PH-0: Discovery** & **PH-1: PRD** |
| **3. Plan** | Thiết kế kỹ thuật chi tiết: Như thế nào (How) | [mini_coursework.md](./mini_coursework.md) & [coursework.md](./coursework.md) | **PH-2: Tech Architecture** & **PH-3: Design** |
| **4. Tasks** | Danh sách tác vụ nhỏ, testable checklist | Mục *Suggested order* (Checklist triển khai) trong các spec | **PH-4 ➔ PH-5 Transition** |
| **5. Code** | Code thực tế chạy được và vượt qua test | Script trong `src/`, `dags/`, `sql/` | **PH-5: Sprint** & **PH-6: Deploy** |

### Cách tận dụng các công cụ tự động của Spec-Kit:
Nếu bạn sử dụng Spec-Kit CLI (`specify`) hoặc các Extension tích hợp Copilot/Cursor:
1. **Lệnh `/specify`**: Sử dụng để tạo cấu trúc template từ `docs/spec.md` này.
2. **Lệnh `/plan`**: Sử dụng khi bắt đầu phát triển một Module cụ thể (ví dụ: `src/transforms/silver_to_gold.py`) để Agent đọc kế hoạch từ `mini_coursework.md` và sinh ra technical plan cục bộ.
3. **Lệnh `/tasks`**: Dùng để phân rã Plan thành danh sách file cần sửa kèm theo các testcase tương ứng, khớp chính xác với quy định về **Test Seeds** của Nexlab.

---

## 6. Hướng dẫn sử dụng `spec.md` này trong phát triển dự án

Khi bạn hoặc Agent bắt tay vào thực hiện code:
1. **Bước 1**: Copy phần cấu hình ở Mục 4 và ghi vào tệp `AGENTS.md` ở thư mục gốc dự án.
2. **Bước 2**: Khi ra lệnh cho Agent viết code cho bất cứ DAG hay Script nào thuộc Phase 1, hãy gõ câu lệnh:
   > *"Đọc file `AGENTS.md` và `docs/mini_coursework.md`. Tiến hành viết kiểm thử tự động (test seed) trong `tests/` cho tính năng [Tên tính năng], đảm bảo test chạy FAIL. Sau đó viết code xử lý để pass test."*
3. **Bước 3 (Khi chuyển sang Phase 2)**: Bạn chỉ cần gõ câu lệnh:
   > *"Dự án bắt đầu chuyển sang Phase 2. Đọc `AGENTS.md`, `docs/coursework.md`, hai rubric CSV và rubric matrix. Code mới chỉ được viết trong `src/ml/`, `src/drift/`, `src/llm/`, `src/agents/`, `apps/`, thin wrappers `dags/phase2/`, và schema `ml_metadata`; không sửa hành vi Phase 1."*
