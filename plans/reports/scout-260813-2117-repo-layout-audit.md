# Repo layout audit — chỗ sắp xếp khó hiểu / bất hợp lý

Ngày: 2026-08-13 · Read-only, chưa sửa gì · Nguồn: quét toàn repo + `docs/project-file-map.md`

## Tóm tắt

8 vấn đề. **3 cái sửa được ngay** (không đụng protected path), **3 cái bị khoá** bởi
gate `PHASE1_PROTECTED` nên chỉ document được, **2 cái là lỗi trong plan mới**.

Ràng buộc chi phối: `scripts/audit_phase2_evidence.py:58-71` + `:411`. `dags/` được
bảo vệ **trừ** `dags/phase2/`. Nghĩa là mọi thứ lộn xộn nằm trong `dags/`, `src/collectors|transforms|quality|catalog|metadata|streaming|generator`, `sql/` **không được dọn** cho tới khi nộp xong.

---

## A. `infra/` trộn hai trục phân loại — SỬA ĐƯỢC

Đúng như ông chỉ ra.

```
infra/airflow/Dockerfile          <- trục: component
infra/flink/Dockerfile            <- trục: component
infra/kafka/kafka_init_topics.sh  <- trục: component
infra/phase2/rag-pipeline/            <- trục: PHASE
infra/phase2/stream-feature-offline/  <- trục: PHASE
infra/phase2/stream-feature-online/   <- trục: PHASE
```

Không ai đoán được cần vào đâu tìm Dockerfile. Tệ hơn: nếu Phase 3 tới, sẽ có
`infra/phase3/` và trục phase nhân lên, còn `airflow/` vẫn nằm ngoài.

`infra/` **không** protected → sửa được ngay.

Đề xuất: một trục duy nhất — deployable/service.

```
infra/
  airflow/Dockerfile
  airflow/Dockerfile.baseline
  flink/Dockerfile
  kafka/kafka_init_topics.sh
  rag-pipeline/Dockerfile
  stream-feature-offline/Dockerfile
  stream-feature-online/Dockerfile
```

Phase thuộc về `docs/phase2/rubric-matrix.csv` và `configs/phase2-deployables.yaml`
(plan phase 3 sẽ tạo) — đó là nơi ghi cái gì thuộc phase nào, **metadata chứ không phải cây thư mục**.

Việc phải làm kèm: sửa `dockerfile:` path trong 3 workflow caller
(`phase2-rag-pipeline.yaml`, `phase2-stream-feature-offline.yaml`,
`phase2-stream-feature-online.yaml`) và dòng 562-564 `docs/project-file-map.md`.

## B. `configs/` trộn snake_case và kebab-case — SỬA ĐƯỢC

```
collector_config.yaml    drift-config.yaml
spark_config.yaml        spark-benchmark.yaml
source_mapping.yaml      schema-contracts.yaml
ingestion_manifest.yaml  rag-sources.yaml
generator-config.yaml    flink-streaming.yaml
dq_rules.yaml            phase2-governance.yaml
```

7 snake / 10 kebab. Không có ranh giới nào giải thích được — `spark_config.yaml`
và `spark-benchmark.yaml` nằm cạnh nhau, cùng chủ đề, khác quy ước.

Quy tắc global của ông là kebab-case cho file mới. `configs/` không protected,
nhưng đổi tên phải sửa mọi chỗ đọc chúng → rủi ro thật. Đề xuất: **kebab-case
cho file mới, không đổi tên file cũ**, và ghi luật đó vào `AGENTS.md`. Đổi hàng
loạt lúc này là churn không đáng trước hạn nộp.

## C. `src/generators/` là thư mục mồ côi — SỬA ĐƯỢC

```
src/generator/    <- thật, 6 module (protected)
src/generators/   <- CHỈ có __pycache__, không .py nào
```

Bytecode chết còn sót: `config_loader.pyc`, `streaming_problem_factory.pyc`,
`__init__.pyc`. Đây là tàn dư của commit `fix(generators): resolve generator
package collision` — chính là `PHASE1_BASE_SHA`. Untracked, không file nào import.

Vô hại về mặt chạy (Python không import từ `__pycache__` khi thiếu source), nhưng
hai thư mục tên gần giống nhau là bẫy đọc code. `rm -rf src/generators/` là xong —
untracked nên git không thấy gì, gate không đổi.

## D. `dags/` có bốn quy ước đặt tên cùng lúc — KHOÁ

```
01_collect_company_master_data.py     <- số thứ tự
dag_04_stream_market_events_to_kafka.py <- prefix dag_ + số
dp1_bronze_ingest.py                  <- mã pipeline
build_offline_features.py             <- động từ
ingest_source_to_bronze.py            <- động từ
stage1_local_evidence_pipeline.py     <- prefix stage
```

Và số nhảy cóc: có `01,02,03,05,06,07,08,09` — thiếu `04` vì nó là
`dag_04_stream_market_events_to_kafka.py`.

`dags/` protected → **không sửa được** trước khi nộp. Document trong
`project-file-map.md` là cách xử lý duy nhất bây giờ.

## E. Hai module DAG util song song, cùng tên — KHOÁ, mức độ cao nhất trong nhóm khoá

```
dags/utils/stage1_dag_utils.py   (39 dòng) <- 13 DAG cũ + 2 test dùng
dags/_stage1_dag_utils.py        (29 dòng) <- 8 DAG mới dùng, gồm CẢ 5 wrapper phase2
```

Nội dung khác nhau, tên gần trùng, chia theo **thời điểm viết** chứ không theo
chức năng. Một người mới đọc `dags/phase2/phase2_rag_ingest.py` sẽ import nhầm
module với xác suất cao.

`dags/` protected → không hợp nhất được. Nhưng `dags/phase2/` **được** sửa, nên
sau khi nộp có thể cho các wrapper phase2 dùng một module riêng dưới
`dags/phase2/` và bỏ hẳn `dags/_stage1_dag_utils.py` khỏi đường Phase 2.

## F. `images/` ở root chỉ chứa 4 asset tài liệu — SỬA ĐƯỢC (thấp)

```
images/architecture/architecture-stage-1.png
images/architecture/system_deployment_diagram.dot
images/architecture/system_deployment_diagram.png
images/schema/schema_evidence_erd.png
```

Trong khi `docs/architecture/` đã tồn tại và `docs/evidence/screenshots/` giữ ảnh
bằng chứng. Ba nơi chứa ảnh. `images/` xứng đáng là `docs/images/`.

Lưu ý: các file này được rubric R01 tham chiếu qua evidence manifest — di chuyển
phải cập nhật manifest, mà `docs/evidence/` **protected**. → Hoãn tới sau khi nộp.

## G. Phân tầng phase không thể hiện trong `src/` — KHÔNG SỬA, chỉ cần biết

19 package con trong `src/`. Chỉ 7 cái protected (`collectors`, `transforms`,
`quality`, `catalog`, `metadata`, `streaming`, `generator`). 12 cái còn lại —
`agents`, `drift`, `evidence`, `governance`, `io`, `jobs`, `lakehouse`, `llm`,
`ml`, `observability`, `orchestration`, `security` — nhìn cây thư mục **không
biết cái nào Phase 1 cái nào Phase 2**.

Nguồn sự thật duy nhất là hằng số `PHASE1_PROTECTED` trong một file Python.
Đó là nơi rất dễ bị bỏ sót khi đọc.

Không đề xuất di chuyển (di chuyển = phá gate). Đề xuất: `AGENTS.md` thêm bảng
phase-ownership cho cả 19 package, dẫn thẳng tới `audit_phase2_evidence.py:58`.

---

> **Cập nhật 2026-08-13 21:47.** Đã rà đủ 12 package (mục H0 bên dưới) và đo toàn
> bộ phạm vi đặt tên theo phase. Kết quả đầy đủ + thiết kế hợp nhất nằm trong
> `plans/260813-1846-production-hardening-overlay/phase-01-start.md`. Chưa thực
> thi thay đổi nào — người dùng yêu cầu review plan trước.

## H0. Lỗ hổng trong danh sách protected — NGHIÊM TRỌNG NHẤT BÁO CÁO NÀY

`src/lakehouse/compaction.py` là **code Phase 1**, không phải Phase 2. Bằng chứng:

- docstring tự khai: *"the spine for W19 (lakehouse compaction + DW indexing)"*
- được `dags/06_pyspark_silver_to_gold.py` và `dags/dp1_bronze_ingest.py` gọi — cả hai đều là DAG Phase 1 protected
- `scripts/demo_lakehouse_compaction.py` sinh ra `docs/evidence/lakehouse_compaction_benchmark.json`, tức bằng chứng rubric R25/R26 đã chấm
- có test riêng `tests/test_compaction.py`, `tests/test_dag_06_compaction.py`

Nhưng `src/lakehouse/` **không** nằm trong `PHASE1_PROTECTED`.

Hệ quả: một thay đổi Phase 2 vào `src/lakehouse/` có thể phá hành vi Phase 1 và
làm sai lệch bằng chứng R25/R26 đã ghi — **mà gate không bắt được**. Cây thư mục
và danh sách bảo vệ đang lệch nhau ở đúng chỗ nguy hiểm nhất.

### Rà đủ 12 package — phương pháp: truy vết importer

Package nào được DAG Phase 1 protected hoặc module `src/` đã protected import thì
package đó chứa hành vi Phase 1, bất kể tên gọi.

| Package | Chủ | Bằng chứng |
|---|---|---|
| `src/security/` | **Phase 1** | `src/transforms/spark_session.py` — **file đã protected** — import `src.security.secrets`. Thêm `src/jobs/stage1_*`, `scripts/run_stage1_real_e2e.py` |
| `src/evidence/` | **Phase 1** | `audit_mini_coursework_rubric.py` + `run_mini_coursework_submission.py` dựng `docs/evidence-index.md` — chính là bản 100/100 đã chấm |
| `src/lakehouse/` | **Phase 1** | W19 compaction; `dags/06`, `dags/dp1_bronze_ingest`; sinh R25/R26 |
| `src/jobs/` | **Phase 1** | `stage1_evidence_job`, `stage1_spark_lakehouse_job`, `kafka_to_bronze_job`; 3 DAG P1 |
| `src/orchestration/` | **Phase 1** | `airflow_tasks.py`; 3 DAG P1 |
| `src/io/` | **Dùng chung** | P1: `dags/dp1_bronze_ingest`, `dags/stage1_real_e2e_pipeline`, `src/generator/storage.py`, `src/jobs/*`. P2: 3 module Feast |
| `src/governance/` | **Dùng chung** | P1: `datahub_emitter/graphql/model` chạy `sync_datahub_governance.py` (lineage R33-R38). P2: `phase2_lineage.py` |
| `src/agents/` `src/drift/` `src/llm/` `src/ml/` `src/observability/` | Phase 2 | chỉ P2 import |

**Sáu** package phải bảo vệ, không phải bốn như ước đoán ban đầu — thêm
`src/security/` và `src/evidence/`.

`src/security/` là ca sắc nhất: **code đã protected phụ thuộc code chưa
protected**, nên gate có thể xanh trong khi hành vi Phase 1 đổi bên dưới.

Hai package dùng chung **không** bảo vệ cả gói (sẽ chặn việc Phase 2 hợp lệ) mà
bảo vệ ở mức file qua `PHASE1_PROTECTED_EXCEPTIONS` — đúng cơ chế đang dùng cho
`src/streaming/flink/jobs/` và `sql/init_ml_metadata.sql`:

- `src/io/` protected, trừ helper phục vụ Feast
- `src/governance/` protected, trừ `phase2_lineage.py`

Thêm vào `PHASE1_PROTECTED` là **siết**, không phải nới — không thể mất điểm LLM.
Nhưng phải chạy lại gate ngay sau khi thêm: nếu đỏ, nghĩa là đã có mutation Phase 1
lọt lưới từ trước, và đó là một phát hiện chứ không phải chướng ngại cần né.

## Hai lỗi trong plan mới `260813-1846-production-hardening-overlay`

**H1. Phase 7 ghi "Create `src/lakehouse/`" — sai hai lần.** Thứ nhất nó đã tồn
tại. Thứ hai, theo H0 nó là code Phase 1 — nên phase 7 **không được** thêm
`catalog.py`/`snapshots.py` vào đó. Iceberg Phase 2 phải nằm ở package riêng
(`src/iceberg/`), giữ đúng nguyên tắc additive của cả plan.

**H2. Phase 3 và phase 8 giả định `infra/phase2/...` path** khi khai
`configs/phase2-deployables.yaml` và Dockerfile CDC. Nếu làm mục A thì hai phase
này phải dùng path mới. → Đưa việc dọn `infra/` vào **phase 1** (đã là phase
hygiene, không cần quota), rồi phase 3/8 kế thừa.

---

## Không phải vấn đề — kiểm rồi, kết luận là ổn

Ghi ra để khỏi bị "sửa" nhầm:

- **`feature_repo/` ở root** — không phải trùng lặp với `src/ml/feast/`. Nó là
  re-export mỏng bắt buộc theo convention của Feast CLI, và
  `feature_repo/structured/definitions.py` có comment 8 dòng giải thích chính xác
  vì sao (lazy Feast import, chỉ `.venv-phase2` load). Thiết kế có lý do, đã ghi lại.
- **`packages/` (TypeScript) + `supabase/`** — product plane, pnpm workspace hợp lệ
  cạnh Python `src/`. Monorepo đa ngôn ngữ là chủ ý.
- **`node_modules/`, `mutants/`, `outputs/`, `*.egg-info/`, `.next/`** — untracked,
  `.gitignore` đã phủ đúng. Chỉ là rác local.
- **`sql/` vs `supabase/migrations/`** — hai database khác nhau (Phase 1
  `ops` vs product plane Supabase). Tách đúng.
- **`docs/project-file-map.md`** (634 dòng) — vẫn cập nhật, có cả `src/lakehouse`
  và `infra/phase2`. Tài liệu không lệch; **cây thư mục mới là chỗ lệch**.

---

## Đề xuất thứ tự

| # | Việc | Chặn bởi | Khi nào |
|---|---|---|---|
| 0 | Thêm `src/lakehouse|io|jobs|orchestration` vào `PHASE1_PROTECTED` (H0) | không | **trước mọi thứ khác** |
| 1 | `rm -rf src/generators/` (C) | không | ngay |
| 2 | Làm phẳng `infra/` theo trục service (A) + sửa 3 workflow + file-map | không | ngay, đưa vào phase 1 của plan |
| 3 | Sửa plan phase 7 (H1) và phase 3/8 path (H2) | mục 2 | ngay |
| 4 | Ghi luật kebab-case cho config mới vào `AGENTS.md` (B) | không | ngay |
| 5 | Bảng phase-ownership 19 package trong `AGENTS.md` (G) | không | ngay |
| 6 | Hợp nhất DAG util cho nhánh phase2 (E) | nộp xong | sau |
| 7 | `images/` → `docs/images/` (F) | nộp xong (`docs/evidence/` protected) | sau |
| 8 | Chuẩn hoá tên DAG (D) | nộp xong | sau |

---

## Phạm vi đặt tên theo phase — đo được

315 file tracked chứa `phaseN` trong path. Đối chiếu với `rubric-matrix.csv`:

| Cột | Trỏ tới | Số dòng |
|---|---|---:|
| `evidence_path` | `docs/phase2/...` | **117/117** |
| `test` | `tests/phase2/...` | **117/117** |
| `validation_command` | `tests/phase2/...` | **117/117** |
| `artifact_path` | `.github/workflows/phase2-*.yaml` | 13 |
| `artifact_path` | `tests/phase2`, `dags/phase2`, `docs/phase2` | 14 |
| — | `infra/phase2` | **0** |

Cộng hai hành vi hard-code trong gate: carve-out `dags/phase2/` ở
`audit_phase2_evidence.py:411`, và luật evidence path không được rời
`docs/phase2/evidence/`.

Ba tầng + luận điểm "không gộp được `docs/phase2/evidence/`" nằm đầy đủ trong
`plans/260813-1846-production-hardening-overlay/phase-01-start.md`.

## Quyết định đã chốt (2026-08-13)

1. **Đổi tên 8 workflow `phase2-*.yaml` — CÓ**, sang tên theo chức năng, kèm cập
   nhật 13 dòng `artifact_path`. `ci.yml` **không** đổi cho tới khi kiểm
   branch-protection: đổi tên workflow là đổi tên status check, và nếu nó đang là
   required check thì yêu cầu đó âm thầm hết hiệu lực.
2. **`dags/phase2/`, `tests/phase2/`, `docs/phase2/` — KHÔNG**, dời sang Tier 3
   sau khi nộp.
3. **Requirements — GỘP, không đổi tên.** Đã đo trước khi chốt: 10 package trùng
   đều **cùng lower bound**, Phase 2 chỉ thêm upper bound → không xung đột. Kết
   quả: một `requirements.txt`, 26 package, pin dạng có chặn trên. Chỉ 3 chỗ
   tham chiếu (`ci.yml:24`, `phase2-ci.yaml:65,88`).

## Câu hỏi còn mở

1. Làm phẳng `infra/` đụng 3 workflow đang xanh. Một PR gộp hay tách từng
   deployable?
2. Có workflow nào trong 8 cái đang là **required status check** không? Cần xem
   repo settings trước khi đổi tên.
3. Gộp requirements xong thì bỏ `.venv-phase2` luôn, hay giữ tới khi phase 10 thêm
   thư viện ML?
