---
title: "Financial Distress Data — Onboarding Stakeholder Deep Dive"
date: 2026-08-09
status: study-guide
audience: "Project onboarding / production architecture meeting"
---

# Financial Distress Data — Onboarding Stakeholder Deep Dive

Tài liệu này tiếp tục phần Slide 12 của
[Onboarding Presentation Script](onboarding-presentation-script.md) và giữ
speaker notes chi tiết về stakeholder research.

## Stakeholder deep dive — phần cần trình bày kỹ

Phần này tương ứng với cụm slide stakeholder trong Beamer. Khi thuyết trình,
đừng mô tả stakeholder như một “API khác”. API thường trả về các fact có schema
ổn định; stakeholder research trả về evidence, claim, context và judgement có
authority, confidence, thời điểm hiệu lực và trạng thái review. Vì vậy đây là
một domain có lifecycle riêng nhưng vẫn đi qua cùng Bronze / Silver / Gold.

#### 12A. Ai là stakeholder và họ tạo ra loại thông tin nào?

| Vai trò | Họ biết gì | Giá trị cho hệ thống | Quyền quyết định |
|---|---|---|---|
| IR / company representative | giải thích hoạt động, sự kiện, kế hoạch | context và clarification | không tự động xác nhận distress |
| Auditor / accountant | chất lượng báo cáo, caveat, accounting issue | evidence có authority cao cho reporting facts | có thể xác nhận hoặc phản biện accounting claim |
| Lender / credit officer | covenant, repayment, liquidity pressure | early warning về khả năng trả nợ | đóng góp risk assessment, không thay outcome label |
| Analyst / researcher | risk drivers, outlook, thesis, watchlist | narrative, hypothesis, ranking signal | tạo claim cần review và provenance |
| Risk committee / reviewer | đánh giá conflict và materiality | resolved view và approval | duyệt signal dùng downstream |
| Operations / data steward | access, PII, retention, lineage | governance và vận hành | quyết định dữ liệu có được đưa vào pipeline hay không |

Speaker script:

> “Stakeholder không phải một nguồn sự thật duy nhất. Mỗi vai trò có authority
> khác nhau và trả lời câu hỏi khác nhau. Auditor mạnh ở reporting evidence,
> lender mạnh ở repayment pressure, analyst mạnh ở interpretation. Hệ thống
> giữ riêng author role, claim, evidence và reviewer decision để không biến
> opinion thành fact.”

#### 12B. Phân loại thông tin: fact, claim, signal, outcome

Trên slide cần giải thích bốn lớp, vì đây là điểm dễ bị hỏi:

```text
Evidence / document  ->  Claim / observation  ->  Reviewed signal  ->  Outcome label
       chứng cứ             nhận định                 tín hiệu              kết quả đã biết
```

- **Evidence**: tài liệu, URL, file, meeting note hoặc đoạn trích có hash.
- **Claim/observation**: một phát biểu có subject, predicate, value và thời gian.
- **Reviewed signal**: claim đã được reviewer đánh giá, có thể dùng để ranking,
  alert hoặc feature.
- **Outcome label**: kết quả quan sát được sau đó, ví dụ event đã xảy ra. Label
  phải được tạo theo time boundary, không lấy từ dự đoán của stakeholder.

Speaker script:

> “Tôi không đưa toàn bộ free text vào model. Tôi tách evidence khỏi claim,
> claim khỏi reviewed signal, và reviewed signal khỏi outcome label. Nhờ vậy
> analyst vẫn đọc được context, còn ML không bị label leakage.”

#### 12C. Domain model nên có những thực thể nào?

Giải thích bốn thực thể chính:

| Entity | Một record đại diện cho | Khóa/quan hệ quan trọng |
|---|---|---|
| `research_document` | tài liệu gốc hoặc meeting note | `document_id`, `document_hash`, source, access class |
| `research_chunk` | đoạn nhỏ có vị trí trong document | `chunk_id`, `document_id`, offset/page |
| `stakeholder_observation` | claim hoặc numeric/narrative signal | `observation_id`, `company_key`, observation time |
| `stakeholder_review` | quyết định approve/reject/conflict | `review_id`, observation, reviewer, reviewed time |
| `stakeholder_label` | label đã được phép dùng downstream | `label_id`, observation, policy/version |

Nguyên tắc quan hệ:

```text
document 1 --- N chunk
document 1 --- N observation
observation 1 --- N review
observation 0 --- 1 resolved label
```

Không nên chỉ lưu một cột `stakeholder_comment` trên bảng financial. Cách đó
làm mất provenance, không phân biệt được nhiều người nói khác nhau và không
giải quyết được correction hoặc conflict.

#### 12D. Observation contract — giải thích từng nhóm field

Contract tối thiểu:

```text
observation_id, company_key, observation_type
claim_text, value_numeric, value_text, unit
observation_date, effective_from, effective_to
source_type, source_uri, document_hash, author_role
confidence, review_status, access_class, pii_status
created_ts, updated_ts, schema_version
```

Khi bị hỏi “tại sao nhiều field như vậy?”, trả lời theo nhóm:

1. **Identity** — `observation_id`, `company_key`, `observation_type` giúp
   dedupe, join đúng doanh nghiệp và biết đây là liquidity, covenant, event hay
   outlook signal.
2. **Content** — `claim_text` giữ nguyên lời giải thích; `value_numeric`,
   `value_text`, `unit` cho phép vừa search narrative vừa tính toán có kiểm soát.
3. **Time** — `observation_date` là lúc ghi nhận; `effective_from/to` là lúc
   claim có hiệu lực. Hai thời gian này không được gộp tùy tiện.
4. **Provenance** — `source_type`, `source_uri`, `document_hash`, `author_role`
   cho biết claim đến từ đâu, ai nói và có thể replay/audit không.
5. **Governance** — `confidence`, `review_status`, `access_class`, `pii_status`
   quyết định record có được phục vụ analyst, model hay RAG hay chưa.
6. **Change control** — `created_ts`, `updated_ts`, `schema_version` giúp theo
   dõi correction và tránh silently overwrite lịch sử.

Speaker script:

> “Observation contract là boundary giữa thông tin con người và data platform.
> Tôi giữ cả nội dung lẫn metadata để downstream biết record này là gì, có hiệu
> lực khi nào, do ai tạo, mức tin cậy bao nhiêu và đã được duyệt chưa.”

#### 12E. Lifecycle production: từ capture đến Gold

```text
Capture form / upload / approved connector
        |
        v
Bronze: raw document + raw observation + ingest metadata
        |
        +--> hash, malware/PII/access scan, quarantine nếu fail
        |
        v
Silver: entity resolution + type/unit/time normalization + dedupe
        |
        +--> reviewer queue cho low confidence hoặc conflict
        |
        v
Gold: approved signal + provenance + valid_from/valid_to
        |
        v
Point-in-time join với financial, market và news features
```

Cách giải thích:

- **Bronze** không sửa raw input; nếu source gửi correction, append record mới.
- **Silver** chuẩn hóa ticker/company, loại signal, đơn vị tiền tệ, timezone,
  effective period và business key.
- **Gold** chỉ chứa signal đủ điều kiện downstream, có review/version và vẫn
  trỏ về evidence gốc.
- **PIT join** chỉ cho phép signal đã tồn tại trước reference timestamp đi vào
  feature của thời điểm đó.

#### 12F. Authority, confidence và review status không giống nhau

Ba khái niệm thường bị trộn:

| Khái niệm | Câu hỏi trả lời | Ví dụ |
|---|---|---|
| Authority | Người/nguồn này có vị thế gì cho claim này? | auditor cao cho accounting caveat |
| Confidence | Người tạo tin claim đúng đến mức nào? | analyst tự đánh giá 0.7 |
| Review status | Tổ chức đã kiểm tra và cho phép dùng chưa? | `pending`, `approved`, `rejected`, `conflict` |

Quy tắc đề xuất:

```text
raw observation -> không dùng trực tiếp cho label/model
approved signal -> được dùng cho analyst/ranking, subject to policy
resolved label  -> chỉ dùng train/evaluation khi time-safe và outcome-defined
```

Một record có confidence 0.95 vẫn có thể `pending`. Ngược lại, một claim từ
nguồn có authority cao nhưng chưa đủ evidence vẫn cần reviewer kiểm tra.

#### 12G. Conflict resolution — khi stakeholder nói khác nhau

Ví dụ: analyst ghi “liquidity pressure cao trong Q3”; IR phản hồi “đã có
refinancing, pressure giảm”. Hệ thống không chọn record cuối cùng theo
`updated_ts`.

Quy trình:

1. Lưu cả hai observation và link về evidence/document.
2. Chuẩn hóa chúng về cùng `company_key`, period, unit và observation type.
3. Đánh dấu `conflict` nếu predicate hoặc value mâu thuẫn.
4. Reviewer xem authority, thời điểm hiệu lực, materiality và evidence.
5. Tạo resolved view có `resolution_reason`, reviewer, policy version và
   timestamp; không xóa raw history.
6. Nếu chưa giải quyết, Gold có thể phát `conflict_flag` thay vì một signal giả
   chính xác.

Công thức precedence nên được version hóa, ví dụ:

```text
priority = authority_weight
         * evidence_quality
         * review_weight
         * recency_decay
```

Đây là cơ chế hỗ trợ reviewer, không phải giấy phép tự động biến score cao
thành sự thật. Với material conflict, human review vẫn là gate.

#### 12H. Stakeholder signal và cách tính

Đây là công thức đề xuất cho ranking/feature, không phải công thức Phase 1 đã
implement:

```text
S_human(t) =
  sum(w_source * w_confidence * w_review * direction * exp(-lambda * age_days))
  ---------------------------------------------------------------------------
  sum(w_source * w_confidence * w_review)
```

Trong đó:

- `direction = +1` nếu claim cảnh báo risk, `0` nếu neutral, `-1` nếu positive;
- `w_source` phản ánh authority của role/source cho loại claim đó;
- `w_confidence` là confidence chuẩn hóa, ví dụ 0–1;
- `w_review = 0` cho `rejected`, thấp cho `pending`, bằng 1 cho `approved`;
- `age_days = reference_date - effective_from`, không dùng thời điểm ingest nếu
  claim có effective date rõ ràng;
- `lambda` điều khiển decay, phải chọn bằng backtest/governance chứ không đoán.

Điểm cần nhấn mạnh:

> “Signal là evidence-weighted human signal. Nó giúp analyst xếp hạng và mở
> alert, nhưng không tự động trở thành ground truth. Ground truth phải đến từ
> outcome definition độc lập.”

#### 12I. Label leakage — câu hỏi production quan trọng nhất

Với reference time `t`, feature stakeholder chỉ hợp lệ nếu:

```text
feature_effective_from <= t
and review_completed_at <= t
and source_event_time <= t
```

Nếu reviewer duyệt claim sau khi distress đã xảy ra, claim đó có thể biết trước
kết quả và làm model “đẹp giả”. Cần lưu riêng:

```text
source_event_time      # sự kiện/claim xảy ra
observed_at            # hệ thống nhận được
review_completed_at    # reviewer duyệt
label_event_time       # outcome thực tế
```

Trong training snapshot, chỉ dùng record thỏa time boundary. Nếu không xác định
được thời điểm, record có thể dùng cho qualitative research nhưng bị loại khỏi
training/evaluation.

#### 12J. Acceptance criteria cho stakeholder production

| Actor | Action | Result |
|---|---|---|
| Collector | ingest document/observation | tạo raw record append-only, có hash và source provenance |
| Entity resolver | map ticker/company | map được canonical `company_key` hoặc đưa vào quarantine |
| DQ job | validate required fields/time/unit | ghi `data_quality_result`, critical fail chặn Gold |
| Reviewer | approve/reject/conflict | tạo review event, không overwrite observation |
| Gold job | publish approved signal | chỉ publish record đủ policy và có valid time interval |
| Feature builder | PIT join | không dùng signal đến sau reference timestamp |
| RAG/API | retrieve evidence | trả citation, access check và review status |
| Operator | monitor freshness/conflict/PII | alert có owner, SLA và runbook |

Kết luận phần stakeholder:

> “Thiết kế này giữ được tốc độ của API cho numeric facts và thêm chiều sâu của
> con người cho context/risk interpretation. Boundary ổn định là canonical
> company, observation contract, provenance, review và point-in-time semantics.”


## Quay lại presentation script

Tiếp tục với
[Slide 13 — Stakeholder signal formula](onboarding-presentation-script.md#slide-13--stakeholder-signal-formula).
