# Research Report: Schema Design Audit — Financial Distress Data v2

Ngày: 2026-09-02. Đối tượng: quyết định schema trong
`plans/260831-1644-rebuild-target-mlops-architecture/phase-02-data-model.md` đối chiếu
`sql/schema_evidence.sql`, `sql/init_project_metadata.sql`, `sql/init_ml_metadata.sql`,
`src/transforms/`, `src/io/paths.py`.

## Table of Contents

- [Executive Summary](#executive-summary)
- [Research Methodology](#research-methodology)
- [Findings F1-F16](#findings)
- [Comparative Analysis](#comparative-analysis)
- [Implementation Recommendations](#implementation-recommendations)
- [Resources & References](#resources--references)
- [Appendix A — Naming convention đề xuất](#appendix-a--naming-convention-đề-xuất)
- [Appendix B — Kết luận per câu hỏi](#appendix-b--kết-luận-per-câu-hỏi)
- [Unresolved Questions](#unresolved-questions)

## Executive Summary

P2 sửa đúng **vấn đề lớn nhất** (bi-temporal, vintage-preserving dedup, DECIMAL money, TIMESTAMPTZ,
FK thật, deterministic `check_id`, partitioning). Không tranh cãi phần đó.

Nhưng **quyết định primary key là sai theo consensus Kimball**, và nó sai vì một lỗi lập luận cụ thể:
P2 gộp hai key khác nhau (`company_key` = hash(ticker), `company_version_key` = hash(ticker|valid_from))
rồi áp phê bình của cái thứ nhất lên cả hai. `company_version_key` **thật sự** là SCD2 version
surrogate hợp lệ. Xoá nó khỏi fact = mọi join fact→dim thành range join, ERD mất FK khai báo được,
và mâu thuẫn mini row 42 (được chấm điểm).

Về naming: repo hiện có **ba** convention suffix timestamp cùng tồn tại (`_ts` 21 chỗ, `_timestamp`
19 chỗ, `_at` ~20 chỗ), P2 thêm cái **thứ tư** (`known_from`, không suffix) và dùng **ba tên cho một
concept** trong cùng một file (`known_from`, `known_from_ts`, `knowledge_ts`). Đổi
`valid_from_ts`/`valid_to_ts` → `known_from_ts`/`known_to_ts` **phá mini row 40 (2đ)** vì rubric ghi
đúng tên cột cũ.

Về bảng: ERD graded thiếu 3/12 dataset gold; **không fact table nào có primary key**; Bronze lại
**có** PK (mâu thuẫn append-only + duplicate simulation của chính project); `silver.companies` PK
`ticker` **phá input của SCD2**; `distress_labels` vi phạm naming convention được chấm điểm (mini 43).

Tổng: 16 finding, trong đó 4 chạm trực tiếp điểm rubric, 5 là lỗi correctness, 7 là convention.

## Research Methodology

- Nguồn web: 5 truy vấn (Kimball surrogate/durable key · bi-temporal SQL:2011 naming · Iceberg
  schema/decimal/partitioning 2025 · DW table & timestamp naming convention · Feast PIT correctness).
- Nguồn repo: `sql/*.sql`, `src/transforms/keys.py`, `src/transforms/gold/*.py`,
  `src/metadata/schema_registry.py`, `src/io/paths.py`, `phase-02-data-model.md`, 3 rubric CSV.
- Khoảng thời gian tài liệu: 2011-2026, ưu tiên 2024-2026.
- Từ khoá: surrogate key, durable key, SCD Type 2, SQL:2011 system-versioned, application time,
  Iceberg decimal widening, hidden partitioning, medallion naming, Feast `created_timestamp_column`.

---

## Findings

### F1 — [BLOCKER] Xoá surrogate khỏi fact trái consensus Kimball; lập luận của P2 sai một phần

**P2 nói** (`phase-02:57-59`): *"A surrogate key exists to decouple facts from natural-key
volatility, to be a compact join key, and to carry version identity. `sha256(upper(ticker))[:16]`
fails all three."*

**Repo có hai key, không phải một:**

| Key | Sinh ra ở | Nội dung | Đánh giá |
|---|---|---|---|
| `company_key` | `keys.py:14-17` | `sha256(upper(ticker))[:16]` | Fail cả 3 test. P2 đúng. |
| `company_version_key` | `dim_company.py:50` | `sha256(f"{ticker}\|{valid_from}")[:16]` | **Pass test thứ 3** — nó mã hoá version identity. P2 sai khi gộp. |

`company_version_key` là **đúng** SCD2 version surrogate: PK của `dim_company`
(`schema_evidence.sql:50`), và là FK từ 3 fact table (`:63,:70,:77`).

**Consensus web (Kimball):** fact table **luôn** join bằng surrogate key của dimension; natural key
giữ trong dimension như attribute mô tả, **không** dùng làm join key của fact. Lý do: independence
khỏi source system, historical accuracy cho SCD2, và integer/compact join nhanh hơn character join.

**Hệ quả nếu xoá theo P2** (`phase-02:41-42`, `ticker` là declared natural key trên fact):

1. Mọi join fact→dim thành **range join**:
   `ON f.ticker = d.ticker AND f.known_from >= d.known_from_ts AND f.known_from < COALESCE(d.known_to_ts,'infinity')`.
   Spark không broadcast/hash-join range predicate tốt → shuffle-heavy ở 10-50M row (đúng scale P4 nhắm).
2. Join có thể trả **>1 row** nếu SCD2 window chồng nhau. Không có exclusion constraint nào chặn.
3. Point-in-time dimension attribution thành trách nhiệm của **mọi consumer, mọi query, mãi mãi**.
   Đây chính là loại lỗi mà D-3/D-4 đang cố diệt, chỉ đổi chỗ.
4. **ERD mất FK khai báo được** từ fact→dim. mini row 42 (2đ) chấm *"Relationship between dim & fact
   tables"*. Không có key thì không có relationship để export.

**D-1 là defect về *usage*, không phải về *design*.** Bằng chứng của chính P2 — "nothing reads
`company_key`" — chứng minh join **đang** dùng sai, không chứng minh key sai. Fix đúng: làm join
dùng nó, không phải xoá nó.

**Đề xuất (theo web):** giữ 3 lớp key theo đúng Kimball:

```
dim_company
  company_version_key   PK, surrogate  ← fact join bằng cái này
  company_durable_key   durable/supernatural key, bất biến qua mọi version
                        ← dùng để GROUP BY entity xuyên version
  ticker                natural key, attribute mô tả (+ UNIQUE với is_current)
```

Xoá `company_key` (`sha256(ticker)` — vô nghĩa). Giữ `company_version_key`. Thêm
`company_durable_key` nếu cần group xuyên version — web gọi đây là *durable supernatural key*, và
nó **không** dùng để join fact.

### F2 — [BLOCKER, mất điểm] Rename `valid_from_ts`/`valid_to_ts` phá mini row 40

mini rubric row 40, 2 điểm, nguyên văn:

> `Dim table with SCD 2  (valid_from_ts, valid_to_ts, is_current)`

`phase-02:43` đổi thành `known_from_ts`/`known_to_ts`.

**Semantic thì P2 đúng:** D-7 chứng minh `valid_from_ts` hiện là ingestion timestamp, tức là
**system/transaction time**, không phải valid time. Tên cột đang nói dối.

**Nhưng tên thay thế không đúng chuẩn.** SQL:2011 và consensus DW:

| Trục | Concept | Suffix chuẩn | SQL:2011 |
|---|---|---|---|
| Valid time | business / effective time | `_valid_from`, `_valid_to` | `APPLICATION_TIME` |
| System time | transaction / audit time | `_sys_start`, `_sys_end` | `SYSTEM_TIME` |

`known_from_ts` không nằm trong từ vựng chuẩn nào. Web cảnh báo trực tiếp: *"'knowledge time' and
'as of' can mean different things depending on the vendor or internal team nomenclature"* — tức đây
là thuật ngữ nội bộ, phải document, không phải chuẩn.

**Đề xuất:** giữ `valid_from_ts` / `valid_to_ts` / `is_current` **đúng tên rubric** trên
`dim_company`, và giải thích semantic trong data dictionary + ADR-017. Nếu muốn chính xác thuật ngữ,
thêm alias view `dim_company_sys` phơi `sys_start`/`sys_end`. Đổi tên cột được chấm điểm sang một
thuật ngữ không chuẩn = mất 2 điểm mà không được chuẩn hơn.

**Trên fact thì ngược lại:** thêm trục knowledge time là **mới**, không phá gì. Ở đó dùng tên chuẩn
được — xem F3.

### F3 — [BLOCKER] Ba tên cho một concept, và convention suffix thứ tư

Trong **cùng** `phase-02-data-model.md`:

| Dòng | Tên | Ngữ cảnh |
|---|---|---|
| `:38` | `known_from` | "Facts carry a knowledge-time axis (`known_from`)" |
| `:43` | `known_from_ts` | rename của `dim_company` |
| `:39`, `:92` | `knowledge_ts` | grain của `fact_financial_statement` |

Ba identifier, một trục thời gian. `phase-05:61` lại dùng `feature.known_from`, `phase-02:152` dùng
`feature.known_from`. Đây là thứ trở thành vĩnh viễn sau khi contract re-freeze ở P2 exit
(`phase-02:32-33`).

**Repo-wide đã có ba convention suffix** (đo bằng grep trên `sql/*.sql` + `schema_registry.py`):

| Suffix | Số lần | Ở đâu |
|---|---|---|
| `_ts` | 21 (`created_ts`, `updated_ts`, `fetched_ts`, `quarantined_ts`, `last_event_ts`…) | `ml`, gold tables |
| `_timestamp` | 19 (`event_timestamp`, `feature_event_timestamp`, `latest_event_timestamp`) | Feast-mandated + gold |
| `_at` | ~20 (`created_at`, `checked_at`, `started_at`, `ended_at`, `requested_at`) | `ops` |

Tức `ops` (tên mới của `ops`) dùng `_at`, `ml` (`ml`) dùng `_ts`. P2 thống nhất
**type** (TIMESTAMPTZ, `phase-02:45`) nhưng **không** thống nhất **tên**. Rồi thêm `known_from` không
suffix = cái thứ tư.

**Consensus web:** *"Suffix consistency: using `_from` and `_to` (or `_start` and `_end`)
consistently across all tables makes it easier for BI tools and analysts to write standardized
joins."* Và: *"Choose one convention, document it, and enforce it."*

**Đề xuất — chốt một lần, ghi vào ADR-017:**

| Loại | Suffix | Ví dụ |
|---|---|---|
| TIMESTAMPTZ, business/valid time | `_ts` | `report_release_ts` |
| TIMESTAMPTZ, system/knowledge time | `_ts` với tiền tố `known_` hoặc `sys_` | `known_from_ts`, `known_to_ts` |
| DATE | `_date` | `trading_date`, `listing_date` |
| Feast contract | **giữ nguyên** | `event_timestamp`, `created_timestamp` |

Chọn `_ts` (không `_at`) vì: `ml` schema đã dùng nó, gold tables đã dùng nó, và `_at` chỉ hơn ở
convention app-framework (Rails/Laravel) chứ không phải DW. Migration `_at` → `_ts` chỉ trong
`ops` schema, 8 cột, làm cùng lượt TIMESTAMPTZ ở step 6.

**Không** để `known_from` không suffix và **không** dùng `knowledge_ts` — chọn `known_from_ts` cho cả
fact và dim, một tên duy nhất.

### F4 — [Correctness] PK `(track, check_id)` có leading column vô dụng

`phase-02:109`: `ops.data_quality_result` PK `(track, check_id)`, `track ∈ {mini, ml, llm}`.
`phase-02:156-157`: `check_id` = deterministic hash of `(run_id, dataset_name, check_name)`.

Nếu `check_id` là hash của một triple đã unique thì **`check_id` một mình đã unique**. `track` trong
PK không constrain gì. Tệ hơn: leading column cardinality = 3 → index prefix vô dụng, mọi FK/lookup
phải mang thêm một cột.

Repo hiện tại làm **đúng**: `data_quality_result (check_id TEXT PRIMARY KEY)`
(`init_project_metadata.sql:18`). P2 đang làm nó tệ hơn.

**Đề xuất — chọn một:**
- (a) PK = `check_id`, `track` là cột `NOT NULL` + `CHECK (track IN ('mini','ml','llm'))` + index riêng. **Khuyến nghị.**
- (b) Đưa `track` vào hash: `check_id = hash(track, run_id, dataset_name, check_name)`, PK = `check_id`.

Cả hai giữ nguyên ý định "merged from both schemas" mà không có composite PK giả.

### F5 — [Correctness, mâu thuẫn nội bộ] Bronze có PRIMARY KEY

`schema_evidence.sql:6`: `bronze.companies (ticker VARCHAR PRIMARY KEY)`.

Mâu thuẫn ba nguồn:

| Nguồn | Yêu cầu |
|---|---|
| `AGENTS.md` | "Bronze: append-only" |
| `AC-P4-4` | "Bronze writer → receives a duplicate business key → appends only; **both vintages survive**" |
| mini row 7 (2đ) | "Simulate another offline data problem (Ví dụ: 2% duplicate rate)" |

PK trên Bronze cấm cả ba. Consensus medallion: *"Raw events land in bronze exactly as they arrived.
Silver cleans, conforms, and deduplicates them."*

P2 rewrite `schema_evidence.sql` (`phase-02:162`) nhưng **không chỗ nào** nói Bronze phải bỏ PK.

**Đề xuất:** Bronze **không** PK, không UNIQUE. Grain document là
`(business_key, created_ts, ingest_batch_id)` — khai báo trong data dictionary, không enforce.
Bronze chỉ có `NOT NULL` trên business key + `created_ts`.

### F6 — [Correctness] `silver.companies (ticker PRIMARY KEY)` phá input của SCD2

`schema_evidence.sql:28`. Nhưng `merge_dim_company` (`dim_company.py:24-40`) cần **nhiều snapshot
mỗi ticker, sort theo `created_ts`** để phát hiện change:

```python
rows = sorted(snapshots, key=lambda item: (str(item["ticker"]).upper(), _utc_iso(item["created_ts"])))
...
changed = previous is None or any(previous.get(f) != row.get(f) for f in tracked)
```

PK `ticker` ở Silver ⇒ đúng một snapshot/ticker ⇒ `changed` luôn False sau lần đầu ⇒ **SCD2 không bao
giờ sinh version thứ hai**. Đây là lý do cấu trúc khiến mini row 40 (SCD2) khó chứng minh bằng dữ
liệu thật.

P2 fix trục vintage cho `financial_statements` (`phase-02:147-149`) nhưng **không đề cập
`silver.companies`**.

**Đề xuất:** `silver.companies` PK = `(ticker, created_ts)` — hoặc `(ticker, snapshot_date)` nếu
snapshot theo ngày. Đây là bảng nuôi SCD2, nó phải giữ history.

### F7 — [BLOCKER, mất điểm] Không fact table nào có primary key

`schema_evidence.sql`:

| Bảng | Dòng | PK | UNIQUE |
|---|---|---|---|
| `gold.fact_financial_statement` | 62-68 | **không** | không |
| `gold.fact_market_price` | 69-75 | **không** | không |
| `gold.obt_company_quarter_risk` | 76-81 | **không** | không |
| `gold.feat_company_financial_4q` | 82-86 | **không** | không |
| `gold.feat_company_market_30d` | 87-91 | **không** | không |
| `gold.feat_company_news_30d` | 92-96 | **không** | không |
| `gold.feat_company_unified` | 97-103 | **không** | chỉ CHECK |

P2 khai báo grain (`phase-02:92`) và thêm **DQ assertion** uniqueness (`:97`). Nhưng DQ check ≠
constraint: nó chạy sau khi ghi, ngoài transaction, và có thể bị skip.

mini row 42 (2đ) chấm *"Relationship between dim & fact tables (You can simply export via DBeaver)"*.
DBeaver export ERD từ **constraint**, không từ DQ config. Không PK + không FK ⇒ ERD export ra một tập
bảng rời.

**Đề xuất:** khai báo grain thành PK thật trong ERD graded:

```sql
CREATE TABLE gold.fact_financial_statement (
    company_version_key VARCHAR NOT NULL REFERENCES gold.dim_company(company_version_key),
    date_key            INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
    ticker              VARCHAR NOT NULL,          -- natural key, attribute
    report_period       VARCHAR NOT NULL,
    statement_variant   VARCHAR NOT NULL,
    known_from_ts       TIMESTAMPTZ NOT NULL,
    is_latest_vintage   BOOLEAN NOT NULL,
    total_assets        DECIMAL(20,2),
    total_liabilities   DECIMAL(20,2),
    created_ts          TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, report_period, statement_variant, known_from_ts)
);
CREATE UNIQUE INDEX uq_ffs_latest_vintage
  ON gold.fact_financial_statement (ticker, report_period)
  WHERE is_latest_vintage;
```

Iceberg không enforce PK — nhưng ERD Postgres/DuckDB thì có, và đó chính xác là thứ làm
`build_schema_evidence.py` **falsifiable** theo O-5. Partial unique index thay DQ check ở
`phase-02:97` cho phần chạy được trong RDBMS; giữ DQ check cho phần Iceberg.

### F8 — [Mất điểm] ERD graded thiếu 3/12 dataset gold

`paths.py:20-38` liệt kê 18 dataset (bronze 3, silver 3, gold 12). `schema_evidence.sql` có gold 9.

| Thiếu trong ERD | Có trong `paths.py` |
|---|---|
| `gold.fact_market_alert` | ✓ dòng 32 |
| `gold.fact_news_sentiment` | ✓ dòng 33 |
| `gold.distress_labels` | ✓ dòng 34 |

mini row 39 (2đ) = *"Visualize tables on all zones"*. R-4 mitigation của P2 (`phase-02:228`) nói
*"`src/io/paths.py` keeps all 18 dataset names"* — đúng, nhưng ERD vẫn thiếu 3. Rewrite ở
`phase-02:162` không nêu việc thêm.

### F9 — [Mất điểm] `distress_labels` vi phạm naming convention được chấm điểm

mini row 43 (2đ) nguyên văn: *"Naming convention (- Gold layer: `dim_`, `fact_`, `obt_`, `feat_`,
`raw_`…)"*.

| Tên hiện tại | Vấn đề |
|---|---|
| `gold.distress_labels` | **không prefix** + **số nhiều** (mọi gold table khác là số ít) |
| `gold.distress_holdout_v1` | version trong tên bảng, đồng thời P4 dùng Iceberg tag `holdout-v1` cho **cùng** mục đích → double versioning |
| `ml.label_table` | "table" trong tên bảng; redundant |

**Đề xuất:**
- `gold.distress_labels` → `gold.fact_distress_label` (hoặc khai báo prefix `label_` trong convention doc rồi dùng `gold.label_company_quarter` — nhưng rubric chỉ liệt kê 5 prefix, thêm cái thứ 6 phải giải thích).
- `gold.distress_holdout_v1` → `gold.distress_holdout`, version do Iceberg tag `holdout-v1` giữ. Một nguồn version, không hai.
- `ml.label_table` → `ml.distress_label`.

### F10 — [Convention] Plural/singular lệch giữa zone và không được khai báo

| Zone | Ví dụ | Dạng |
|---|---|---|
| bronze | `companies`, `financial_statements`, `market_prices_daily` | số nhiều |
| silver | `companies`, `financial_statements`, `market_prices_daily` | số nhiều |
| gold | `dim_company`, `fact_financial_statement`, `feat_company_unified` | số ít |

Web: không có chuẩn tuyệt đối; điều quan trọng là *"a deliberate choice and consistency"*. Kimball
practice = **số ít** cho dim/fact. Nên split "plural raw / singular modeled" thật ra là **defensible**
— nhưng nó không được viết ở đâu, nên đọc như tai nạn. mini row 43 chấm naming convention.

**Đề xuất:** khai báo tường minh trong `docs/architecture/data-model.md` (file P1 tạo từ merge
`02_schema_design.md` + `schema-design.md`, `plan.md:132`):

> Bronze/Silver mirror nguồn: số nhiều, tên feed. Gold là modeled: số ít, có prefix
> `dim_`/`fact_`/`obt_`/`feat_`/`raw_`.

Rồi thêm một lint đơn giản trong `scripts/run_quality_gates.py` để enforce. Convention không enforce
là convention chết.

### F11 — [Correctness + cost] `DECIMAL(38,2)` over-provisioned, và scale là quyết định một chiều

`phase-02:47`: "Money is `DECIMAL(38,2)`."

**Đúng ở phần lớn nhất:** DOUBLE cho money là sai (D-10). Web: *"Choose Decimal whenever precision
and accuracy are essential, such as columns holding values for amount, money"*; Iceberg DOUBLE là
IEEE 754 64-bit, có rounding error cố hữu.

**Nhưng ba chi tiết:**

1. **Scale không đổi được sau này.** Iceberg: *"Modifying the scale is not permitted, as changing the
   scale alters the underlying storage layout of the decimal bytes in Parquet or Avro, which would
   corrupt historical data reads. Promoting decimal(9,2) to decimal(18,2) is fully supported, whereas
   decimal(9,2) to decimal(9,4) is prohibited."* ⇒ **precision mở rộng được, scale thì không.**
   Nên chọn precision **nhỏ** (mở sau được) và scale **đúng ngay** (không sửa được).
   P2 làm ngược: chọn precision max (38) — thứ duy nhất có thể mở sau.
2. **Cost.** `DECIMAL(38,2)` → Parquet `FIXED_LEN_BYTE_ARRAY(16)` = 16 byte/value.
   `DECIMAL(18,2)` hoặc `(20,2)` → 8 byte. Ở 10-50M row × ~20 cột money, chênh ~1.6-16 GB. Cộng với
   bottleneck BigDecimal allocation đã biết của Iceberg (apache/iceberg#13742).
3. **Scale 2 cho VND cần lý do.** VND không có subunit lưu hành; báo cáo tài chính VN thường theo
   đơn vị đồng hoặc triệu đồng. Scale 2 lưu hai chữ số thập phân luôn `.00` — 100% waste nếu nguồn
   là số nguyên đồng. Nhưng nếu có tỷ giá/ratio thì cần. **Phải quyết và ghi lý do**, vì không sửa được.

**Đề xuất:** `DECIMAL(20,2)` cho money (±9.99×10^17 VND ≈ 38 nghìn tỷ USD, thừa sức cho tổng thị
trường ~1600 công ty), `DECIMAL(18,6)` cho ratio/rate. Ghi vào ADR-017: *precision widening là đường
thoát, scale thì không có — 2 được chọn vì X*.

Ghi chú: AC-P2-11 (`assets = liabilities + equity` khớp chính xác, không cần tolerance) thoả mãn với
**bất kỳ** DECIMAL — nó không đòi 38.

### F12 — [Modeling] Fix D-9 là băng dán, không phải fix dimensional

D-9: `report_period` + `fiscal_year` + `fiscal_quarter` mã hoá một fact ba lần trên fact table.
P2 fix (`phase-02:155`): derive `report_period` từ `(fiscal_year, fiscal_quarter)` + consistency check.

**Fix Kimball là đưa chúng vào dimension.** Và lý do chúng bị denormalize lên fact rất rõ:
`gold.dim_date` (`schema_evidence.sql:58-61`) có đúng **hai cột**:

```sql
CREATE TABLE gold.dim_date (
    date_key INTEGER PRIMARY KEY,
    calendar_date DATE UNIQUE NOT NULL
);
```

Một date dimension không có date attribute nào. Nên `fiscal_year`/`fiscal_quarter` không có chỗ nào
để ở ngoài fact.

**Đề xuất:** enrich `dim_date` (`fiscal_year`, `fiscal_quarter`, `month`, `quarter_end_date`,
`is_quarter_end`, `day_of_week`, `is_trading_day`) và/hoặc thêm `dim_fiscal_period` key
`report_period`. Fact chỉ giữ `date_key` (+ `report_period` như degenerate dimension nếu cần cho
partition). Lợi kép: mini row 39/42 có star schema thật để visualize, và consistency check ở
`phase-02:155` trở thành không cần thiết vì không còn dư thừa.

`dim_date` **không** có trong `Related Code Files` của P2 (`phase-02:138-167`). Nên nó sẽ ở nguyên
trạng hai cột.

### F13 — [Correctness] `date_key` integer đúng chuẩn, nhưng dim_date phải được populate

`keys.py:20-27` → `int(value.strftime("%Y%m%d"))`. Đây **đúng** smart integer date key kiểu Kimball.
Giữ nguyên.

Fallback `f"{fiscal_year}-01-01"` (`fact_financial_statement.py:22`, `:40`) là defect D-6, P2 sửa
thành raise (`phase-02:144`) — đúng.

**Nhưng:** `fact.date_key REFERENCES dim_date(date_key)` (`schema_evidence.sql:64`). AC-P2-9 đòi
"zero orphans". Nếu `dim_date` không được generate cho **mọi** date_key mà fact sinh ra, FK orphan.
`dim_date` không có trong `Related Code Files` của P2 và không có AC nào populate nó.

**Đề xuất:** thêm `src/transforms/gold/dim_date.py` (generate calendar 2015-2030 + fiscal attributes)
vào `Related Code Files` P2, và một AC: *"dim_date populated cho mọi date_key xuất hiện trong bất kỳ
fact table → zero orphan"*.

### F14 — [Correctness, tinh vi] Feast default tie-break **chống lại** thiết kế bi-temporal

Web (Feast):
- `event_timestamp` = upper bound **inclusive** của PIT join; Feast scan ngược tìm giá trị mới nhất tại-hoặc-trước thời điểm đó.
- `created_timestamp_column` = tie-break; **Feast chọn row có `created_timestamp` cao nhất** cho một `event_timestamp`.
- Nguyên văn về restatement: *"Feast's built-in 'last known good' logic prioritizes the most recent information by default"* — nếu cần *"seeing the world exactly as it was known at the time, rather than the corrected version"* thì **phải quản version tường minh hoặc custom filtering**.

Tức: nếu map `known_from_ts` → `created_timestamp`, Feast sẽ **luôn** chọn vintage mới nhất — đúng
hành vi leakage mà project đang cố diệt. Feast default là kẻ địch ở đây.

P2/P5 có nhận ra, nhưng chỉ ở mức **risk response**, không phải design:
`phase-05:147-150`: *"Response: repoint Feast entity timestamps to `known_from`, not
`event_timestamp`."*

**Đề xuất:** biến thành design decision tường minh trong ADR-017:
> Trong `feat_*`, `event_timestamp` = `known_from_ts` (knowledge time là trục join của Feast).
> Valid time (`report_period`) là feature/attribute, không phải trục thời gian của Feast.
> `created_timestamp` chỉ dùng để tie-break các bản ghi cùng `known_from_ts` (retry của cùng một lần ingest).

Kèm thêm: `feat_company_unified` CHECK hiện tại (`schema_evidence.sql:102`)
`feature_event_timestamp <= event_timestamp`. Với knowledge time, invariant đúng là
`feature_known_from_ts <= label_decision_ts` — một so sánh **khác**. P2 sửa leakage guard
(`phase-02:152-153`) nhưng CHECK trong ERD không nằm trong `Related Code Files`.

### F15 — [Convention] `ml.label_table` — "table" trong tên bảng

`init_ml_metadata.sql:10`. PK `(ticker, event_timestamp, label_version)` (`:18`) thì **tốt** — natural
composite PK, đúng grain, có version axis. Chỉ tên là dở.

**Đề xuất:** `ml.distress_label`. Giữ nguyên PK.

Ghi chú tích cực: `ml` nhìn chung **tốt hơn** `ops` ở mọi mặt P2 định sửa —
đã TIMESTAMPTZ, đã `_ts` suffix, đã có FK thật (`rag_chunk.document_hash → rag_document`,
`:55`), đã có composite natural PK. Hướng migration đúng là kéo `ops` về chuẩn của `ml`, không phải
gặp nhau ở giữa.

### F16 — [Correctness] FK nullable làm "zero orphans" thành assertion rỗng

`phase-02:131-133`: *"All three `run_id` columns stay nullable — Postgres does not enforce a foreign
key on NULL, so ad-hoc scripts degrade gracefully instead of failing. A DQ check monitors the rate of
NULL `run_id` rather than a hard constraint."*

Cơ chế đúng (Postgres MATCH SIMPLE: FK không check khi bất kỳ cột nào NULL). Nhưng hệ quả:
`build_schema_evidence.py` assert "zero orphans" sẽ **pass trivially** trên bảng toàn NULL `run_id`.
Đây đúng cùng lớp lỗi với D-16 ("cannot fail because of pipeline behavior") mà P2 đang diệt.

AC-P2-9 hiện tại: *"every declared FK resolves with zero orphans and every table reports
`row_count > 0`"*. Không có ceiling cho NULL rate.

**Đề xuất:** AC-P2-9 thêm mệnh đề: *"và NULL-rate của mỗi cột FK ≤ 5%"* (hoặc ngưỡng bạn chọn),
kèm AC negative: seed một `run_id` trỏ tới run không tồn tại → script **phải fail**. AC-P2-10 đã làm
đúng pattern này cho `dim_company`; cần bản tương đương cho FK metadata.

---

## Comparative Analysis

### Quyết định key: P2 vs consensus

| Chiều | P2 đề xuất | Consensus Kimball | Phán quyết |
|---|---|---|---|
| Fact join key | `ticker` (natural) | surrogate của dimension | **P2 sai** |
| Xoá `company_key` = hash(ticker) | có | đúng — không decouple, không compact | **P2 đúng** |
| Xoá `company_version_key` = hash(ticker\|valid_from) | có | **giữ** — đây là version surrogate | **P2 sai** |
| Durable key cho group xuyên version | không có | có, nếu cần group | **thiếu** |
| Natural key giữ trong dim làm attribute | có | có | **P2 đúng** |
| Tier-2 entity registry defer + document limitation | có | (ngoài phạm vi Kimball) | **P2 đúng, honest** |

### Naming: hiện trạng vs P2 vs chuẩn

| Đối tượng | Hiện tại | P2 | Chuẩn web | Khuyến nghị |
|---|---|---|---|---|
| SCD2 window | `valid_from_ts`/`valid_to_ts`/`is_current` | `known_from_ts`/`known_to_ts` | `_valid_from`/`_valid_to` (app time), `_sys_start`/`_sys_end` (sys time) | **giữ tên cũ** (rubric 40) + document semantic |
| Knowledge time trên fact | không có | `known_from` / `knowledge_ts` (2 tên) | không có chuẩn phổ quát | **`known_from_ts`**, một tên |
| Timestamp suffix | `_ts` / `_timestamp` / `_at` (3 kiểu) | không thống nhất | `_at` cho app, `_ts`/`_date` cho DW | **`_ts` + `_date`**; giữ `event_timestamp` cho Feast |
| Table plurality | plural raw / singular gold, không khai báo | không đề cập | chọn một, document, enforce | **khai báo split hiện tại** + lint |
| Gold prefix | `dim_`/`fact_`/`obt_`/`feat_` ✓, `distress_labels` ✗ | không đề cập | Kimball `dim_`/`fact_` | **`fact_distress_label`** |
| Version trong tên bảng | `distress_holdout_v1` | giữ | Iceberg tag/branch | **bỏ `_v1`**, dùng tag |

### Money type

| Option | Bytes/Parquet | Range VND | Scale sửa được? | Phán quyết |
|---|---|---|---|---|
| `DOUBLE` (hiện tại) | 8 | ~2^53 chính xác | n/a | **sai** — D-10 đúng |
| `DECIMAL(38,2)` (P2) | 16 | 10^36 | **không** | đúng nhưng over-provisioned |
| `DECIMAL(20,2)` | 8 | 10^18 | **không** | **khuyến nghị** |

---

## Implementation Recommendations

### Quick fix list — bàn giấy, sửa `phase-02-data-model.md` trước khi code

Thứ tự theo mức chặn.

1. **F1** — bỏ dòng "delete `company_version_key`". Giữ nó làm PK `dim_company` + FK trên mọi fact.
   Chỉ xoá `company_key`. Thêm `company_durable_key` nếu cần group xuyên version. Sửa `phase-02:41-42`,
   `:62-63`, `:142`, `:146`, AC-P2-3.
2. **F2** — bỏ rename `valid_from_ts`→`known_from_ts` trên `dim_company`. Sửa `phase-02:43`, `:181`.
   Giữ tên rubric; semantic vào ADR-017 + data dictionary.
3. **F3** — chốt một tên: `known_from_ts`. Sửa `phase-02:38`, `:39`, `:92`, `:143`, `:152`,
   `phase-05:61`. Thêm bảng suffix convention vào ADR-017. Migration `_at`→`_ts` trong `ops`.
4. **F7** — thêm PK/UNIQUE thật vào mọi fact/feat table trong `schema_evidence.sql` rewrite.
   Sửa `phase-02:97` (DQ assertion → partial unique index cho phần RDBMS).
5. **F5 + F6** — Bronze bỏ PK; `silver.companies` PK → `(ticker, created_ts)`.
   Thêm vào `phase-02:162` scope.
6. **F8** — thêm `fact_market_alert`, `fact_news_sentiment`, `fact_distress_label` vào ERD.
7. **F9** — rename `distress_labels` → `fact_distress_label`; bỏ `_v1` khỏi `distress_holdout`;
   `ml.label_table` → `ml.distress_label`.
8. **F4** — PK `ops.data_quality_result` = `check_id`, `track` là cột thường + CHECK enum.
   Sửa `phase-02:109`, `:187`, AC-P2-7.
9. **F11** — `DECIMAL(20,2)` money, `DECIMAL(18,6)` ratio. Ghi lý do scale vào ADR-017.
   Sửa `phase-02:47`, `:155`, AC-P2-11.
10. **F12 + F13** — thêm `src/transforms/gold/dim_date.py` vào `Related Code Files`; enrich `dim_date`;
    thêm AC dim_date-populated. Xem lại việc còn cần consistency check D-9 không.
11. **F14** — ADR-017 nói rõ `feat_*.event_timestamp = known_from_ts`; cập nhật CHECK của
    `feat_company_unified`.
12. **F16** — AC-P2-9 thêm NULL-rate ceiling + AC negative cho FK metadata.
13. **F10** — viết naming convention vào `docs/architecture/data-model.md` + lint trong
    `run_quality_gates.py`.

### DDL đề xuất (thay `sql/schema_evidence.sql` phần gold)

```sql
-- BRONZE: append-only, không PK, không UNIQUE
CREATE TABLE bronze.companies (
    ticker       VARCHAR NOT NULL,
    company_name VARCHAR,
    exchange     VARCHAR,
    created_ts   TIMESTAMPTZ NOT NULL,
    ingest_batch_id VARCHAR NOT NULL
    -- grain (document, không enforce): (ticker, created_ts, ingest_batch_id)
);

-- SILVER: giữ snapshot history để nuôi SCD2
CREATE TABLE silver.companies (
    ticker       VARCHAR NOT NULL,
    company_name VARCHAR NOT NULL,
    exchange     VARCHAR NOT NULL,
    industry     VARCHAR,
    sector       VARCHAR,
    delisted_flag BOOLEAN NOT NULL DEFAULT FALSE,
    created_ts   TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, created_ts)
);

-- GOLD: dimension với 3 lớp key
CREATE TABLE gold.dim_company (
    company_version_key VARCHAR PRIMARY KEY,           -- surrogate, fact join bằng cái này
    company_durable_key VARCHAR NOT NULL,              -- bất biến qua version, dùng để GROUP BY
    ticker              VARCHAR NOT NULL,              -- natural key, attribute
    company_name        VARCHAR NOT NULL,
    exchange            VARCHAR NOT NULL,
    industry            VARCHAR,
    sector              VARCHAR,
    listing_date        DATE,
    delisted_flag       BOOLEAN NOT NULL DEFAULT FALSE,
    valid_from_ts       TIMESTAMPTZ NOT NULL,          -- tên rubric mini 40, semantic = system time
    valid_to_ts         TIMESTAMPTZ,                   -- closed-open [from, to) theo SQL:2011
    is_current          BOOLEAN NOT NULL
);
CREATE UNIQUE INDEX uq_dim_company_current ON gold.dim_company (ticker) WHERE is_current;
CREATE INDEX ix_dim_company_durable ON gold.dim_company (company_durable_key);

CREATE TABLE gold.dim_date (
    date_key       INTEGER PRIMARY KEY,                -- YYYYMMDD, smart integer key
    calendar_date  DATE UNIQUE NOT NULL,
    fiscal_year    SMALLINT NOT NULL,
    fiscal_quarter SMALLINT NOT NULL,
    month          SMALLINT NOT NULL,
    quarter_end_date DATE NOT NULL,
    is_quarter_end BOOLEAN NOT NULL,
    day_of_week    SMALLINT NOT NULL,
    is_trading_day BOOLEAN NOT NULL
);

CREATE TABLE gold.fact_financial_statement (
    company_version_key VARCHAR NOT NULL REFERENCES gold.dim_company(company_version_key),
    date_key            INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
    ticker              VARCHAR NOT NULL,
    report_period       VARCHAR NOT NULL,              -- degenerate dimension, dùng cho partition
    statement_variant   VARCHAR NOT NULL,              -- {consolidated,separate}×{audited,unaudited}
    known_from_ts       TIMESTAMPTZ NOT NULL,          -- knowledge time
    is_latest_vintage   BOOLEAN NOT NULL,              -- derived
    total_assets        DECIMAL(20,2),
    total_liabilities   DECIMAL(20,2),
    total_equity        DECIMAL(20,2),
    created_ts          TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, report_period, statement_variant, known_from_ts)
);
CREATE UNIQUE INDEX uq_ffs_latest ON gold.fact_financial_statement (ticker, report_period)
  WHERE is_latest_vintage;

CREATE TABLE gold.fact_distress_label (                -- đổi từ distress_labels
    ticker        VARCHAR NOT NULL,
    report_period VARCHAR NOT NULL,
    label_version VARCHAR NOT NULL,
    distress_label SMALLINT NOT NULL,
    decision_ts   TIMESTAMPTZ NOT NULL,                -- ranh giới so với known_from_ts
    created_ts    TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, report_period, label_version)
);

CREATE TABLE gold.feat_company_unified (
    ticker            VARCHAR NOT NULL,
    event_timestamp   TIMESTAMPTZ NOT NULL,            -- Feast contract = known_from_ts
    created_timestamp TIMESTAMPTZ NOT NULL,            -- Feast tie-break
    known_from_ts     TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, event_timestamp),
    CHECK (event_timestamp = known_from_ts)
);
```

Partition (Iceberg, theo web): `PARTITIONED BY (month(known_from_ts))` cho statement (volume thấp),
`day(trading_date)` cho price. Web cảnh báo hai điều: *"a table's overall file size footprint should
be at least 1TB before utilizing partitions"* và over-partitioning là *"the most frequent mistake"*.
Ở 5-20 GB target (`AC-P4-8`), **month** là đúng, **day** cho statement là sai. Iceberg hỗ trợ
partition evolution nên mở lên `day` sau được không cần rewrite.

### Common Pitfalls

| Bẫy | Hậu quả | Tránh bằng |
|---|---|---|
| `ALTER TYPE ... TIMESTAMPTZ` không có `AT TIME ZONE 'UTC'` | dịch 7 giờ (D-13) | P2 đã xử lý đúng (`phase-02:135`) |
| Đổi scale DECIMAL sau khi có data | Iceberg **cấm**; corrupt historical read | chọn scale đúng ngay, precision mở sau |
| Feast `created_timestamp` tie-break | luôn chọn vintage mới nhất = leakage | `event_timestamp = known_from_ts` |
| DQ check thay constraint | pass sau khi đã ghi rác | PK/partial unique index + DQ cho Iceberg |
| FK nullable + assert zero-orphan | assertion rỗng | thêm NULL-rate ceiling + AC negative |
| Range join fact→dim | shuffle-heavy, có thể fan-out >1 row | join bằng `company_version_key` |
| Over-partition | file nhỏ, metadata phình | `month()` ở 5-20 GB, evolve lên `day()` sau |

---

## Resources & References

### Official Documentation
- Apache Iceberg Spec — https://iceberg.apache.org/spec/
- PyIceberg types (DOUBLE = IEEE 754 64-bit) — https://py.iceberg.apache.org/reference/pyiceberg/types/
- Snowflake — Iceberg data types — https://docs.snowflake.com/en/user-guide/tables-iceberg-data-types
- Athena — Iceberg supported types — https://docs.aws.amazon.com/athena/latest/ug/querying-iceberg-supported-data-types.html
- Azure Databricks — medallion lakehouse architecture — https://learn.microsoft.com/en-us/azure/databricks/lakehouse/medallion

### Key sources cited in findings
- Iceberg decimal type widening (scale immutable) — https://iceberglakehouse.com/iceberg/iceberg-decimal-type-widening/
- apache/iceberg#13742 — BigDecimal allocation bottleneck — https://github.com/apache/iceberg/issues/13742
- Iceberg partitioning best practices — https://lakeops.dev/blog/iceberg-partitioning-best-practices
- Starburst — Iceberg performance / partition sizing — https://www.starburst.io/blog/best-practices-for-optimizing-apache-iceberg-performance/
- Kimball surrogate key prefix convention — https://dwbi1.wordpress.com/2012/03/
- Surrogate key column naming — https://dwbi1.wordpress.com/2012/03/14/name-of-surrogate-key-columns/
- Red Gate — schema naming conventions (prefix usage) — https://www.red-gate.com/blog/database-schema-naming-conventions/
- Bytebase — singular vs plural table naming — https://www.bytebase.com/blog/sql-table-naming-dilemma-singular-vs-plural/
- DW naming convention (singular for DW) — https://www.linkedin.com/pulse/data-warehouse-naming-convention-kirill-andriychuk
- Timestamp/date column naming — https://medium.com/@neverdonerefactoring/naming-conventions-date-and-timestamp-columns-3a56bef8acae
- Medallion naming cheatsheet — https://dev.to/thesius_code_7a136ae718b7/medallion-architecture-guide-naming-conventions-cheatsheet-2688
- DOUBLE vs DECIMAL for money — https://www.guptaakashdeep.com/choosing-between-double-and-decimal-data-type/

### Further Reading
- Kimball Group — The Data Warehouse Toolkit, ch. Slowly Changing Dimensions (durable supernatural key)
- SQL:2011 temporal features — `APPLICATION_TIME` vs `SYSTEM_TIME`, closed-open interval `[start, end)`
- Feast docs — `get_historical_features`, `created_timestamp_column` tie-break semantics

---

## Appendix A — Naming convention đề xuất

Đưa nguyên khối này vào `docs/architecture/data-model.md` và ADR-017; enforce bằng lint trong
`scripts/run_quality_gates.py`.

```
ZONE / SCHEMA
  bronze / silver     tên feed, SỐ NHIỀU, mirror nguồn      companies, financial_statements
  gold                SỐ ÍT + prefix                        dim_, fact_, obt_, feat_, raw_
  ops                 Postgres metadata vận hành            pipeline_run_log, data_quality_result
  ml                  Postgres metadata ML                  distress_label, feast_registry_revision

TABLE
  dim_<entity>        dimension, số ít                      dim_company, dim_date
  fact_<event>        fact, số ít                           fact_financial_statement
  obt_<subject>       one-big-table                         obt_company_quarter_risk
  feat_<entity>_<win> feature table                         feat_company_market_30d
  KHÔNG version trong tên bảng — dùng Iceberg tag/branch

COLUMN
  <x>_key             surrogate key                         company_version_key, date_key
  <x>_durable_key     durable key (bất biến qua version)    company_durable_key
  ticker              natural key (attribute, không join)
  <x>_ts              TIMESTAMPTZ                           created_ts, known_from_ts, valid_from_ts
  <x>_date            DATE                                  trading_date, listing_date
  is_<x>              BOOLEAN                               is_current, is_latest_vintage
  event_timestamp     RESERVED — Feast contract, không đổi
  created_timestamp   RESERVED — Feast tie-break, không đổi
  KHÔNG dùng _at (migrate 8 cột ops sang _ts)
  KHÔNG dùng "table" trong tên bảng/cột

TYPE
  money               DECIMAL(20,2)     scale KHÔNG sửa được sau — ghi lý do
  ratio / rate        DECIMAL(18,6)
  timestamp           TIMESTAMPTZ       migrate bằng AT TIME ZONE 'UTC', không bare ALTER TYPE
  date surrogate      INTEGER YYYYMMDD

TEMPORAL
  valid time      = report_period (+ dim_fiscal_period)     "kỳ nào"
  knowledge time  = known_from_ts                           "biết được từ khi nào"
  interval        closed-open [from, to)  theo SQL:2011
  SCD2 dim        valid_from_ts / valid_to_ts / is_current   (tên do rubric mini 40 quy định)

CONSTRAINT
  bronze          KHÔNG PK, KHÔNG UNIQUE (append-only)
  silver          PK gồm trục snapshot/vintage
  gold fact       PK = grain đầy đủ; partial unique index cho is_latest_vintage
  FK              khai báo trên bảng có data thật; nullable FK phải kèm NULL-rate ceiling
```

## Appendix B — Kết luận per câu hỏi

| Câu hỏi của bạn | Kết luận |
|---|---|
| **Primary key chọn đúng chưa?** | **Chưa.** Xoá `company_version_key` khỏi fact trái consensus Kimball (F1). Xoá `company_key` thì đúng. Thiếu durable key. 7 bảng gold không có PK nào (F7). Bronze có PK nhưng không được có (F5). `silver.companies` PK phá SCD2 (F6). PK `(track, check_id)` có cột dẫn vô dụng (F4). |
| **Các bảng phù hợp chưa?** | **Gần đủ.** ERD graded thiếu 3/12 dataset gold (F8). `dim_date` chỉ 2 cột nên fiscal attributes bị denormalize lên fact (F12). `dim_date` không có trong scope P2 nhưng FK trỏ vào nó (F13). Thiếu `dim_fiscal_period` nếu muốn fix D-9 đúng cách. |
| **Đặt tên phù hợp chưa?** | **Chưa.** Rename `valid_from_ts` phá rubric mini 40 (F2). Ba tên cho một concept trong cùng file (F3). Repo có 3 convention suffix, P2 thêm cái thứ 4 (F3). `distress_labels` vi phạm rubric mini 43 (F9). `distress_holdout_v1` double-version (F9). `ml.label_table` redundant (F15). Plural/singular lệch và không khai báo (F10). |
| **Chuẩn production chưa?** | **Phần lớn có, ba chỗ chưa.** Đúng: bi-temporal, vintage-preserving dedup, DECIMAL, TIMESTAMPTZ + `AT TIME ZONE`, partial unique index, deterministic `check_id` + ON CONFLICT, partitioning, honest deferral của Tier-2. Chưa: DECIMAL(38,2) over-provisioned + scale không sửa được (F11), Feast tie-break chống lại thiết kế (F14), FK nullable làm assert rỗng (F16). |
| **Chuẩn convention trên web chưa?** | Naming: **không** (F2, F3, F9, F10). Key: **không** (F1). Type: **gần** (F11). Temporal: **có, nhưng dùng thuật ngữ nội bộ chưa document** (F2). Medallion: **có**, trừ PK trên Bronze (F5). |

---

## Unresolved Questions

1. **Scale của money.** Nguồn vnstock trả VND nguyên đồng, triệu đồng, hay tỷ đồng? Quyết định scale
   là **một chiều** trong Iceberg. Cần xem một payload thật trước khi chốt `DECIMAL(20,2)` vs
   `DECIMAL(20,0)`.
2. **`company_durable_key` sinh từ đâu?** Nếu vnstock không có delisting endpoint (đã verify
   2026-09-01, ADR-017), durable key chỉ có thể là `hash(ticker)` — tức quay lại `company_key`, chỉ
   đổi tên và đổi mục đích (group thay vì join). Có acceptable không, hay defer luôn cùng Tier-2?
3. **`statement_variant` có nằm trong grain của mọi fact, hay chỉ `fact_financial_statement`?**
   `phase-02:92` chỉ nói fact statement. `fact_market_price` không có variant. Cần khai báo rõ để PK
   không lệch giữa các fact.
4. **Rename `distress_labels` có phá evidence row nào không?** Cần grep
   `docs/phase2/rubric-matrix.csv` cho `distress_labels` trước khi đổi — cùng cơ chế mà
   `phase-02:242-243` đã dùng cho `company_key`.
5. **mini row 40 có chấp nhận tên khác nếu semantic đúng và có document?** Rubric ghi đúng ba tên
   cột. Nếu người chấm linh động thì F2 hết là blocker. Không xác định được từ CSV — cần hỏi giảng viên.
