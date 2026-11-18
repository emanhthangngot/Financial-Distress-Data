# Advise — Plan audit: 300 điểm rubric + kiến trúc target

Ngày: 2026-09-02. Đối tượng: `plans/260831-1644-rebuild-target-mlops-architecture`.
Loại: advisory. Không sửa code, không sửa file plan.

## Reframing đã xác nhận

**Vấn đề.** Plan tuyên bố hai mục tiêu binding: O-1 (83 component sống đúng
`images/architecture/fdd-architecture-full-4k.png`) và O-2 (161 dòng / 300 điểm rubric có evidence
chạy thật). Cần biết plan như đang viết có chạm 300 điểm mà vẫn thoả kiến trúc không, thiếu chỗ nào.

**Yêu cầu.**
1. Verify số học 300 điểm / 161 dòng.
2. Liệt kê dòng rubric không có acceptance criterion trong phase file nào.
3. Liệt kê component trong ảnh không có phase sở hữu.
4. Chỉ tên từng lỗi phải sửa, kèm số dòng.
5. Thứ tự thực thi ưu tiên điểm trong 48 weekdays.

**Mục tiêu.** Biết chính xác khoảng cách tới 300 điểm; checklist bàn được cho `ak:plan`; success
metrics đo bằng lệnh/số.

**Ngoài phạm vi.** Sửa code; sửa file plan; tự ý cắt O-1.

**Ràng buộc (user chốt).** 300 điểm binding, mini re-earn dạng re-capture · điểm > image fidelity
khi buộc chọn · GKE dùng được (quota + credit OK) · **P1 rename toàn bộ, giữ nguyên** · 48 weekdays
/ ~283h.

---

## Đã verify (bằng chứng, không suy đoán)

### V1. Số học rubric của plan ĐÚNG

Parse 3 CSV bằng `csv.reader`. Dòng đầu mỗi CSV (README + deployment diagram) không có điểm; dòng
cuối là dòng tổng `100`.

| Track | Dòng có điểm | Tổng điểm | Plan ghi |
|---|---|---|---|
| mini | 44 | 100 | 44 / 100 ✓ |
| ML | 57 | 100 | 57 / 100 ✓ |
| LLM | 60 | 100 | 60 / 100 ✓ |
| **Tổng** | **161** | **300** | 161 / 300 ✓ |

`plan.md:56-64` và `phase-03:44-59` khớp chính xác. C19/C20 trong `debate-audit` đúng là PROVEN.

### V2. Trục kiến trúc (O-1): coverage đầy đủ, không có component mồ côi

Map 62 lớp component đọc được từ ảnh vào 13 phase file. **Không lớp nào có 0 phase sở hữu.**

Đã kiểm: Terraform, Ansible, GKE, Lakekeeper, Iceberg, MinIO, Spark, Airflow, DataHub, Debezium,
Kafka, Flink, Feast, Redis, Kubeflow, Ray, MLflow, KServe, Triton, llm-d, LWS, Knative/Kourier,
Gateway API/HTTPRoute, Istio, Kiali, Vault, ESO, OTel, Loki, Prometheus, Grafana, Jaeger,
PushGateway, Jenkins, Argo CD, Argo Rollouts, AnalysisTemplate, NGINX, cert-manager, KEDA, Superset,
Trino, dbt, Next.js web, prediction-api, feature-api, drift-api, feature-mcp, drift-mcp, kagent,
agentgateway, Coordinator Agent, Sandbox, holdout tag, frozen eval set, Data Generator, GitHub SCM,
canaryTrafficPercent, mTLS STRICT, AuthorizationPolicy, vnstock source.

Danh sách 83 dòng ở `debate-proposal.md:798-880` khớp ảnh.

### V3. Trục rubric (O-2): 118 / 300 điểm không có acceptance criterion

Đếm trên 13 phase file: **139 AC**, **74 citation rubric**. Per-row:

| Track | Dòng được AC cite | Dòng thiếu | Điểm thiếu AC |
|---|---|---|---|
| ML | 53 / 57 | 15, 16, 17, 43 | 8 |
| LLM | 53 / 60 | 2, 3, 31, 32, 33, 47, 55 | 10 |
| **mini** | **0 / 44** | tất cả 44 | **100** |
| | | | **118 / 300** |

**Không một AC nào trong toàn bộ 13 phase file cite một dòng `mini` nào.** Bảng `owning_phase` ở
`phase-03:63-88` — cơ chế được thiết kế để đóng R-6 — cũng chỉ liệt kê dòng ML/LLM, **zero dòng
mini**. Effort baseline 103-149 ngày (`plan.md:258-259`) được tính từ chính các phase file đó.

Chi tiết dòng thiếu:

| Dòng | Nội dung | Điểm |
|---|---|---|
| ML 15 | Simulate data drift | 2 |
| ML 16 | Using generator configuration | 2 |
| ML 17 | Bảng label (id, label) | 2 |
| ML 43 | Terraform setup GKE | 2 |
| LLM 2 | Deploy LLM inference platform | 2 |
| LLM 3 | Setup a custom model | 2 |
| LLM 31 | Simulate data drift | 1 |
| LLM 32 | Using generator configuration | 1 |
| LLM 33 | Bảng label | 2 |
| LLM 47 | Terraform setup GKE | 1 |
| LLM 55 | A/B test agents với model config khác nhau | 1 |

`phase-04:116` có nhắc "Retain drift simulation, generator configuration and the label table" trong
implementation step nhưng **không có AC nào** — theo chính tiêu chuẩn của plan (mỗi dòng rubric phải
có AC dạng `WHO -> ACTION -> RESULT`), step không phải bằng chứng.

### V4. Ba lỗi cụ thể trong plan

**L1 — Cut ladder sai số điểm Flink.** `plan.md:285` ghi:

> `| 3 | Debezium + Flink CDC (P5 partial) | 5-7 | **0** | Rubric asks for stream→store *jobs*, not Flink |`

Sai. mini dòng 20-24 ghi nguyên văn *"Flink job to handle streaming data problems"*:

| mini row | Nội dung | Điểm |
|---|---|---|
| 20 | Baseline (without optimization) | 2 |
| 21 | Handle burst with explanation | 3 |
| 22 | Handle late arrival with explanation | 3 |
| 23 | Handle other streaming problem with explanation | 3 |
| 24 | Window processing | 2 |
| | | **13** |

Cut item 3 rủi ro **13 điểm**, không phải 0. R-9 (`plan.md:336`) có flag "recompute at P3 exit" nhưng
con số đang in ra sai và có thể dẫn tới quyết định cắt sai.

**L2 — P12 xếp sai thứ tự capture mini.** `phase-12:71` và `phase-12:162` ghi mini rows *"depends
only on P4 and P2"* → capture `--track mini` sau P4. Sai: 13 điểm Flink (mini 20-24) phụ thuộc **P5**;
12 điểm lineage + data contract per-DP (mini 33-38) phụ thuộc P4 **và** P5 (DP3 = offline feature
table). Chạy `--track mini` sau P4 sẽ fail ≥25 điểm.

**L3 — P3 owning_phase không phủ mini.** `phase-03:63-88` liệt kê 24 nhóm dòng, tất cả là ML/LLM.
Step 3 (`phase-03:134-135`) nói "assert programmatically that no row is unowned" — cơ chế phát hiện
tồn tại, nhưng bảng nguồn thì rỗng cho mini, nên gap sẽ chỉ lộ ra **lúc chạy assert ở P3**, và
Risk Assessment (`phase-03:186-188`) phản ứng bằng *"add the capability to the owning phase and
re-baseline that phase's effort"* — tức re-baseline giữa đường trên một lịch đã overcommit 1.8-2.6×.

### V5. Mini track đã implement — là re-capture, không phải build lại

Có sẵn trong repo:

- `docs/evidence/flink/` — `baseline-contract.json`, `baseline-runtime.json`, `comparison.json`,
  `optimized-contract.json`, `optimized-runtime.json`, `optimized-checkpoints.json`,
  `restart-before/after/after-cancel.json` → phủ mini 20-24
- `docs/evidence/generator/` — `effective-config.json`, `profile.json/html`,
  `runtime-validation.json`, `source-manifest.json` → phủ mini 4-13
- `docs/evidence/docker/phase8-image-sizes.json` → mini 2-3
- `docs/evidence/duckdb_index_benchmark.json` → mini 26
- `docs/evidence/airflow/`, `docs/evidence/datahub/` → mini 27-38
- `docs/submission/rubric-(mini-coursework)/` — đủ 10 file theo đúng section rubric
- docs: `spark-and-storage-optimization.md`, `flink-stream-processing.md`,
  `05_storage_optimization.md`, `08_docker_optimization.md`, `data-pipeline-orchestration.md`,
  `data-governance.md`, `01_data_generator.md`, `02_schema_design.md`, `07_data_contracts.md`,
  `09_novel_idea_1.md`, `10_novel_idea_2.md`

Nhưng P1 (rename 296 file) + P2 (data model v2) + P4 (Iceberg thay Parquet) **làm invalid** phần lớn
evidence này. mini 39-43 (schema design, SCD2, feat_ tables, ERD, naming convention = 10 điểm) bị P2
viết lại hoàn toàn; mini 14-19 Spark (16 điểm) chạy trên contract cũ; mini 25 compaction/z-order
(2 điểm) đổi từ Parquet sang Iceberg. Đây là re-capture **có sửa nội dung**, không phải re-run script.

### V6. Phân bố điểm theo phụ thuộc runtime (ước lượng của tôi, không phải số đo)

| Track | Cần cluster sống | Chạy được local |
|---|---|---|
| mini | 0 | 100 |
| ML | 59 | 41 |
| LLM | 68 | 32 |
| **Tổng** | **127** | **173** |

173/300 điểm không phụ thuộc GKE. Đây là phân loại thủ công của tôi từ nội dung từng dòng, không
phải số đã kiểm chứng bằng thực nghiệm — cần đối chiếu lại ở P3.

### V7. Số học lịch

48 weekdays từ 2026-09-02 đến 2026-11-06 (verify bằng `datetime`; plan ghi 48, đúng).
Critical path plan: 87-125 ngày → 522-750h ở 6h/ngày, vs ~283h khả dụng. Overcommit 1.8-2.6× —
plan tự thừa nhận ở `plan.md:257-269`.

---

## Verdict

**Plan chưa đạt 300 điểm, nhưng không phải vì thiếu năng lực thiết kế — mà vì mini track (100 điểm,
33% tổng điểm) không được nối vào bộ máy acceptance criteria.** Trục kiến trúc thì ổn: 62/62 lớp
component có phase sở hữu, danh sách 83 dòng khớp ảnh, O-1 khả thi về mặt cấu trúc. Trục rubric thì
118/300 điểm không có một AC nào, và 100 trong số đó là toàn bộ mini. Cơ chế phát hiện (P3 step 3
assert no row unowned) có tồn tại, nên gap sẽ bị bắt — nhưng bắt **muộn**, ở P3, trên một lịch đã
overcommit 1.8-2.6×, và phản ứng được kê là "re-baseline effort của phase đó". Đó là chuyển rủi ro
lịch thành rủi ro giữa đường. Cộng thêm ba lỗi cụ thể (cut ladder ghi Flink 0 điểm thay vì 13; P12
xếp mini sau P4 thay vì sau P5; bảng owning_phase rỗng cho mini), plan hiện tại **sẽ phát hiện ra là
mình không đủ 300 điểm vào khoảng ngày thứ 20**, chứ không phải bây giờ. Sửa được trong 1-2 ngày
việc bàn giấy, và đó là việc rẻ nhất trong toàn bộ kế hoạch.

---

## Nên làm

Thứ tự bắt buộc. Bước 1-3 là bàn giấy, tổng 1-2 ngày, phải xong **trước** khi P1 khởi động.

1. **Bổ 44 dòng mini vào bảng `owning_phase` của P3** (`phase-03:63-88`). Gán cụ thể:
   - mini 2-3 (Docker, multistage) → **P11** (P11 sở hữu `tests/`; hoặc P12 nếu coi là evidence)
   - mini 4-9 (generator offline: skew, cardinality, schema evolution, duplicate, config, store) → **P4**
   - mini 10-13 (generator streaming: burst, late, duplicate, config) → **P4**
   - mini 14-19 (Spark: baseline + 4× handle-with-explanation + integrated) → **P4**
   - mini 20-24 (Flink: baseline + burst + late + other + window) → **P5**
   - mini 25 (lakehouse compaction/z-order) → **P4**
   - mini 26 (DW indexing) → **P2**
   - mini 27-32 (DP1/DP2/DP3 × ingest+validate) → **P4** (DP3 → **P5**)
   - mini 33-38 (lineage + data contract × 3 DP) → **P4** (DP3 → **P5**)
   - mini 39-43 (schema design, SCD2, feat_ tables, ERD, naming convention) → **P2**
   - mini 44-45 (novel ideas × 5 điểm) → **P2** (PIT restatement) + **P4** (generator restatement)
2. **Viết AC cho 11 dòng ML/LLM thiếu.** ML 15/16/17 và LLM 31/32/33 → thêm AC vào P4 (drift
   simulation, generator config, label table — hiện chỉ là step ở `phase-04:116`). ML 43 / LLM 47 →
   thêm AC Terraform-GKE vào P6. LLM 2/3 → thêm AC vào P8. LLM 55 → thêm AC vào P8 hoặc P10.
3. **Sửa ba lỗi.** L1: `plan.md:285` đổi `0` → `13` và ghi rõ mini 20-24. L2: `phase-12:71,162`
   đổi `--track mini after P4` → `after P5`. L3: thêm assert ở `verify_rubric_coverage.py` rằng
   `track=mini` có ≥1 dòng cho mỗi owning_phase P2/P4/P5.
4. **Đảo thứ tự capture trong P12 theo giá trị điểm/ngày**, không theo track. Hiện `phase-12:67-72`
   xếp LLM → mini → ML. Với ràng buộc "điểm > ảnh", thứ tự đúng là: (a) 173 điểm local-runnable
   trước — chạy được ngay cả khi GKE chưa lên; (b) 127 điểm cluster sau. Cụ thể: mini 100 + ML 41
   + LLM 32 = 173 điểm không đợi P6.
5. **Đặt tripwire lịch theo điểm, không theo phase.** Plan có R-1 với "weekly slack check at the
   60% date". Thay bằng: mốc ngày 15 phải có ≥100 điểm captured, ngày 30 ≥200, ngày 40 ≥260.
   Miss mốc → kích cut ladder ngay, không chờ.
6. **Chạy P1 rename như bạn quyết** (4-6 ngày, toàn bộ), nhưng thêm một bước không có trong plan:
   trước khi rename, **snapshot `docs/evidence/` và `docs/submission/` sang tag git** để re-capture
   mini có bản đối chiếu. `phase-03:148` xoá `docs/phase1/` và `docs/platform/evidence-tree/` —
   xoá không có bản đối chiếu là bỏ mất tham chiếu duy nhất cho 100 điểm re-capture.
7. **Chỉ sau khi 1-6 xong mới mở P1.**

---

## Không nên làm

- **Không tin `plan.md:285` cut ladder trước khi recompute.** Nó nói Flink 0 điểm. Thật là 13. Nếu
  ngày 30 bạn cần cắt và tin bảng này, bạn mất 13 điểm mà tưởng mất 0. R-9 flag đúng nhưng con số
  in ra thì sai — sai số in ra nguy hiểm hơn không in.
- **Không xoá `docs/evidence/` + `docs/submission/` trước khi mini có AC.** Đó là 100 điểm re-capture
  duy nhất bạn có. Xoá ở P3 (`phase-03:124,148`) trong khi AC mini chưa viết = tự tay biến
  re-capture thành build-lại.
- **Không để P3 là chỗ đầu tiên phát hiện gap mini.** Assert của P3 sẽ bắt, nhưng lúc đó bạn đã tiêu
  P1 (4-6 ngày) + P2 (8-12 ngày) và phải re-baseline effort. Phát hiện bây giờ tốn 1-2 ngày bàn giấy.
- **Không chạy `--track mini` sau P4.** Sẽ fail ≥25 điểm (Flink 13 + DP3 lineage/contract 4 +
  DP3 ingest/validate 4 + phần feature table). Đợi P5.
- **Không chạy P5 và P6 song song như `plan.md:235` đề nghị nếu ưu tiên điểm.** P5 giữ 13 điểm Flink
  + 12 điểm lineage; P6 giữ Istio/Vault/Ansible = 5 điểm (`plan.md:292-293`). Nếu buộc chọn một
  luồng, P5 đáng gấp 5 lần. Song song chỉ hợp lý khi cả hai chắc chắn xong.
- **Không đầu tư Kiali, Triton, Trino, Superset, dbt trước ngày 40.** `plan.md:284-289` xác nhận
  0 điểm. Chúng phục vụ O-1, mà O-1 bạn đã chốt là nhường khi buộc chọn.

---

## Có thể rẻ hơn / hiệu quả hơn

Xếp theo tỉ lệ điểm-thu-được / ngày-bỏ-ra:

1. **Viết AC cho mini + 11 dòng ML/LLM** — 1-2 ngày bàn giấy, khoá 118 điểm vào bộ máy verify.
   Đây là hạng mục có ROI cao nhất trong toàn bộ kế hoạch. Không có nó, `verify_rubric_coverage.py`
   sẽ exit 0 trên một matrix thiếu 118 điểm AC.
2. **Front-load 173 điểm local-runnable** — chạy được song song với việc chờ GKE/quota, và không
   phụ thuộc G0. Hiện plan để chúng rải rác sau P6.
3. **Re-capture mini bằng docker-compose, không bằng GKE** — mini 0/100 điểm cần k8s.
   `docker compose config` đã là verify command trong `AGENTS.md`. Tiết kiệm cả vCPU và thời gian.
4. **Gộp P11 (quality engineering, 6-9 ngày) vào sớm** — 20 điểm (ML 10-14 + LLM 26-30) hoàn toàn
   local, không đợi P7/P8/P9 như `phase-11` frontmatter yêu cầu. Test coverage, EP/BVA, mutation,
   property-based, load test đều chạy được trên code hiện có. Hiện dependency
   `["P7","P8","P9"]` khoá 20 điểm rẻ sau 3 phase đắt nhất.
5. **Đối với mini 14-19 (Spark, 16 điểm) — chỉ cần "with explanation"**, không cần re-benchmark từ
   đầu. Rubric chấm phần giải thích (`docs/spark-and-storage-optimization.md` đã có 83 dòng). Sau
   Iceberg cutover, cập nhật con số + giữ nguyên lập luận.

---

## Đường đi cụ thể (từ hiện trạng tới 300 điểm)

**Ngày 0-2 — Bàn giấy, không chạm cluster.**
- Bổ 44 dòng mini + 11 dòng ML/LLM vào bảng `owning_phase` P3.
- Sửa `plan.md:285` (Flink 13 điểm), `phase-12:71,162` (mini sau P5).
- Tag git `evidence-baseline-pre-rebuild` trên `docs/evidence/` + `docs/submission/`.
- Đặt tripwire điểm: ngày 15 ≥100, ngày 30 ≥200, ngày 40 ≥260.

**Ngày 1 (song song) — G0 quota + credit.**
- Bạn nói quota đã xin và credit còn. Vẫn phải ghi số đo thật vào `reports/gate-decisions.md`
  (`AC-P0-2` cấm giá trị suy đoán). Đây là điều kiện mở P4/P6.

**Ngày 3-8 — P1 rename toàn bộ** (quyết định của bạn, chạy một mình).
- Exit gate: `pytest tests` zero skip + `scripts/run_stage1_quality_gates.py` pass.

**Ngày 9-20 — P2 + P3 (nối tiếp, source-only, 0 vCPU).**
- P2 khoá mini 26, 39-43 (12 điểm) + novel idea 1.
- P3 xuất `docs/rubric-matrix-unified.csv` 161 dòng có `owning_phase` đủ 3 track.
- **Mốc ngày 15: capture đợt 1** — mini 39-43 + ML 55-56 + LLM 58-59 + novel ideas ≈ 30 điểm.

**Ngày 21-34 — P4 + P11 song song** (P11 không thực sự cần P7/P8/P9).
- P4 khoá mini 4-19, 25, 27-32 (DP1/DP2), 33-36 ≈ 60 điểm + ML 15-17 / LLM 31-33.
- P11 khoá ML 10-14 + LLM 26-30 + ML 55 / LLM 58 = 24 điểm, toàn bộ local.
- **Mốc ngày 30: ≥200 điểm.** Nếu chưa: kích cut ladder đã recompute.

**Ngày 35-42 — P5 rồi P6.**
- P5 khoá mini 20-24 (13 điểm) + DP3 (mini 31-32, 37-38) + ML 18-21 / LLM 38-39.
- P6 mở đường cho 127 điểm cluster: Istio, Vault, Terraform, Ansible.
- **Mốc ngày 40: ≥260 điểm.**

**Ngày 43-48 — P7/P8/P9/P10/P12 nén.**
- Đây là chỗ 1.8-2.6× overcommit đập vào. Với ràng buộc "điểm > ảnh", cắt theo cut ladder **đã sửa**:
  Kiali → Triton → Trino/Superset/dbt → Jenkins (giữ GitHub Actions) → Ray (dùng Spark distributed).
  Tổng 0 điểm mất, ~20-27 ngày tiết kiệm. **Không cắt Debezium/Flink** (13 điểm) như plan hiện gợi ý.
- P12 chạy `run_unified_evidence_capture.py --only-failed` liên tục, không chờ một cửa sổ cuối.

---

## Lợi ích

- 118 điểm hiện không có AC được khoá vào bộ máy verify trước khi tiêu ngày nào — thay vì lộ ra ở P3
  sau 12-18 ngày đã tiêu.
- `verify_rubric_coverage.py` exit 0 trở thành bằng chứng thật cho O-2, không phải bằng chứng trên
  một matrix thiếu 1/3 điểm.
- 173 điểm local-runnable chạy được song song với chờ quota/GKE → tách rủi ro G0 khỏi rủi ro điểm.
- Cut ladder có số đúng → khi buộc cắt ở ngày 40, cắt đúng chỗ 0 điểm, không mất 13 điểm Flink.
- Tag evidence baseline biến mini từ "build lại 100 điểm" thành "re-capture có đối chiếu".
- Tripwire theo điểm cho tín hiệu sớm hơn tripwire theo phase: bạn biết mình đang thiếu điểm ở ngày
  15, không phải ở ngày 40.

---

## Trade-offs (kèm cái tôi phản đối mà bạn đã quyết)

- **P1 rename toàn bộ tốn 4-6 ngày cho ≤4 điểm** (ML 55 / LLM 58 "clean repo", một phần). Bạn đã
  quyết giữ; tôi ghi lại đây là chi phí đã biết, không đề nghị lại. Hệ quả kèm theo: nó làm invalid
  evidence mini và tạo thêm việc re-capture, nên bước tag git ở ngày 0-2 trở thành bắt buộc, không
  còn là tuỳ chọn.
- **O-1 nhường khi buộc chọn** → tấm ảnh sẽ mô tả một hệ thống không sống 100%. `phase-12:110-111`
  đã yêu cầu "honest gap table" — đó là cách xử lý đúng, nhưng nghĩa là bạn nộp một diagram kèm bảng
  ghi rõ cái gì chưa dựng. Nếu có buổi demo live, đây là chi phí thật.
- **Chạy P11 sớm hơn dependency của nó** đánh đổi: test viết trên code chưa qua P7/P8/P9 sẽ phải sửa
  lại khi API thay đổi. Chi phí: ~2-3 ngày sửa test. Lợi: 24 điểm về sớm 20 ngày.
- **Đảo thứ tự capture LLM-first → local-first** rủi ro R-5 (`plan.md:332`): 100 điểm LLM đã từng
  executed, capture muộn hơn thì nguy cơ mất cao hơn. Giảm nhẹ bằng: LLM 32 điểm local nằm trong đợt
  local-first; 68 điểm LLM cluster capture ngay khi P6+P8 mở, trước ML.
- **Điều kiện khuyến nghị này hết đúng:** nếu deadline dời ra sau 2026-11-06 hoặc capacity vượt
  40h/tuần, số học overcommit đổi và "điểm > ảnh" không còn cần thiết — lúc đó quay lại plan gốc với
  cả hai mục tiêu binding. Chi phí đổi hướng lúc đó: thấp, vì mọi thứ tôi đề nghị (AC cho mini, sửa
  3 lỗi, tag evidence, tripwire điểm) đều là việc plan gốc cũng cần.

---

## Work checklist

- [ ] Bổ 44 dòng mini vào bảng `owning_phase` trong `phase-03-contracts-rubric.md:63-88`, gán P2/P4/P5/P11 theo mapping ở §Nên làm bước 1
- [ ] Viết AC cho ML 15, 16, 17 và LLM 31, 32, 33 vào `phase-04-data-plane.md` §Success Criteria
- [ ] Viết AC cho ML 43 / LLM 47 (Terraform GKE) vào `phase-06-platform.md`
- [ ] Viết AC cho LLM 2, 3 (deploy LLM inference platform, custom model) vào `phase-08-llm-agent-track.md`
- [ ] Viết AC cho LLM 55 (A/B test agents khác model config) vào `phase-08` hoặc `phase-10`
- [ ] Sửa `plan.md:285`: cut item 3 Debezium+Flink từ `0` điểm thành `13` điểm, ghi rõ mini 20-24
- [ ] Sửa `phase-12-observability-evidence.md:71` và `:162`: `--track mini` chuyển từ "after P4" thành "after P5"
- [ ] Thêm assert vào spec `verify_rubric_coverage.py` (`phase-03:141-144`): `track=mini` phải có ≥1 dòng cho mỗi owning_phase trong {P2, P4, P5}
- [ ] Tag git `evidence-baseline-pre-rebuild` trên `docs/evidence/` + `docs/submission/` trước khi P3 xoá tree
- [ ] Sửa `phase-03:124,148`: chỉ xoá evidence tree **sau** khi tag tồn tại và 44 AC mini đã viết
- [ ] Đổi `phase-11-quality-engineering.md` frontmatter `dependencies` từ `[P7,P8,P9]` thành `[P1]` cho 24 điểm local (ML 10-14, LLM 26-30, ML 55, LLM 58); giữ dependency P9 chỉ cho load test API
- [ ] Thêm §Score Tripwires vào `plan.md`: ngày 15 ≥100 điểm, ngày 30 ≥200, ngày 40 ≥260; miss → kích cut ladder
- [ ] Ghi số đo quota + credit thật (USD + VND) vào `reports/gate-decisions.md` theo AC-P0-2, không dùng giá trị suy đoán
- [ ] Recompute cut ladder trên matrix 161 dòng, xác nhận Debezium/Flink không nằm trong 7 item đầu
- [ ] Chạy `.venv/bin/python scripts/run_stage1_quality_gates.py` xác nhận baseline pass trước khi mở P1

## Success metrics

| Metric | Cách đo | Target |
|---|---|---|
| Dòng rubric có owning_phase | `verify_rubric_coverage.py` | 161 / 161, exit 0 |
| Dòng rubric có AC trong phase file | grep citation `(mini N)` / `(ML N)` / `(LLM N)` trên `phase-*.md` | 161 / 161 (hiện: 106) |
| Điểm không có AC | tổng điểm các dòng thiếu citation | 0 (hiện: 118) |
| Điểm mini có AC | grep `(mini ` trên `phase-*.md` | ≥1 citation cho mỗi 44 dòng (hiện: 0) |
| Tổng điểm matrix | `awk` cột points trên `docs/rubric-matrix-unified.csv` | 300.0 |
| Dòng `design_only` | `verify_rubric_coverage.py` | 0 |
| Component ảnh có phase sở hữu | `verify_target_architecture.py` | 83 / 83 mapped |
| Cut ladder item 3 điểm rủi ro | đọc `plan.md:285` | ghi `13`, không phải `0` |
| P12 mini ordering | đọc `phase-12:71,162` | ghi "after P5" |
| Evidence baseline tag | `git tag -l evidence-baseline-pre-rebuild` | tồn tại trước khi `docs/evidence/` bị xoá |
| Điểm captured ngày 15 / 30 / 40 | `run_unified_evidence_capture.py` summary | ≥100 / ≥200 / ≥260 |
| Điểm captured lúc freeze | `run_unified_evidence_capture.py` | 300 / 300, zero failed |
| Load balancer ngoài | `kubectl get svc -A --field-selector spec.type=LoadBalancer` | đúng 1 dòng (NGINX) |
| Fast loop | `.venv/bin/python -m pytest tests -m "not slow"` | pass, zero skip |
| Definition of done | `.venv/bin/python scripts/run_stage1_quality_gates.py` | exit 0 |
