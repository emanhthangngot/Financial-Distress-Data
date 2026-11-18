---
title: "Financial Distress Data — Onboarding Presentation Script"
date: 2026-08-10
status: study-guide
audience: "Project onboarding / production architecture meeting"
---

# Financial Distress Data — Onboarding Presentation Script

## Cách học nhanh

Học theo thứ tự:

1. Đọc phần **Thông điệp cốt lõi** để hiểu project trong 30 giây.
2. Đọc **Speaker script** thành tiếng một lần.
3. Học thuộc 5 công thức trong phần **Formula cheat sheet**.
4. Ôn phần **Q&A** để trả lời khi bị hỏi sâu.

File slide Beamer:

- Source: [onboarding-presentation-beamer.tex](./onboarding-presentation-beamer.tex)
- PDF: [onboarding-presentation-beamer.pdf](./onboarding-presentation-beamer.pdf)
- Compile: `xelatex -interaction=nonstopmode -halt-on-error onboarding-presentation-beamer.tex`

Không cần học thuộc mọi tên file. Chỉ cần nhớ luồng:

```text
Source -> Bronze -> Silver -> Gold -> DQ/Metadata -> Analyst/ML/RAG
```

## Thông điệp cốt lõi

> Đây là một data platform cho early-warning financial distress của doanh
> nghiệp niêm yết Việt Nam. Hệ thống thu thập dữ liệu, chuẩn hóa qua Bronze /
> Silver / Gold, kiểm tra chất lượng, lưu lineage và tạo ra risk features có thể
> truy xuất, giải thích và phục vụ analyst, ML hoặc RAG.

Một câu ngắn hơn:

> Project không chỉ tính financial ratios; project xây dựng một data foundation
> đáng tin cậy để biết dữ liệu đến từ đâu, được xử lý thế nào và có thể dùng an
> toàn trong production hay không.

## Điều phải nói chính xác

the platform hiện đã có local-first runtime evidence end-to-end. Nó dùng Airflow,
Kafka, MinIO, PostgreSQL, PySpark, DuckDB và PyTest.

Adapter hiện tại là fixture-backed để test ổn định. `SourceAdapter` đã được thiết
kế để thay bằng live API hoặc stakeholder connector, nhưng
`src/collectors/source_adapters/vnstock_adapter.py` hiện vẫn re-export
`VnstockFixtureAdapter`.

Vì vậy hãy nói:

> Foundation và contract đã được verify; live source integration và stakeholder
> workflow là bước production hardening tiếp theo.

Không nói:

> Hệ thống hiện đang chạy live production data từ vnstock.

the platform cũng chưa train ML model. `distress_label` hiện là rule-based proxy,
không phải validated credit-risk model.

## Speaker script — deck stakeholder-centric hiện tại

Đây là phần speaker script chính, khớp với deck 16 trang hiện tại. Cách trình bày
được tổ chức theo chuỗi:

\`\`\`text
Stakeholder -> decision objective -> evidence -> cost of error
            -> output -> threshold/metric -> workflow -> business impact
\`\`\`

### Title — Financial Distress Data

“Project này xây dựng nền tảng dữ liệu và risk intelligence cho bài toán
financial distress. Mục tiêu không dừng ở việc tạo ra một score; kết quả phải
được chuyển thành một quyết định có trách nhiệm, có evidence và có thể audit.
Ba nhóm sử dụng trọng tâm là lender, investor và management.”

### Slide 1 — Mục tiêu và phạm vi hệ thống

“Hệ thống thu thập và chuẩn hóa financial/market data, kiểm tra quality và time
semantics, sau đó tạo risk score, label, driver và evidence theo từng thời điểm.
Foundation hiện tại là local-first và đã có contract/runtime evidence. Live API
hoặc stakeholder workflow là production hardening tiếp theo, vì vậy tôi phân biệt
rõ verified behavior với proposed design.”

### Slide 2 — Chuỗi giá trị dữ liệu và decision output

“Luồng xử lý đi từ source qua chuẩn hóa và DQ, tạo feature theo thời điểm, rồi
đưa vào risk output và decision workflow. Có ba contract cần bảo vệ: data
contract xác định dữ liệu là gì và đến từ đâu; model contract xác định score,
driver và threshold; decision contract xác định ai nhận kết quả và phải làm gì.”

### Slide 3 — Nguyên tắc thiết kế: stakeholder-centric risk intelligence

“Tôi không đánh giá hệ thống chỉ bằng câu hỏi model đạt accuracy bao nhiêu. Tôi
bắt đầu từ stakeholder, decision objective và cost of error; sau đó mới chọn
output, metric, threshold và explainability. Cuối cùng, kết quả phải đi vào
workflow và được đo bằng business impact. Đây là sự khác biệt giữa model-centric
và stakeholder-centric design.”

### Slide 4 — Một risk score, ba quyết định kinh doanh

“Nếu model trả về risk 82%, con số này chưa đủ để tạo ra business value. Lender
hỏi có nên cấp tín dụng; investor hỏi sức khỏe đang tốt lên hay xấu đi; management
hỏi yếu tố nào cần xử lý trước. Vì vậy không nên dùng một cách diễn giải, một
threshold hoặc một metric duy nhất cho cả ba nhóm.”

### Slide 5 — Ngân hàng: tín dụng và giám sát rủi ro

“Lender dùng output trong underwriting, điều chỉnh hạn mức và tái tục. Evidence
cần ưu tiên gồm leverage, liquidity, operating cash flow, profitability, interest
coverage, exposure, collateral và độ mới của dữ liệu. Output phù hợp là score/label
đi kèm driver, as-of date, provenance và lý do escalation; model hỗ trợ thẩm định,
không tự động phê duyệt hoặc từ chối.”

### Slide 6 — Ngân hàng: chính sách ngưỡng và escalation

“Với lender, false negative có thể gây tổn thất trực tiếp nếu hồ sơ bị đánh giá
an toàn nhưng thực tế có distress. Vì vậy recall thường quan trọng trong lớp
screening, nhưng giảm threshold quá thấp sẽ làm false positive và chi phí review
tăng. Có thể mô hình hóa policy bằng:

\`\`\`text
Recall    = TP / (TP + FN)
Precision = TP / (TP + FP)
Expected Loss(tau)
  = C_FN * FN(tau) + C_FP * FP(tau) + C_review * N_review(tau)
\`\`\`

Threshold phải được chọn theo risk appetite, portfolio và năng lực review; không
chọn theo accuracy đơn lẻ. Quy trình đúng là score vượt ngưỡng -> enhanced review
-> kiểm tra driver/evidence -> quyết định limit/collateral/approval -> audit trail
và theo dõi lại ở kỳ tiếp theo.”

### Slide 7 — Nhà đầu tư: nghiên cứu và giám sát danh mục

“Investor quan tâm đến trajectory hơn là một score cô lập. Ví dụ 20% -> 28% ->
51% -> 78% cho thấy xu hướng deteriorating và có thể ưu tiên company cho research
hoặc portfolio review. Cần kết hợp trend, change-point, peer/context, market
signal và confidence. Output là decision support, không phải lệnh mua/bán tự
động.”

### Slide 8 — Nhà đầu tư: explainability và chất lượng tín hiệu

“Risk 78% cần được giải thích bằng các yếu tố đóng góp như debt ratio tăng,
operating cash flow suy yếu, interest coverage và profitability giảm. Explanation
giúp analyst kiểm tra tính hợp lý và đặt câu hỏi tiếp theo, nhưng không được
diễn giải contribution thành causal claim. Các metric phù hợp gồm alert precision,
lead time, trend stability, driver consistency và coverage theo sector/size.”

### Slide 9 — Ban điều hành: early warning và remediation

“Management là người ở bên trong doanh nghiệp nên câu hỏi khác hoàn toàn: rủi ro
nào đang hình thành và cần ưu tiên xử lý ở đâu. Chuỗi 18% -> 25% -> 46% -> 71%
nên được chuyển thành operational alert. Driver phải gắn với hướng khắc phục:
nợ tăng liên quan đến debt structure; cash flow yếu liên quan đến liquidity,
receivables và working capital; chi phí tăng liên quan đến cost owner; vốn mỏng
liên quan đến capital plan.”

### Slide 10 — Ban điều hành: quy trình từ driver đến action

“Một alert có giá trị khi nó đi qua operating loop: risk alert và as-of date ->
driver và evidence -> owner và remediation plan -> follow-up measurement. Metrics
không chỉ là model performance mà còn gồm lead time, time-to-acknowledge,
time-to-mitigate, tỷ lệ alert có owner và residual-risk reduction.”

### Slide 11 — So sánh ba decision products

“Model backbone có thể dùng chung, nhưng decision product phải khác nhau. Lender
cần score, exposure và escalation; investor cần trend, explanation và signal
stability; management cần driver, owner, deadline và action status. Success measure
cũng khác: lender tối ưu theo cost of error, investor theo signal quality, còn
management theo time-to-action và mức giảm residual risk.”

### Slide 12 — Shared data contract và stakeholder-specific view

“Tôi giữ shared layer gồm entity, metric, period, source, effective time, DQ và
lineage. Trên đó là role layer gồm decision objective, threshold, evidence và
explanation. Governance layer chịu trách nhiệm human review, audit trail, access
control, feedback và xử lý conflict. Cách tách lớp này cho phép thêm stakeholder
view mà không phá vỡ downstream contract.”

### Slide 13 — Chuyển đổi nguồn: API và stakeholder research

“Tôi không thay toàn bộ API bằng free text. API vẫn phù hợp cho numeric facts,
market prices và dữ liệu tần suất cao. Stakeholder research bổ sung context,
observation, author/role, confidence, evidence và review status. Raw document,
normalized observation và mapping vào entity/metric/period cần được lưu tách biệt.
Nếu API fact và stakeholder judgement bất đồng, giữ conflict history và chờ
review; không âm thầm overwrite.”

### Slide 14 — Migration governance và acceptance criteria

“Migration cần shadow run trước cutover. Tôi kiểm tra contract compatibility, DQ,
freshness, source agreement, conflict resolution, decision usefulness và rollback
safety. Chỉ chuyển source khi có bằng chứng workflow tạo ra giá trị và vẫn giữ
snapshot/API fallback. Như vậy cutover là một quyết định có tiêu chí, không phải
thay đổi connector theo cảm tính.”

### Slide 15 — Kết luận

“Financial Distress Data không chỉ tạo ra prediction. Hệ thống cung cấp đúng
evidence, đúng threshold và đúng workflow cho từng stakeholder. Một model backbone
có thể phục vụ ba decision products, nhưng giá trị production chỉ xuất hiện khi
kết quả được giải thích, review và chuyển thành hành động có thể kiểm chứng.”

## Appendix — architecture, formula và Q&A notes

Phần dưới đây giữ các ghi chú implementation chi tiết để trả lời câu hỏi phụ.
Không dùng phần này làm thứ tự trình bày chính của deck hiện tại.

### Slide 1 — Business problem

**Trên slide:**

```text
Financial distress early warning for Vietnamese listed companies
```

**Nói:**

“Mục tiêu của project là phát hiện sớm các dấu hiệu financial distress của
doanh nghiệp niêm yết. Distress thường không xuất hiện từ một chỉ số duy nhất.
Nó có thể là thanh khoản yếu, nợ cao, âm vốn chủ sở hữu, lợi nhuận giảm, không
đủ khả năng trả lãi, giá biến động mạnh hoặc có thông tin tiêu cực từ thị
trường và stakeholder.

Vì vậy tôi xây dựng một data platform có khả năng gom các nguồn này, chuẩn hóa,
kiểm tra và tạo ra một company-quarter risk view có thể audit.”

### Slide 2 — Người dùng và output

**Trên slide:**

```text
Data Engineer -> owns pipeline
Analyst        -> investigates risk
ML Engineer    -> consumes features and labels
Stakeholder    -> submits/reviews research signals
Operator       -> owns runtime and governance
```

**Nói:**

“Data engineer quản lý ingestion và quality. Analyst cần xem công ty nào có
rủi ro, vì sao rủi ro và nguồn nào chứng minh điều đó. ML engineer dùng Gold
features và eligible labels. Stakeholder hoặc analyst cung cấp research signal
nhưng signal đó phải có source, confidence và review status. Operator quản lý
runtime, access, cost và observability.”

Output chính là:

- `fact_financial_statement`;
- `fact_market_price`;
- `distress_labels`;
- `obt_company_quarter_risk`;
- financial, market, news và unified feature tables.

### Slide 3 — Architecture overview

**Trên slide:**

```text
API / official disclosure / stakeholder research
        -> Bronze raw evidence
        -> Silver canonical data
        -> Gold facts and features
        -> DQ + metadata + lineage
        -> Dashboard / ML / RAG / product
```

**Nói:**

“Bronze giữ raw evidence để replay và audit. Silver là nơi chuẩn hóa tên cột,
kiểu dữ liệu, nullable fields, business keys và deduplication. Gold là lớp phục
vụ analyst và downstream consumers. DQ và metadata chạy song song để mỗi run
đều có status, row counts, freshness, errors, source request và checkpoint.”

### Slide 4 — Ingestion và streaming

**Nói:**

“Batch ingestion lấy company master, quarterly financial statements và daily
market prices. Streaming dùng Kafka cho price events, news events và market
alerts. Tất cả collector phụ thuộc vào một adapter contract, nên khi đổi nguồn
thì collector và downstream transforms không cần biết chi tiết vendor.”

Các Kafka topic hiện tại:

```text
financial.price_events
financial.news_events
financial.alert_events
```

“Fixture generator cố ý tạo duplicate, late arrival, burst và legacy null để
kiểm tra các failure mode trước khi có live source.”

### Slide 5 — Bronze, Silver và Gold

**Nói:**

“Bronze append-compatible và lưu source fields cùng ingestion metadata. Silver
normalize column names, validate required fields, route invalid rows sang
failed-record structure và giữ record mới nhất theo business key + `created_ts`.
Gold tạo dimension, fact, label, OBT và feature tables.”

Business keys:

```text
companies              -> ticker
financial_statements   -> ticker + report_period
market_prices_daily    -> ticker + trading_date
stream events          -> event_id
```

Dimension company dùng SCD Type 2 để giữ lịch sử thay đổi ngành, sàn, sector
hoặc trạng thái delisted.

### Slide 6 — Time semantics và leakage prevention

**Nói:**

“Có bốn loại timestamp không được nhầm lẫn.”

| Field | Ý nghĩa |
|---|---|
| `event_timestamp` | business event xảy ra khi nào |
| `created_ts` | source tạo record khi nào |
| `ingest_ts` | record vào Bronze khi nào |
| `report_release_date` | báo cáo được công bố khi nào |

“Khi tạo feature cho báo cáo quý, chỉ được dùng feature có thời điểm công bố
nhỏ hơn hoặc bằng `report_release_date`.”

```text
feature_event_timestamp <= reference_event_timestamp
```

Ví dụ: BCTC được công bố ngày 28/03 thì giá ngày 20/03 được dùng, giá ngày
05/04 không được dùng. Điều này ngăn future leakage khi sau này train model.

### Slide 7 — Nội dung phân tích và công thức

**Nói:**

“Ở Gold OBT, mỗi dòng có grain là một công ty trong một quý. Hệ thống tính
thanh khoản, đòn bẩy, hiệu quả sử dụng vốn, khả năng trả lãi và một Z-Score
proxy.”

Các chỉ số:

```text
current_ratio       = current_assets / current_liabilities
debt_to_asset       = total_liabilities / total_assets
debt_to_equity      = total_liabilities / equity
ROA                 = net_income / total_assets
ROE                 = net_income / equity
interest_coverage   = EBIT / interest_expense
```

Market return:

```text
daily_return = (close_today - close_previous_day) / close_previous_day
```

```text
abs(daily_return) > 0.07 -> volatility_signal = true
```

### Slide 8 — Z-Score và distress label

**Nói:**

“Z-Score ở đây là một biến thể Altman Z double-prime-inspired. Nó là rule-based
proxy để tạo baseline minh bạch, chưa phải model credit-risk đã được validate.”

```text
X1 = (current_assets - current_liabilities) / total_assets
X2 = retained_earnings / total_assets
X3 = EBIT / total_assets
X4 = equity / total_liabilities
```

```text
Z = 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4
```

Ngưỡng:

```text
Z < 1.1        -> distress zone
Z > 2.6        -> safe zone
1.1..2.6       -> gray zone
```

Warning rules:

```text
debt_to_asset > 0.8
current_ratio < 1.0
hai quý liên tiếp net_income < 0
equity < 0
interest_coverage < 1.0
```

Label logic:

```text
Z < 1.1 hoặc warning_count >= 2
    -> distress_label = 1

Z > 2.6 và warning_count < 2
    -> distress_label = 0

gray zone
    -> distress_label = 0, nhưng training_eligible = false
```

Nếu thiếu dữ liệu:

```text
Z = NULL và warning_count >= 2 -> label 1, confidence medium
Z = NULL và warning_count < 2  -> label NULL, insufficient_data
```

Financial sector hiện được loại khỏi rule này theo sector policy để tránh áp
dụng cùng một logic cho ngành có balance sheet đặc thù.

### Slide 9 — Ví dụ AAA

**Trên slide:**

```text
Assets = 1000             Liabilities = 500
Current assets = 300      Current liabilities = 200
Equity = 500              Retained earnings = 150
EBIT = 120                Interest expense = 20
Net income = 80
```

**Nói:**

```text
current_ratio      = 300 / 200 = 1.5
debt_to_asset      = 500 / 1000 = 0.5
ROA                = 80 / 1000 = 0.08
ROE                = 80 / 500 = 0.16
interest_coverage  = 120 / 20 = 6.0
```

```text
X1 = 100 / 1000 = 0.10
X2 = 150 / 1000 = 0.15
X3 = 120 / 1000 = 0.12
X4 = 500 / 500 = 1.00

Z = 6.56*0.10 + 3.26*0.15 + 6.72*0.12 + 1.05*1.00
Z = 3.0014
```

“AAA có Z lớn hơn 2.6, không có warning nghiêm trọng, nên `label = 0`,
confidence high và training eligible.”

### Slide 10 — Ví dụ BBB

**Trên slide:**

```text
Assets = 1000             Liabilities = 900
Current assets = 100      Current liabilities = 250
Equity = -50              Retained earnings = -100
EBIT = 10                 Interest expense = 20
Net income = -30
```

**Nói:**

```text
current_ratio      = 100 / 250 = 0.4
debt_to_asset      = 900 / 1000 = 0.9
ROA                = -30 / 1000 = -0.03
interest_coverage  = 10 / 20 = 0.5
```

```text
X1 = -150 / 1000 = -0.15
X2 = -100 / 1000 = -0.10
X3 = 10 / 1000 = 0.01
X4 = -50 / 900 = -0.0556

Z ≈ -1.3011
```

“BBB có Z nhỏ hơn 1.1, debt-to-asset cao, current ratio thấp, equity âm và
interest coverage yếu. Vì vậy `label = 1`, confidence high và reason lưu lại
từng warning để analyst hiểu vì sao.”

### Slide 11 — Data Quality và metadata

**Nói:**

“Không phải record nào cũng được đưa xuống Gold. Critical DQ failure sẽ halt
downstream. Warning được log và có thể route record sang failed records nhưng
pipeline vẫn tiếp tục.”

Critical checks:

- required key không null;
- business key unique;
- schema match registry;
- fact key tồn tại trong dimension.

Warning checks:

- freshness lag;
- asset range;
- sentiment range;
- volume drop;
- Silver retention.

PostgreSQL `ops` lưu:

```text
pipeline_run_log
data_quality_result
dataset_freshness
schema_version_registry
failed_records
backfill_request
source_request_log
collector_checkpoint
```

### Slide 12 — Chuyển từ API sang stakeholder research

**Nói:**

“Tôi không thay toàn bộ API bằng free text. API vẫn phù hợp cho financial facts,
market prices và dữ liệu có tần suất cao. Stakeholder research được đưa vào như
một source domain riêng cho context, risk drivers, watchlist, outlook và human
reviewed labels.”

Source taxonomy:

| Source | Dùng cho |
|---|---|
| Official/company disclosure | financial facts, material events |
| Market/API | price, volume, volatility |
| News/research documents | narrative và citations |
| Analyst/stakeholder | risk drivers, outlook, watchlist |
| Credit/outcome system | confirmed distress outcomes |

Stakeholder observation tối thiểu:

```text
observation_id
ticker / company_key
observation_type
claim_text
value_numeric / value_text / unit
observation_date
effective_from / effective_to
source_type / source_uri / document_hash
author_role
confidence
review_status
access_class / pii_status
created_ts / updated_ts
```

Pipeline mới:

```text
stakeholder form / upload / approved document
    -> Bronze raw document or observation
    -> hash + PII + access scan
    -> Silver normalize and validate
    -> human review / conflict resolution
    -> Gold stakeholder signals
    -> PIT join with financial and market facts
```

“Không overwrite khi hai người đưa ra thông tin khác nhau. Lưu cả hai, đánh dấu
conflict và chỉ tạo resolved view sau khi có precedence hoặc reviewer decision.”

### Stakeholder deep dive — phần cần trình bày kỹ

Phần speaker notes chi tiết cho stakeholder research đã được tách sang
[Onboarding stakeholder deep dive](onboarding-stakeholder-deep-dive.md).

### Slide 13 — Stakeholder signal formula

Đây là công thức đề xuất cho production, không phải công thức đang implement
trong the platform:

```text
human_risk_signal =
    sum(source_weight
        * confidence_weight
        * review_weight
        * direction
        * recency_decay)
    / sum(source_weight * confidence_weight * review_weight)
```

Trong đó:

```text
direction = +1 risk, 0 neutral, -1 positive
recency_decay = exp(-lambda * age_in_days)
```

Signal này nên là feature hoặc analyst-ranking signal. Không dùng thẳng làm
ground-truth label nếu chưa có outcome definition và approval process.

### Slide 14 — Production migration plan

**Nói:**

“Migration được thực hiện theo shadow run, không cutover ngay.”

1. Implement stakeholder adapter theo source contract.
2. Tạo schema và mapping cho observation/document/review.
3. Chạy API và stakeholder source song song.
4. So sánh entity resolution, units, periods, duplicates, nulls và freshness.
5. Review conflict, low-confidence và PII records.
6. Backfill snapshot đã được approve.
7. Cutover có versioned source registry và fallback.
8. Rollback bằng đổi source-registry version, không xóa dữ liệu.

### Slide 15 — the platform AI/product direction

**Nói:**

“the platform xây trên Gold foundation. RAG pipeline fetches trusted documents,
normalizes, chunks, deduplicates theo content hash, kiểm tra license/access/PII,
embed và lưu vào PGVector. Product plane phục vụ analyst; evidence plane chứa
feature/RAG services, agents, MCP, observability và deployment controls.”

Điểm cần nói thật:

- the platform là additive, không sửa semantic the platform.
- RAG evidence mặc định còn dùng committed text fixtures.
- Không gọi fixture UI là live production data.
- Không claim component là deployed nếu chưa có runtime evidence.

### Slide 16 — Kết luận

**Nói:**

“Giá trị của project là data contract và trust layer. Khi source thay đổi từ API
sang stakeholder research, tôi không cần viết lại toàn bộ pipeline. Tôi chỉ thay
adapter và thêm một governed domain cho observation/review/provenance. Bronze,
Silver, Gold, DQ, PIT và metadata vẫn bảo vệ downstream consumers.”

Roadmap:

```text
live adapter
    -> stakeholder schema
    -> shadow run
    -> review and backfill
    -> controlled cutover
    -> model and AI validation
```

## Formula cheat sheet

```text
current_ratio       = current_assets / current_liabilities
debt_to_asset       = total_liabilities / total_assets
debt_to_equity      = total_liabilities / equity
ROA                 = net_income / total_assets
ROE                 = net_income / equity
interest_coverage   = EBIT / interest_expense
daily_return        = (close_t - close_t_minus_1) / close_t_minus_1
```

```text
X1 = (current_assets - current_liabilities) / total_assets
X2 = retained_earnings / total_assets
X3 = EBIT / total_assets
Z = 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4
```

```text
Z < 1.1 -> distress
Z > 2.6 -> safe
otherwise -> gray zone
```

```text
feature_event_timestamp <= reference_event_timestamp
```

## Q&A script

### “Dữ liệu hiện tại có phải live API không?”

“Chưa. Current adapter là deterministic fixture để CI và runtime evidence ổn
định. Nhưng collector phụ thuộc vào `SourceAdapter` contract, nên live adapter
có thể được đưa vào mà không thay đổi downstream schema và transforms.”

### “Tại sao dùng fixture?”

“Để kiểm tra đúng pipeline semantics mà không phụ thuộc network, rate limit hoặc
vendor schema. Fixture còn mô phỏng duplicate, late arrival, burst và null
schema.”

### “Z-Score có phải machine learning không?”

“Không. Đây là rule-based baseline lấy cảm hứng từ Altman Z''. ML là bước tiếp
theo, cần outcome labels, temporal split, validation và model monitoring.”

### “Nếu API và stakeholder nói khác nhau thì sao?”

“Không overwrite. Lưu cả hai observation, gắn source, confidence, effective
time và review status. Precedence phải được định nghĩa theo từng field.”

### “Stakeholder label có thể dùng train model không?”

“Chỉ khi label có definition, observation window, reviewer authority và outcome
semantics rõ. Nếu chưa, nó là feature hoặc weak annotation, không phải ground
truth.”

### “Làm sao chống data leakage?”

“Dùng report release time hoặc business effective time làm reference boundary.
Feature được publish sau thời điểm đó bị loại. Validation phải chứng minh
future-feature leakage bằng zero.”

### “Production-ready chưa?”

“Data-engineering foundation đã được verify local end-to-end. Full production
scope vẫn cần live source connector, stakeholder review/access control, scale
testing, licensing/compliance và model validation.”

## Một phút trước khi vào meeting

Nhớ 7 ý:

1. Business problem: early warning financial distress.
2. Grain: one company + one quarter.
3. Flow: Source → Bronze → Silver → Gold.
4. Gold: facts, ratios, labels, features.
5. Trust: DQ, metadata, lineage, PIT.
6. Formula: ratios + Z-Score-inspired rules.
7. Production: API và stakeholder source coexist with provenance/review.

## References trong repo

- [the platform source of truth](mini_coursework.md)
- [Data generator contract](01_data_generator.md)
- [Schema design](architecture/data-model.md)
- [Data contracts](07_data_contracts.md)
- [System architecture](system-architecture.md)
- [Onboarding production research briefing](../plans/reports/research-260809-1944-financial-distress-onboard-production.md)
- [Distress label implementation](../src/transforms/compute_distress_labels.py)
- [Risk OBT implementation](../src/transforms/gold/obt_company_quarter_risk.py)
- [PIT feature implementation](../src/transforms/features/point_in_time.py)
