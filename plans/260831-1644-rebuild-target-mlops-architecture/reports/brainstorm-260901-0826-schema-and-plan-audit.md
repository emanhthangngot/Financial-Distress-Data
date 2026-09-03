---
title: "Audit toàn diện: plan rebuild + data model Phase 1"
date: 2026-09-01
type: brainstorm
status: advisory
supervisor: kongming
scope: plans/260831-1644-rebuild-target-mlops-architecture + platform .chema
---

# Audit toàn diện — plan rebuild và data model Phase 1

## Tóm tắt (đọc phần này là đủ để ra quyết định)

Plan `260831-1644` **đúng về mặt hạ tầng, sai về mặt trọng tâm**. Nó điều tra rất kỹ vCPU,
namespace, phiên bản CRD — nhưng **không có một dòng nào về thiết kế dữ liệu**, và còn chủ động
đóng băng data model hiện tại (`plan.md:72` G-3, `plan.md:87` N-5). Trực giác của bạn về primary
key / cột / bảng là đúng, và vấn đề nghiêm trọng hơn bạn nghĩ: **cái ERD bạn đang nhìn không phải
là schema mà hệ thống thực sự chạy.**

Ba phát hiện quyết định:

1. **Surrogate key là hàng chết.** `company_key` / `company_version_key` được ghi vào mọi dòng
   fact nhưng **không có join hay check nào dùng tới**. Toàn bộ hệ thống join bằng `ticker`.
2. **Silver dedup xoá sạch lịch sử restatement**, khiến "Point-in-Time Leakage Guard" —
   novel idea được chấm điểm của dự án — **không thể phát hiện nguồn rò rỉ lớn nhất**, và
   luôn báo xanh.
3. **Bằng chứng schema là bằng chứng giả.** `scripts/build_schema_evidence.py` chạy DDL vào một
   DuckDB rỗng, insert đúng 2 dòng hard-code, để **toàn bộ bảng fact trống**, rồi assert
   `foreign_key_count >= 4` từ `information_schema`. Nó không thể fail vì bất kỳ lý do nào liên
   quan tới pipeline.

Cộng thêm: plan cần **82–119 ngày công** nhưng chỉ còn **48 ngày làm việc** tới 2026-11-06, và bị
chặn bởi một gate quota GCP nằm ngoài tầm kiểm soát.

**Khuyến nghị: sửa data model trước, mua đúng lượng hạ tầng mà model yêu cầu, cắt phần còn lại.**

---

## 1. Contract của việc này

| Trường | Nội dung |
|---|---|
| **Outcome** | Một project thống nhất (bỏ ranh giới platform data store, **một** evidence tree; ML track và LLM track cùng đọc một bộ bảng Gold. |
| **Constraints** | Cửa sổ credit đóng 2026-11-06 (48 ngày làm việc). Quota GCP hiện tại `CPUS_ALL_REGIONS=12` vs sàn always-on 13–18 vCPU. Một người vận hành. ~100 điểm LLM đã có, không được mất. `AGENTS.md` và `plan.md` hiện đang **cấm** sửa data contract. |
| **Non-goals** | Không đạt 100% fidelity với `fdd-architecture-full-4k.png`. Không xây registry định danh doanh nghiệp nếu không có nguồn dữ liệu thật. Không viết lại plan từ đầu. |
| **Acceptance** | (a) Leakage guard **fail** trên một restatement được seed, rồi **pass** sau khi lọc vintage; (b) mọi FK khai báo đều resolve trên bảng **có dữ liệu**, zero orphan; (c) grep `company_version_key` trên toàn bộ bundle nộp bài trả về **một** câu chuyện nhất quán; (d) chạy lại training pin theo knowledge-time cho ra feature byte-identical ở hai ngày khác nhau. |

---

## 2. Audit plan `260831-1644`

### 2.1 Những gì plan làm tốt (kiểm chứng được)

| Claim | Trạng thái |
|---|---|
| Mini rubric có 44 dòng chấm điểm | **ĐÚNG.** File có 84 dòng vật lý → 47 record logic → 47−1 header−2 = 44. Khớp `phase-01-contracts.md:75-76`. |
| `rubric-matrix.csv` = 60 LLM executed + 57 ML design_only, 19 cột | **ĐÚNG.** 117 data row, 19 cột, đếm khớp chính xác. |
| Inventory 83 component, mỗi component thuộc đúng một phase | **CÓ THẬT**, `debate-proposal.md:880-882`. |
| Dependency graph acyclic | **ĐÚNG** theo frontmatter mọi phase file; mọi cạnh đều tăng chỉ số phase. |
| Gate G0 / R-3 / R-5 (export trước khi nâng KServe) | Thiết kế gate tốt, có kỷ luật. |

Audit C19/C20 trong `debate-audit.md:25-26` để UNPROVEN — nay đã **PROVEN**, plan đúng.

### 2.2 Mâu thuẫn nội tại: G-2 vs N-5

- `plan.md:71` G-2 — "Clean cutover — ... **one table format (Iceberg)**; zero shims"
- `plan.md:87` N-5 — "No changes to platform .ronze/Silver/Gold Parquet semantics (**Iceberg runs parallel**)"

Một đường Parquet chạy song song **chính là** một shim. Hai điều khoản này không thể cùng đúng.
`phase-07-web-analytics.md:50` chỉ gỡ *Gold* Parquet reader — Bronze/Silver Parquet tồn tại vĩnh
viễn. Kết quả thực tế: **hai table format, không phải một.** Đây không phải lỗi diễn đạt, nó là
lý do vì sao plan không thể tạo ra một platform thống nhất.

### 2.3 Plan không có bất kỳ công việc data-model nào

Duyệt toàn bộ 10 phase file: **không có** một acceptance criterion nào về primary key, grain,
kiểu dữ liệu, chuẩn hoá, hay chiến lược partition. Phân loại 57 AC:

- Hạ tầng "còn sống" (Argo Synced/Healthy, CRD tồn tại, pod chạy): đa số.
- Hành vi pipeline (idempotent, dedup, canary chia traffic): thiểu số.
- **Đúng đắn về mô hình dữ liệu: 0.**

Gần nhất là `AC-P2-3` (ghi hai lần cùng kết quả) và `AC-P2-4` (Bronze append-only) — kiểm tra
*cơ chế ghi*, không kiểm tra *mô hình*.

`plan.md:195` khoá mục tiêu 10–50M dòng, nhưng `src/io/paths.py:13-14` quy định layout là
**một file duy nhất cho mỗi dataset** (`{bucket}/{layer}/{dataset}/data.parquet`), không partition.
Một file Parquet 50M dòng ≈ 1–5 GB: mỗi lần đọc là full-file, mỗi lần append phải ghi lại toàn bộ,
không ghi song song được. Plan không có công việc nào xử lý điều này.

### 2.4 Số học lịch trình

```
Effort theo frontmatter:  2+4+10+8+8+14+8+10+10+8  =  82 ngày (min)
                          3+6+14+12+12+20+12+14+14+12 = 119 ngày (max)
Plan tuyên bố:            ~8 tuần × 30h/tuần        = 240 giờ
82 ngày × 6h                                        = 492 giờ
119 ngày × 6h                                       = 714 giờ
                                            → vượt 2.0× – 3.0×
```

Còn 2026-09-01 → 2026-11-06 = **48 ngày làm việc**. Đường tới hạn tuần tự
P0→P1→P2→P3→P5→P8→P9 riêng nó đã là 60–83 ngày (`plan.md:133` xác nhận chỉ P3∥P4 song song
được, mà chỉ có một người làm nên song song thực tế ≈ 0).

Chưa tính: độ trễ duyệt quota, rework, và phần sửa data model.

**Biện pháp giảm rủi ro duy nhất của plan cho gate G0 là "dừng lại"** (`phase-00-gates.md:25`,
branch C). Một plan có deadline cứng mà contingency là halt thì không phải là plan.

---

## 3. Audit data model Phase 1

### 3.1 Surrogate key không làm gì cả

```
company_key         = sha256(upper(ticker))[:16]        src/transforms/keys.py:14-17
company_version_key = sha256(f"{ticker}|{valid_from}")  src/transforms/gold/dim_company.py:51
```

Một surrogate key tồn tại để làm ba việc. Chấm điểm cái hiện tại:

| Mục đích | `sha256(ticker)[:16]` |
|---|---|
| Tách fact khỏi biến động của natural key | **Trượt.** Là hàm thuần tuý của `ticker`. Ticker đổi → key đổi. Hai pháp nhân khác nhau từng dùng mã `ABC` nhận **cùng một key**. |
| Khoá join gọn | **Trượt ngược.** 16 byte hex vs ticker 3 ký tự = 3 byte → **lớn hơn 5 lần** cái nó thay thế. Nhân với 10–50M dòng. |
| Mang định danh phiên bản | Không — đó là việc của `company_version_key`. |

**Và không có gì đọc nó.** Đây là phần quan trọng nhất:

| Nơi | Khoá thực sự dùng | Bằng chứng |
|---|---|---|
| PIT feature join | `ticker` | `src/transforms/features/pit.py:111-119` |
| Silver dedup | `(ticker, report_period)` | `src/jobs/stage1_evidence_job.py:387`, `stage1_spark_lakehouse_job.py:655` |
| Gold uniqueness check | `["ticker","report_period"]` | `src/jobs/stage1_dq_job.py:75` |
| OBT join nhãn | `(ticker, report_period)` | `src/transforms/gold/obt_company_quarter_risk.py:18,21` |
| Referential integrity | `company_key` — **kiểm tra chính nó** | `src/jobs/stage1_dq_job.py:78-83` |

Consumer duy nhất của `company_key` là một check RI so nó với chính tập key sinh ra từ nó — một
tautology, chỉ fail được nếu SHA-256 mất tính tất định.

**Kết luận: đây không phải "chọn sai surrogate key", mà là "surrogate key không cần tồn tại".**
Mọi cách "sửa" mà vẫn băm từ `ticker` (thêm salt, kéo dài, ghép exchange) đều tái tạo y hệt lỗi cũ.

### 3.2 Silver dedup phá huỷ lịch sử — và vô hiệu hoá novel idea

Quy tắc (bị **`AGENTS.md` bắt buộc**): giữ dòng có `created_ts` mới nhất cho mỗi
`(ticker, report_period)` — `src/transforms/silver/core.py:31-38`, `silver/spark.py:96-99`.

Đây không phải deduplication. Deduplication loại các dòng **giống nhau**. Cái này loại các dòng
**khác nhau ở đúng những con số quan trọng nhất** và chỉ giữ dòng mới nhất.

**Ca thử quyết định — một restatement:**

> Công ty X nộp Q2-2023 vào tháng 8/2023, equity 500 tỷ. Tháng 3/2024 kiểm toán buộc điều chỉnh:
> equity Q2-2023 thực ra là 120 tỷ. Công ty vỡ nợ Q4-2024.
>
> Ngày 2023-09-01 thị trường biết 500 tỷ. Ngày 2024-04-01 mới biết 120 tỷ.
> Model dùng con số 120 tỷ gắn nhãn "có sẵn từ 2023" đã được cho biết trước đáp án.

Sau Silver, chỉ còn dòng 120 tỷ, nhưng `event_timestamp` của nó vẫn là mốc Q2-2023.

**`src/ml/leakage_guard.py:84-90` chỉ so sánh hai cột timestamp**, không bao giờ nhìn giá trị.
Nó thấy `feature_ts <= label_ts` → **PASS**. Trên một dataset đang rò rỉ. Theo thiết kế.

Ba lỗi cộng dồn:

1. `_parse_timestamp` trả `datetime.min` khi null/không parse được (`pit.py:100-104`,
   `silver/core.py:50`) — **fail open, không bao giờ raise**.
2. `event_timestamp` và `report_release_date` đều nằm trong danh sách **nullable** của contract
   (`src/metadata/schema_registry.py:118-130`) — đường đi bệnh lý chính là đường đi hợp lệ.
3. `date_key` fallback về `f"{fiscal_year}-01-01"` (`fact_financial_statement.py:19-23`) — một
   báo cáo Q4-2024 công bố tháng 3/2025 bị đóng dấu 2024-01-01, **lệch 14 tháng về quá khứ**.

Và rò rỉ này **không phân bố đều**: doanh nghiệp kiệt quệ tài chính restate nhiều hơn hẳn doanh
nghiệp khoẻ mạnh *(giả định từ literature kế toán, chưa kiểm chứng trong repo)*. Rò rỉ tập trung
vào lớp positive. AUC đo được tăng, hiệu năng out-of-sample không tăng, và guard báo xanh.

**Novel idea flagship là một guard đúng, lắp sai tầng — nằm ngay sau phép biến đổi đã phá huỷ
thông tin mà nó cần.**

### 3.3 Bằng chứng schema là hư cấu

`scripts/build_schema_evidence.py:19-24`:

```python
connection.execute(sql_path.read_text(...))          # chạy DDL vào DuckDB rỗng
connection.execute("""
    INSERT INTO gold.dim_company VALUES
      ('aaa-v1', 'aaa', 'AAA', 'Alpha Old', '2025-01-01', '2026-01-01', false),
      ('aaa-v2', 'aaa', 'AAA', 'Alpha New', '2026-01-01', NULL, true)
    """)                                             # đúng 2 dòng hard-code
```

Rồi lines 73-80 assert `table_count >= 15 and foreign_key_count >= 4` đọc từ `information_schema`.
**Toàn bộ bảng fact trống.** Sáu FK không bao giờ được một dòng dữ liệu nào chạm tới.
`CHECK (feature_event_timestamp <= event_timestamp)` — bất biến PIT duy nhất được khai báo trong
schema (`sql/schema_evidence.sql:102`) — nằm trên một bảng zero row.

Artifact này chỉ chứng minh rằng các câu `CREATE TABLE` parse được. Nó **không thể fail** vì
pipeline. Test từng pin nó (`tests/test_schema_evidence.py`) **đã bị xoá** — chỉ còn `.pyc`.

### 3.4 Mâu thuẫn nằm bên trong bundle đã nộp

| Nguồn | Khẳng định |
|---|---|
| `docs/mini_coursework.md:565` | "Facts currently store `company_key` and `date_key` **only**. They do **not** store `company_version_key`." — line 579: "an **explicit** Stage 1 design choice, not an accidental omission" |
| `docs/02_schema_design.md:205` | Cùng nội dung — **đúng với code** |
| `sql/schema_evidence.sql:63,70,77` | `company_version_key NOT NULL REFERENCES gold.dim_company(...)` × 3 |
| `docs/schema-design.md:11-14` | "Gold facts ... reference `dim_company.company_version_key`" |
| `docs/evidence/final/coursework-final-*/queries/schema.json:10` | `"foreign_key_count": 6` |

Cả **ba** bản frozen bundle (`20260731T0030`, `20260802T0115`, `20260802T0130`) đều mang mâu thuẫn
này. Đây là loại lỗi nguy hiểm nhất: người chấm phát hiện được mà **không cần mở code**, và một
khi phát hiện thì nghi ngờ lan sang mọi claim khác trong bundle.

Kiểm tra rủi ro điểm: **không** có rubric row nào trích dẫn `foreign_key_count`. Nhưng mini rubric
dòng 42 có row chấm điểm **"Relationship between dim & fact tables (You can simply export via
DBeaver or similar tools) — 2 điểm"**. Đây chính là row mà fixture giả đang phục vụ.

### 3.5 Các lỗi mô hình còn lại

| # | Vấn đề | Bằng chứng | Vì sao sai |
|---|---|---|---|
| 1 | Grain của `fact_financial_statement` thiếu trục phiên bản | `stage1_dq_job.py:75` unique trên `(ticker, report_period)` | Restatement bị xoá; chạy lại training không tái lập được; `holdout-v1` đóng băng *dòng nào* chứ không đóng băng *giá trị trong dòng* → locked decision #7 không bảo đảm được điều nó hứa |
| 2 | `valid_from_ts` là thời điểm **ingest**, không phải thời điểm hiệu lực | `dim_company.py:45` (`= created_ts`) | Tên cột nói dối. Phiên bản dimension sinh ra theo lúc chạy pipeline, không theo sự kiện nghiệp vụ |
| 3 | SCD2 lai không khai báo | `dim_company.py:29` chỉ track `(industry, sector, exchange, delisted_flag)` | `company_name` được lưu nhưng **không** track → âm thầm là type-1 nằm trong dòng type-2 |
| 4 | Mã hoá dư thừa không ràng buộc | `schema_registry.py:108-117` | `report_period`("2024Q1") + `fiscal_year` + `fiscal_quarter` — ba cột cho một sự kiện, không gì bắt chúng nhất quán |
| 5 | Tiền là `DOUBLE` | `sql/schema_evidence.sql:14-15,22,44,72`, `docs/07_data_contracts.md:120-124` | Double chỉ chính xác nguyên đến 2^53≈9.0e15. Tổng tài sản một ngân hàng VN ≈ 2e15 VND — còn 4.5× dư địa. **Tổng toàn thị trường ~1600 công ty vượt 2^53.** Hệ quả cụ thể: đẳng thức `assets = liabilities + equity` cho residual khác 0, nên DQ check phải chọn một tolerance tuỳ tiện không có cơ sở |
| 6 | `check_id TEXT PRIMARY KEY` = `uuid4()` | `sql/init_ops.sql:18`, `src/metadata/metadata_writer.py:357` | PK không ràng buộc gì (uuid4 không bao giờ đụng). Ghi DQ **không idempotent** — chạy lại cùng `run_id` nhân đôi dòng. Khoá đúng phải là `(run_id, dataset_name, check_name)` |
| 7 | `ops` có **zero** foreign key | `sql/init_ops.sql` toàn bộ | `run_id` trong `data_quality_result`, `failed_records`, `source_request_log` tham chiếu `pipeline_run_log` **chỉ bằng quy ước đặt tên** |
| 8 | `schema_version_registry.is_current` không có ràng buộc | `init_project_metadata.sql:40-48` | Không gì ngăn hai dòng cùng `is_current=TRUE` cho một dataset. Cần partial unique index |
| 9 | `TIMESTAMP` naive vs `TIMESTAMPTZ` | `init_project_metadata.sql` vs `init_ml_metadata.sql` | Domain là VN (UTC+7), pipeline chạy UTC → **lớp lỗi 7 giờ âm thầm**, rơi đúng vào `freshness_lag_minutes` và mọi so sánh PIT |
| 10 | `status`/`severity`/`request_status` là free text | `init_project_metadata.sql`, `dq_checks.py:18-19` | Không CHECK, không enum. Tập giá trị hợp lệ chỉ tồn tại trong đầu người viết code |
| 11 | Không partition, một file/dataset | `src/io/paths.py:13-14` | Mâu thuẫn trực tiếp với mục tiêu 10–50M dòng và với `write_partitioned_parquet` ở `gold/parquet.py:13` — hai quy ước đường dẫn cùng tồn tại |

---

## 4. Ba lựa chọn, có đánh đổi

### Phương án A — Chạy plan như đã duyệt, sửa schema sau

- **Chi phí sửa tăng đơn điệu theo từng phase.** Sau P2 là migrate lakehouse; sau P3 thêm Kafka
  topic schema + Flink state + Feast registry (`ml.feast_registry_revision` giữ
  `registry_digest` và `feature_view_count` — đổi schema là vô hiệu cả hai); sau P9 là regenerate
  evidence tree **lần thứ hai**.
- **Plan đang cấm chính cái sửa đó** (G-3, N-5). Bạn sẽ dành 82–119 ngày thực thi một plan có
  acceptance criteria **bảo vệ** cái bug.
- Giả định chịu lực: cửa sổ credit đủ dài. **Đã sai** — thiếu 1.7–2.5×.

### Phương án B — Đưa redesign vào trước P2, re-baseline *(khuyến nghị)*

- P1 hiện đã là "Contracts, ADRs, unified evidence tree", 4–6 ngày, **0 vCPU**, và đã mang ba
  ADR amendment làm **exit criteria** (R-6). Một redesign data model *chính là* ADR + bump
  contract version + regenerate evidence. Không phải dị vật ghép vào — là bắt P1 làm đúng việc
  mà tiêu đề của nó đã hứa.
- Giải quyết luôn mâu thuẫn G-2/N-5 theo hướng duy nhất tạo ra platform thống nhất: **bỏ N-5**,
  migrate ngữ nghĩa platform .ào Iceberg, G-2 lần đầu tiên trở nên khả thi.
- P1 giãn thành 9–12 ngày. P2 xây Bronze→Silver→Gold trên contract v2 — **không phải việc thêm**,
  là *cùng khối lượng P2* nhắm vào mục tiêu đã sửa.
- **Đánh đổi:** phải tuyên bố `BREAKS-LOCK` với N-5 và G-3, mở lại phán quyết Round-4 của arbiter.
  Ồn ào về mặt thủ tục.
- **Giả định chịu lực:** redesign diễn đạt được *bên trong* cấu trúc exit-criteria của P1.
- **Điều kiện hỏng trước tiên:** nếu redesign làm **thay đổi tập bảng Gold** (thêm/bớt bảng, chứ
  không chỉ cột) khiến phải viết lại hàng loạt `evidence_path` / `validation_command`, thì R-4 trở
  nên bất khả thi và bạn đang re-plan dưới một cái tên khác.
  **Đặt tripwire rõ ràng: viết lại quá ~20 dòng matrix thì dừng, chuyển sang phương án C có chủ ý**
  — thay vì phát hiện điều đó ở giữa P2.

### Phương án C — Bỏ plan, lập lại từ data model

- Sạch sẽ về mặt trí tuệ nhưng vứt bỏ phần dùng lại được: cấu trúc verify quota của Gate G0,
  exit criteria ADR của P1, assertion grep R-4, ma trận 161 dòng với `validation_command` +
  `behavioral_assertion` từng dòng, và bốn vòng debate tạo tính chính danh thủ tục.
- Tốn 5–10 ngày trên tổng 48, đổi lấy **một tài liệu, không phải một deliverable**.

**Chọn B.** Nhỏ nhất mà thoả contract, và rẻ nhất để từ bỏ nếu tripwire kích hoạt.

---

## 5. Mô hình dữ liệu đề xuất

### 5.1 Định danh — **xoá surrogate, đừng sửa nó**

| Tier | Việc | Công |
|---|---|---|
| **Tier 0** *(làm)* | Xoá `company_key`, `company_version_key` khỏi mọi bảng fact/feature. Khai báo `ticker` là khoá tự nhiên — trong contract, trong docs, trong ERD. Chi phí ≈ 0 vì **không có gì join trên chúng**. | ~0.5 ngày |
| **Tier 1** *(làm)* | Thêm `exchange` + cửa sổ hiệu lực niêm yết vào dimension để chuyển sàn HNX→HOSE **biểu diễn được** thay vì bị ghi đè âm thầm. | ~1 ngày |
| **Tier 2** *(chỉ khi có nguồn thật)* | Bảng registry curated ~1600 dòng `(ticker, exchange, valid_from, valid_to, entity_id)`, ticker là thuộc tính SCD của entity chứ không ngược lại. | 3–5 ngày |

**Đánh đổi Tier 2:** bạn đang khẳng định một ánh xạ liên tục pháp nhân mà **không có ground truth**.
Registry với ngày chuyển sàn đoán mò là **một hư cấu mới thay cho hư cấu cũ** — tệ hơn là khoá
trung thực theo ticker.
**Hỏng trước tiên khi** không tìm được nguồn ngày huỷ/tái niêm yết. Khi đó **dừng ở Tier 1** và ghi
ticker-reuse là giới hạn đã biết, chưa xử lý. Một giới hạn được ghi nhận ăn điểm cao hơn một bịa
đặt không được ghi nhận.

### 5.2 Fact mang khoá bền, **không** mang khoá phiên bản

Khoá phiên bản trên fact đóng băng dòng đó vào một version dimension. Khi `industry` bị phân loại
lại, `company_version_key` mới sinh ra và **mọi fact lịch sử trỏ vào version đã bị thay thế** —
hoặc bạn viết lại lịch sử (mất ý nghĩa SCD2), hoặc fact âm thầm trỏ sai.

Tệ hơn: version sinh theo **thời điểm ingest** (§3.5 #2), nên định danh chiều của một fact trở
thành hàm của việc bạn tình cờ chạy pipeline lúc nào. Đó là bug về khả năng tái lập đội lốt
data modeling.

Thực hành chuẩn: fact mang **khoá bền**; version đúng được resolve lúc query bằng as-of join theo
khoảng hiệu lực. `docs/02_schema_design.md:205-213` **đã mô tả đúng như vậy**. Tài liệu đó đúng;
tài liệu nói ngược lại thì sai.

- **Đánh đổi:** as-of join đắt hơn equi-join và dễ sai tinh vi (bao gồm/loại trừ biên `valid_to_ts`).
- **Hỏng trước tiên khi** ai đó viết as-of join với `valid_to_ts` inclusive một bên, exclusive bên
  kia → nhân đôi dòng tại biên version. Chặn bằng **một** view resolution duy nhất có test, cộng
  một assertion uniqueness trên output.

### 5.3 Bi-temporality — **bắt buộc trên fact, không cần trên dimension**

Fact cần hai trục thời gian **độc lập**:

- **Valid time** — kỳ mà con số mô tả (`report_period`, đã có).
- **Knowledge time** — thời điểm *phiên bản này của những con số này* trở nên biết được
  (`known_from`; **hiện không tồn tại ở bất cứ đâu trong repo**).

Một trục không thể mã hoá hai sự thật độc lập. Đây không phải sự thanh lịch kiến trúc — đây là
biểu diễn tối thiểu của câu hỏi.

**Grain đúng của `fact_financial_statement`:**

```
một dòng cho mỗi (entity, report_period, statement_variant, knowledge_ts)
```

`statement_variant` phân biệt hợp nhất/riêng lẻ, đã kiểm toán/chưa — contract **đã có**
`statement_type` nullable (`schema_registry.py:127`) nhưng không dùng trong khoá. Tối thiểu, nếu
không lấy được ngày công bố thật: `(ticker, report_period, source_version)` với `source_version`
tăng đơn điệu theo lần ingest.

Thêm `is_latest_vintage BOOLEAN` là cờ **dẫn xuất**, cộng assertion uniqueness
`(ticker, report_period) WHERE is_latest_vintage` trong DQ gate. Đây là câu trả lời một dòng cho
"nhưng downstream đang mong đợi một dòng mỗi quý": giữ nguyên sự tiện lợi, bỏ đi sự phá huỷ.

**Trên dimension:** SCD2 hiện tại **đã là** knowledge time. Không cần thêm trục. Nhưng **tên đang
nói dối** — đổi `valid_from_ts`/`valid_to_ts` → `known_from_ts`/`known_to_ts`. Chi phí ≈ 0
(`tests/test_naming_convention.py` **không** grep chuỗi này — đã kiểm tra).

### 5.4 Ý tưởng tốt nhất trong toàn bộ audit này

Locked decision #6 nhắm 10–50M dòng. Nhưng quy mô thật là ~1600 ticker × ~40 quý ≈ **64.000** dòng
báo cáo — thiếu ba bậc độ lớn. Nghĩa là con số 10–50M **chắc chắn phải sinh tổng hợp**.

Vậy thì: **cho data generator sinh ra restatement.** Nhiều vintage cho mỗi
`(ticker, report_period)`, với biên độ và độ trễ hiệu chỉnh thực tế.

Việc này biến một công việc chạy-cho-đủ-volume thành **màn trình diễn sống của mô hình bi-temporal**,
đồng thời cho leakage guard một thứ **thật sự bắt được**. Bạn có thể trưng ra delta AUC trước/sau
làm bằng chứng rằng guard là chịu lực. Đó là artifact "novel idea" mạnh hơn hẳn một bộ so sánh
timestamp.

---

## 6. Xử lý phần hư cấu — xếp hạng **(c) > (b) > (a)**

**Hạng 1 — (c) Redesign model rồi regenerate cả hai.** Chi phí evidence biên ≈ 0: plan **đã**
purge và regenerate toàn bộ evidence tree (locked decision #1b, G-5), và cả 117 dòng đều giữ
`validation_command` + `behavioral_assertion` nên "re-run is contract-only, not re-design"
(`plan.md:146`). Bạn chỉ trả tiền cho redesign — thứ mà §4 và §5 đã lập luận độc lập.

> **Hỏng trước tiên khi** redesign trượt qua exit gate của P1 và evidence tree được regenerate trên
> một model migrate dở dang. Khi đó bạn có **hai** hư cấu thay vì một, và cái mới thì tươi hơn,
> khó phát hiện hơn.
> **Luật cứng: không capture evidence trước khi contract được đóng băng và generator có khả năng fail.**

**Hạng 2 — (b) Sửa fixture và docs xuống đúng những gì code làm.** Trạng thái trung thực rẻ nhất.
Nhưng ship một star schema **không có ràng buộc tham chiếu nào** là artifact yếu hơn thấy rõ, và
mini rubric dòng 42 chấm 2 điểm cho "Relationship between dim & fact tables".
**Giảm thiểu:** không cần ship zero FK — §7 trao cho bạn **bốn FK thật, trên bảng có dữ liệu**.
Đổi sáu FK giả trên bảng rỗng lấy bốn FK thật trên bảng có dòng là **lãi ròng** ở bất kỳ cách đọc
trung thực nào.

**Hạng 3 — (a) Bắt code sinh ra FK.** Tệ nhất. Nó xi măng hoá đúng cái lỗi mà §5.2 bảo phải đảo
ngược, tốn công thật trên mọi fact builder, và làm model đúng về sau **đắt hơn**. Bạn đang trả tiền
để biến một khẳng định sai thành đúng.

### Bất kể chọn gì, làm ngay việc này (giá trị/giờ cao nhất trong repo)

**Làm cho `build_schema_evidence.py` có khả năng fail.** Load Gold Parquet **thật** vào DuckDB rồi
assert: mọi FK khai báo resolve với zero orphan; mọi bảng có `row_count > 0`; CHECK PIT của
`feat_company_unified` đúng trên dòng thật; uniqueness đúng trên grain thật. Khoảng nửa ngày.
Nó biến artifact yếu nhất — một assertion trên `information_schema` — thành mạnh nhất: một chứng
minh toàn vẹn tham chiếu trên dữ liệu thật.

---

## 7. Gộp `ops` và `ml`

**Cái gì thực sự vỡ khi gộp thô:**

1. **`data_quality_result` trùng tên.** Hai schema định nghĩa cùng tên cột và cùng
   `check_id TEXT PRIMARY KEY`. Gộp vào một namespace → đụng PK. Khác nhau đúng một điểm:
   `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` vs `TIMESTAMPTZ DEFAULT now()`.
2. **Lệch kiểu timestamp toàn bộ bề mặt** — xem §3.5 #9. **Đây là thứ sẽ thực sự cắn bạn.**
3. **Hai instance Postgres vật lý.** `ml` chạy trên `pgvector/pgvector:pg16`. Gộp đòi
   instance sống sót phải có `pgvector` và di chuyển vector 384 chiều + HNSW index.
4. **`AGENTS.md:11` cấm cross-write.** **Đã kiểm tra: chỉ được thực thi bằng văn xuôi** —
   `AGENTS.md:11` và `docs/project-file-map.md:386`. **Không có test hay code nào enforce.**
   Bán kính ảnh hưởng thấp: sửa docs, không phải migrate code.
5. **Gần như không có toàn vẹn tham chiếu để bảo tồn** — §3.5 #7.

**Gộp an toàn tối thiểu:**

- **Một database, hai schema** — không phải một schema phẳng. Đổi tên `ops` → `ops`,
  `ml` → `ml`. Được một connection, FK xuyên schema, một truy vấn lineage; giữ được tách
  biệt namespace và quyền sở hữu. Đổi tên cũng xoá luôn từ vựng "phase" — đó chính là mục đích.
- **TIMESTAMPTZ khắp nơi, UTC, không ngoại lệ.** Migrate cột `ops` bằng
  `AT TIME ZONE 'UTC'` **tường minh**, không bao giờ `ALTER TYPE` trần (cast trần diễn giải lại giá
  trị naive theo timezone của session — đúng cái bug bạn đang sửa). **Đây là hạng mục không thương
  lượng; làm nó kể cả khi không làm gì khác trong mục này.**
- **Gộp `data_quality_result` thành một bảng trong `ops`**, thêm `track TEXT NOT NULL ∈
  {mini, ml, llm}`, PK = `(track, check_id)`. Hai bảng DQ là vết thương tự gây rõ nhất của việc
  chia đôi: chất lượng dữ liệu là chất lượng dữ liệu.
- **Thêm đúng bốn FK** — tất cả đều thật, đều rẻ, đều trên bảng có dữ liệu:
  - `ops.data_quality_result.run_id → ops.pipeline_run_log.run_id`
  - `ops.failed_records.run_id → ops.pipeline_run_log.run_id`
  - `ops.source_request_log.run_id → ops.pipeline_run_log.run_id`
  - giữ `ml.rag_chunk.document_hash → ml.rag_document.document_hash`

  **Bốn cái này là sự thay thế trung thực cho sáu cái hư cấu ở §6.**
- **Dừng ở đó.** Không gộp `ml.label_table` vào `ops`. Không đụng HNSW index.

> **Đánh đổi:** FK trên `run_id` buộc dòng run phải insert trước mọi dòng phụ thuộc. Script ad-hoc
> ghi DQ ngoài một run đã đăng ký sẽ fail.
> **Giảm thiểu đã có sẵn:** cả ba cột `run_id` đều **nullable**, và Postgres không enforce FK trên
> NULL. Giữ nullable → có toàn vẹn cho run đã đăng ký, suy giảm êm cho run ad-hoc. Thêm một DQ check
> trên **tỷ lệ** `run_id` NULL thay vì một ràng buộc cứng.

**Việc chia đôi có bào chữa được không?** Trước đây có — hai instance, hai vòng đời độc lập, khi
các phase là hai deliverable riêng. **Bây giờ thì không**, trong một bài nộp mà luận điểm là một
platform thống nhất. Việc chia đôi *chính là* ranh giới phase bạn muốn xoá, nhúng vào tầng dữ liệu;
người chấm mở hai file DDL sẽ thấy `-- platform schema` ở dòng comment đầu tiên.

---

## 8. Phạm vi nhỏ nhất vẫn chứng minh được "unified platform" (~22–28 ngày)

**Đóng khung lại luận điểm.** "Unified platform" được chứng minh bằng *một entity model, một trục
thời gian, một feature contract, một metadata store, một lineage, một evidence tree* — với ML track
và LLM track cùng đọc **cùng** bảng Gold và cùng ghi run vào **cùng** metadata schema. Đó là một
luận điểm bảo vệ được. 83 component trên GKE không phải luận điểm; nó là một danh sách mua sắm — và
chính danh sách đó tạo ra cái gate quota có thể chặn đứng bạn.

| # | Deliverable | Ngày |
|---|---|---|
| 1 | Data model thống nhất: định danh Tier 0+1, fact bi-temporal với `known_from`, trục vintage trong grain, cờ `is_latest_vintage`, bảng Iceberg đã partition | 6–7 |
| 2 | Một metadata DB, hai schema, TIMESTAMPTZ toàn bộ, bốn FK thật, một `data_quality_result` (§7) | 2–3 |
| 3 | Một lần chạy end-to-end có orchestration: Bronze→Silver→Gold→features→labels, PIT guard chuyển sang so knowledge time và **trình diễn fail** trên một restatement được seed | 3–4 |
| 4 | ML track trên compute đơn node hiện có: train → MLflow tracking → registry → promotion gate trên holdout đóng băng → drift check | 4–5 |
| 5 | LLM track: RAG trên **cùng entity của warehouse**, citation guard, eval harness, một endpoint phục vụ | 4–5 |
| 6 | Evidence: một cây, regenerate, **mọi assertion đều có khả năng fail** (§6) | 3–4 |

Mục 3 "trình diễn fail" là viên ngọc: một guard bạn có thể **cho xem nó bắt được** một rò rỉ thật
đáng giá hơn nhiều một guard chưa bao giờ fail.

### Thứ tự cắt

Cắt theo thứ tự này. Dừng khi phần còn lại vừa với 30% slack.

| # | Cắt | Tiết kiệm | Lý do |
|---|---|---|---|
| 1 | Migrate Jenkins (P8) | 10–14d | Không có giá trị phân biệt so với GitHub Actions đang chạy; churn thuần trên deadline. Giữ Argo CD |
| 2 | Istio mesh + Vault/ESO (P4) | 8–12d + ~½ sàn always-on | Tiêu thụ always-on lớn nhất (5–6 + 2–3 vCPU, `plan.md:156-157`) — **đây chính là phase tạo ra gate quota có thể halt plan.** Thay bằng NetworkPolicy + K8s Secrets + một ADR ghi lại đánh đổi |
| 3 | Kafka/Debezium/Flink CDC (P3) | 8–12d | **Nguồn dữ liệu là hàng quý.** CDC dưới giây trên báo cáo tài chính quý là kiến trúc trình diễn, và người chấm sẽ nói đúng như vậy. Giữ đường micro-batch, ghi streaming là target có điều kiện kích hoạt |
| 4 | llm-d, KServe 0.14.1→0.18, A/B routing (P6 phần upgrade) | 6–9d | Phục vụ một model trên cái đang chạy. Cũng xoá luôn ranh giới không-thể-revert duy nhất của plan (R-5) |
| 5 | Trino + Superset + dbt (P7) | 10–14d | DuckDB trên Gold + một dashboard tối thiểu chứng minh cùng năng lực analytics |
| 6 | Ray + Kubeflow Pipelines (P5 phần orchestration) | 8–12d | Giữ MLflow + một training job thường. Dữ liệu thật ~64k dòng (§5.4) — distributed training không biện minh được, và người chấm làm phép tính sẽ nhận ra |
| 7 | Observability — giảm chứ không cắt | 4–6d + 2–3 vCPU | Chỉ Prometheus + Grafana; bỏ Loki, Jaeger, OTel collector |
| 8 | **CUỐI CÙNG MỚI CẮT — Iceberg** | — | Cố ý đảo ngược. Iceberg là hạng mục hạ tầng duy nhất **trả tiền cho việc sửa data model**: snapshot isolation, time travel, schema evolution cho bạn knowledge-time ở mức bảng gần như miễn phí, và làm G-2 ("one table format") trở thành sự thật. Giữ Iceberg, cắt mọi thứ quanh nó |

> **Đánh đổi toàn bộ danh sách cắt:** bạn sẽ **không** khớp `fdd-architecture-full-4k.png`, và G-1
> ("every component and edge implemented") trở nên bất khả thi theo cấu trúc.
> **Hỏng trước tiên khi** rubric chấm điểm **theo component** chứ không theo năng lực được chứng
> minh. **Kiểm tra điều này trên ma trận 161 dòng trước khi cam kết cắt** — rebuttal của arbiter ghi
> nhận 21 dòng LLM được ghim vào serving artifact (`plan.md:20`). Nếu vậy, dẫn lại thứ tự cắt theo
> *số dòng rủi ro trên mỗi ngày tiết kiệm* thay vì thứ tự của tôi. Một giờ làm việc, và là khác biệt
> giữa một nhát cắt tốt và một phát đoán.

---

## 9. Ba quyết định tệ nhất

### 1. Quy tắc dedup keep-latest của Silver

`silver/core.py:31-38`, `silver/spark.py:96-99`, `stage1_evidence_job.py:387` — **bắt buộc bởi
`AGENTS.md`**.

Nó vô hiệu hoá novel idea flagship (§3.2), làm lệch training set về phía lớp positive, khiến chạy
lại không tái lập được, và xoá đi thứ có lẽ là feature distress mạnh nhất hiện có.

Điều làm nó *tệ nhất* chứ không chỉ *lớn nhất*: nó bị đóng băng bởi `AGENTS.md` và đóng băng lần
nữa bởi `plan.md` N-5 và G-3. **Governance của dự án đang chủ động bảo vệ cái bug.** Bất kỳ ai
phát hiện ra nó cũng bị ràng buộc thủ tục phải giữ nó lại.

**Đáng lẽ:** dedup trên khoá tự nhiên đầy đủ **bao gồm vintage** — giữ mọi phiên bản khác biệt,
thêm `is_latest_vintage` làm cờ *dẫn xuất*, để consumer tự chọn. Chi phí: Silver phình theo tỷ lệ
restatement (một chữ số % trên dữ liệu thật). Nhược điểm: không có.

### 2. Surrogate key rỗng nghĩa + khẳng định toàn vẹn không thực thi + bài nộp tự mâu thuẫn

`keys.py:14-17` sinh khoá lớn hơn 5× cái nó thay thế; `stage1_dq_job.py:78-83` là consumer duy nhất
và kiểm tra nó với chính nó; `build_schema_evidence.py:19-24,73-80` insert 2 dòng, để fact rỗng, rồi
assert từ `information_schema`; `mini_coursework.md:565,579` phủ nhận thẳng thừng cái mà
`docs/evidence/final/coursework-final-*/queries/schema.json:10` khẳng định trong **cùng một bundle**.

Ba lỗi chồng lên nhau, mỗi cái khuếch đại cái sau. Mâu thuẫn tài liệu *bên trong một bộ artifact
đã nộp* là loại tổn hại lớn nhất, vì nó phát hiện được bởi người **không mở code**.

**Đáng lẽ:** không mint surrogate cho tới khi có một join cần nó; khai báo `ticker` là khoá và nói
nhất quán ở mọi nơi; và xây generator evidence trên output pipeline thật ngay từ ngày đầu, để số
FK là một **phép đo** chứ không phải một **lời nhắc lại DDL**.

### 3. Duyệt một plan 83 component / 82–119 ngày, đóng băng data model, trong khi hứa zero shim

`plan.md:71` G-2 hứa "one table format (Iceberg); zero shims"; `plan.md:87` N-5 bắt buộc Parquet
chạy song song — **một đường Parquet song song theo định nghĩa là một shim.** Hai điều khoản trong
cùng một tài liệu không thể cùng đúng. G-3 cấm luôn cái sửa mà báo cáo này khuyến nghị.

Lỗi sâu hơn là **chọn sai proxy**: plan tối ưu **số lượng component** — dễ đo, dễ trình diễn — thay
vì **tính đúng đắn của dữ liệu**, thứ mà một rubric data engineering thực sự đang hỏi. Bốn vòng
debate đối kháng đã dành cho kế toán vCPU, tiền tố namespace, và phiên bản CRD của KServe; qua cả
bốn vòng, **không có gì trong debate trail chất vấn xem model Gold có đúng hay không.** Cuộc debate
nghiêm túc, và nhắm sai mục tiêu.

**Đáng lẽ:** sửa model trước; mua đúng lượng hạ tầng mà các bảo đảm của model *yêu cầu* (Iceberg cho
time travel, MLflow cho run lineage, một Postgres cho metadata); và coi ảnh kiến trúc là một target
được ghi nhận kèm bảng gap trung thực, chứ không phải một cam kết. Một bài nộp nói "đây là 12
component, đây là lý do từng cái tồn tại, đây là 71 cái tôi cố ý không xây và tại sao" là một
artifact kỹ thuật mạnh hơn 83 component sống dở — và làm được trong 48 ngày.

---

## 10. Checklist

**Trước khi cam kết bất cứ gì (≈1 giờ — 3/4 đã chạy xong, kết quả ở dưới):**

- [x] Rubric row schema-design (`docs/11_rubric_completion_spec.md:493-501`) có bắt buộc FK không?
      → Acceptance là *"sees SCD2 fields, feature timestamp fields, **relationships**, and naming
      conventions"*. Mini rubric dòng 42 chấm **2 điểm** cho "Relationship between dim & fact tables".
      **→ Phương án (b) đơn thuần làm mất 2 điểm; (c) kiếm lại chúng một cách trung thực.**
- [x] `tests/test_naming_convention.py` có grep `valid_from` / `company_key` không? → **KHÔNG.**
      Đổi tên là miễn phí.
- [x] Bất biến "never cross-write" được enforce ở đâu? → **Chỉ văn xuôi**, `AGENTS.md:11` +
      `docs/project-file-map.md:386`. Không test, không code. Bán kính ảnh hưởng thấp.
- [x] Có rubric row nào trích `foreign_key_count: 6` không? → **KHÔNG.** Sáu FK giả không được
      dòng điểm nào trích dẫn trực tiếp.
- [ ] Tính *số dòng rủi ro trên mỗi ngày tiết kiệm* cho từng mục trong thứ tự cắt §8, đối chiếu ma
      trận 161 dòng. **Việc này thay thứ tự của tôi bằng thứ tự của bạn.**

**Rồi, theo thứ tự:**

1. **Gửi yêu cầu tăng quota GCP ngay hôm nay** — nó là cột chống dài nhất bên ngoài và miễn phí để
   bắt đầu. Đừng để bất kỳ quyết định nào khác chặn nó.
2. Thực hiện §6(b) như một sửa chữa toàn vẹn trong ngày: gỡ sáu FK giả, đồng bộ
   `docs/schema-design.md` về `mini_coursework.md:565`. Bạn sẽ không bao giờ ôm một artifact sai
   trong lúc redesign đang chạy.
3. Làm `build_schema_evidence.py` có khả năng fail: load Gold thật, assert zero orphan,
   `row_count > 0`, CHECK PIT đúng trên dòng thật.
4. Tuyên bố `BREAKS-LOCK` với N-5 và G-3, lấy mâu thuẫn G-2/N-5 làm căn cứ. Sửa G-3 thành
   "immutable **after P1 exit**".
5. Viết ADR entity/time: xoá `company_key`; ticker là khoá khai báo (Tier 0+1); `known_from` trên
   fact; grain `(ticker, report_period, statement_variant, knowledge_ts)`; `is_latest_vintage` dẫn
   xuất; đổi tên `valid_from_ts` → `known_from_ts`.
6. Bump contract `financial_statements` lên v2 trong `schema_version_registry` — cơ chế versioning
   **đã tồn tại** và chưa từng được dùng đúng mục đích.
7. Dạy data generator sinh restatement. Việc này vừa nuôi mục tiêu 10–50M dòng vừa cho leakage guard
   một thứ thật để bắt.
8. Chuyển PIT guard sang so `known_from` với thời điểm quyết định nhãn. Làm `_parse_timestamp`
   **raise** thay vì trả `datetime.min`. Xoá fallback `f"{fiscal_year}-01-01"` của `date_key` và
   fail to tiếng.
9. Gộp metadata DB theo §7. Bốn FK. TIMESTAMPTZ.
10. Partition Gold. Tiền → `DECIMAL(38,2)`.
11. Regenerate evidence tree — **một lần**, sau khi contract đóng băng.

---

## 11. Chỉ số thành công

- **Leakage guard là chịu lực:** nó **fail** trên một restatement được seed, và **pass** sau khi
  áp bộ lọc vintage. Một guard chưa bao giờ fail không phải là bằng chứng.
- **Delta rò rỉ đo được:** AUC holdout trên feature latest-vintage trừ AUC trên feature as-known.
  Khoảng cách đáng kể là chứng minh định lượng rằng model cũ đang rò rỉ.
- **Mọi assertion evidence đều có khả năng sai:** với mỗi artifact, bạn gọi được tên thay đổi
  pipeline nào sẽ làm nó fail. Artifact schema-evidence hiện tại trượt bài test này hoàn toàn.
- **Zero mâu thuẫn trong bộ nộp:** grep toàn văn `company_version_key` trả về một câu chuyện nhất quán.
- **Tái lập được:** chạy lại training pin theo mốc knowledge-time cho ra feature byte-identical ở
  hai ngày khác nhau.
- **Toàn vẹn tham chiếu là thật:** mọi FK khai báo resolve trên bảng có dữ liệu, zero orphan, kiểm
  chứng bằng một truy vấn người chấm chạy được.
- **Lịch trình:** còn ~30% slack ở mốc 60% thời gian. Nếu không, **cắt ngay mục tiếp theo trong §8
  thay vì nén khâu verification** — verification chính là thứ đang được chấm.

---

## 12. Giả định và câu hỏi chưa giải quyết

| # | Giả định | Độ tin cậy | Điều gì làm thay đổi câu trả lời |
|---|---|---|---|
| A-1 | Rubric thưởng năng lực được chứng minh hơn số lượng component | **Trung bình** | Đọc ma trận 161 dòng. Nếu nhiều dòng ghim vào artifact component cụ thể, phải dẫn lại thứ tự cắt §8. **Đây là phép kiểm có đòn bẩy cao nhất với tài liệu này.** |
| A-2 | Một người, ~30h/tuần | **Cao** | Hai người biến P3/P4 thành song song thật, đưa tỷ lệ từ 2.5× xuống ~1.6× — vẫn vượt, nhưng danh sách cắt ngắn đi ~2 mục |
| A-3 | Yêu cầu quota khó được duyệt đủ, đặc biệt `PREEMPTIBLE_CPUS 0→28` | **Trung bình** | Duyệt đủ trong ~5 ngày gỡ được hard stop nhưng **không** sửa được việc vượt 1.7–2.5× effort. Vẫn phải cắt |
| A-4 | Doanh nghiệp kiệt quệ restate nhiều hơn hẳn | **Trung bình-cao** (literature, chưa kiểm chứng trong repo) | Nếu tỷ lệ restate không tương quan với nhãn, rò rỉ vẫn thật nhưng không lệch, và AUC bị thổi ít hơn. Sửa bi-temporal vẫn bắt buộc vì lý do tái lập |
| A-5 | Ticker reuse giữa các pháp nhân khác nhau là hiếm nhưng có thật ở VN; chuyển sàn thì phổ biến | **Trung bình** | Nếu chuyển sàn cũng hiếm, Tier 1 thành tuỳ chọn. Nếu reuse phổ biến, Tier 2 thành bắt buộc và bạn phải tìm nguồn registry |
| A-6 | Ba bundle frozen dưới `docs/evidence/final/` đều là artifact được chấm | **Trung bình** | Nếu chỉ bản mới nhất được chấm, mâu thuẫn §3.4 hẹp đi 3 lần — nhưng vẫn hiện diện trong bản được chấm. Kết luận không đổi |
| A-7 | ~100 điểm LLM phụ thuộc evidence row, không phụ thuộc phần hư cấu schema | **Trung bình-cao** — đã kiểm một phần: **không** rubric row nào trích `foreign_key_count` | Nếu một dòng LLM nào trích `schema.json`, phương án (b) mất điểm trực tiếp và (c) thành lựa chọn duy nhất |
| A-8 | "Ngày công" trong bảng effort ≈ 6 giờ tập trung | **Trung bình** | Ở 8h/ngày vượt ~2.3–3.3×; ở 4h/ngày vượt ~1.2–1.7×. **Mọi cách đọc đều cho ra plan vượt cam kết.** Kết luận không nhạy với giả định này |

**Câu hỏi cần bạn quyết:**

1. Có chấp nhận tuyên bố `BREAKS-LOCK` với N-5 và G-3 để mở đường cho việc sửa data model không?
   Không có nó thì mọi khuyến nghị ở §5 đều bị chính plan cấm.
2. Ưu tiên nào cao hơn: **điểm rubric tối đa theo số component**, hay **một hệ thống đúng và bảo vệ
   được**? Câu trả lời quyết định thứ tự cắt ở §8.
3. Có nguồn dữ liệu thật nào cho ngày huỷ/tái niêm yết và chuyển sàn của ticker VN không? Có → Tier 2
   khả thi. Không → dừng ở Tier 1 và ghi nhận giới hạn.

---

*Advisory này được lập với giám sát của `kongming` theo cờ `--advise`. Mọi khẳng định về code và
bằng chứng đều đã được kiểm chứng trực tiếp trên repo tại `path:line` được trích dẫn. Các phán đoán
về thị trường VN và literature kế toán được đánh dấu là giả định.*
