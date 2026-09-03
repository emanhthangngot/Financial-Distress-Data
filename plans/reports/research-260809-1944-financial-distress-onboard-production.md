---
title: "Financial Distress Data — Onboarding and Production Research Briefing"
date: 2026-08-09
status: prepared
scope: "Repository research, onboarding narrative, and stakeholder-source migration design"
---

# Financial Distress Data — Onboarding and Production Research Briefing

## Executive summary

Đây là một data platform cho early-warning financial distress của doanh nghiệp
niêm yết Việt Nam. Mục tiêu không chỉ là tính một điểm rủi ro, mà là tạo một
chuỗi dữ liệu có thể kiểm chứng:

```text
source data -> Bronze raw evidence -> Silver canonical data -> Gold facts/features
            -> DQ + metadata + lineage -> analyst / ML / RAG / product consumers
```

Project có hai lớp:

1. **Phase 1 — verified local-first lakehouse:** Airflow, Kafka, MinIO,
   PostgreSQL, PySpark, DuckDB/DBeaver và PyTest.
2. **Phase 2 — additive AI/product direction:** RAG, feature serving, drift,
   agents/MCP, product UI và GitOps/evidence plane. Phase 2 không được làm thay
   đổi semantic của Phase 1.

Thông điệp production nên dùng:

> API/market feed cung cấp số liệu có cấu trúc và tần suất cao; stakeholder
> research cung cấp context, qualitative signals và human-reviewed labels. Hai
> nguồn được hợp nhất bằng canonical contracts, effective time, confidence và
> provenance — không thay thế mù quáng cho nhau.

## 1. What is implemented versus planned

| Area | Repository evidence | Honest status for the meeting |
|---|---|---|
| Source boundary | `SourceAdapter` protocol; collectors call `fetch_companies`, `fetch_financial_statements`, `fetch_market_prices` | Implemented contract |
| Live market connector | `src/collectors/source_adapters/vnstock_adapter.py` currently re-exports the fixture adapter | Live API integration is a next step, not current evidence |
| Deterministic input | `VnstockFixtureAdapter`, configurable generator and streaming problem factory | Implemented for CI/smoke/evidence |
| Bronze/Silver/Gold | MinIO Parquet paths, Python helpers and Spark-compatible transforms | Implemented and tested; local runtime evidence exists |
| Streaming | Kafka topics, event contracts, micro-batch consumer and Bronze partitions | Implemented as local contract/runtime path |
| DQ/metadata | PostgreSQL `ops`, in-memory writer, critical/warning semantics | Implemented |
| Feature correctness | PIT joins based on `report_release_date`/`event_timestamp` | Implemented contract and validation |
| Distress labels | Rule-based Altman Z''-inspired labeler with warnings, confidence and rule version | Implemented; not an ML model |
| RAG | Chunking, hash dedupe, governance, embedding backend and PGVector store | Additive Phase 2 code; default evidence path still uses committed text fixtures |
| Product UI | Next.js app with fixture/Supabase data ports and honest cached/offline states | UI/product contracts exist; do not call fixture screens live production data |
| Agent platform | Documentation/rubric describe agents and MCP; `src/agents/` is not present in the current checkout | Target/partial Phase 2, not claim as fully deployed |

The checked-in Stage 1 evidence reports a passing local E2E path, including
Bronze/Silver/Gold objects, Kafka offsets, PostgreSQL metadata and DuckDB
validation. The strongest evidence-backed numbers in the repository are 16
financial statement rows, 2 company rows, 732 date rows, 12 market-feature
rows, 2 news-sentiment rows and zero future-feature-leakage rows in the sample
evidence. These are runtime evidence samples, not a production-scale volume
claim.

## 2. Business problem and users

### Business problem

Financial distress often appears as a combination of weak liquidity, increasing
leverage, negative equity, weak interest coverage, recurring losses, adverse
market movement and negative disclosures. A single source is incomplete. The
platform produces a reliable, time-aware company-quarter risk view for early
warning and research.

### Users

- **Data engineer:** owns ingestion, DAGs, Kafka, transforms, DQ, metadata and
  lakehouse operations.
- **Risk/financial analyst:** investigates a ticker, its quarterly ratios,
  signals, sources and explanation.
- **ML engineer:** consumes Gold features and eligible labels for later model
  training and monitoring.
- **Research/stakeholder contributor:** submits or reviews qualitative findings,
  source documents and risk assessments.
- **Platform/operator:** manages runtime, access, cost, observability and
  deployment state.

## 3. Current Phase 1 architecture

### Ingestion

Batch datasets:

- company master: ticker, name, exchange, industry/sector, listing metadata;
- quarterly financial statements: assets, liabilities, equity, revenue, EBIT,
  interest expense, net income, operating cash flow and retained earnings;
- daily market prices: OHLCV and market metadata.

Streaming datasets:

- `financial.price_events`;
- `financial.news_events`;
- `financial.alert_events`.

The source adapter boundary lets the collector remain stable while the backing
source changes. The fixture adapter deliberately creates deterministic rows,
duplicates, legacy nulls, skew, bursts and late arrivals so the contracts can be
tested without network dependency.

### Medallion flow

```text
Source adapter / Kafka
        |
        v
Bronze: append-compatible raw records + source/ingest metadata
        |
        v
Silver: normalized names/types + schema alignment + rejected rows + latest dedupe
        |
        v
Gold: dimensions, facts, labels, OBT and model-ready feature families
        |
        +--> PostgreSQL operational metadata
        +--> DuckDB/httpfs inspection and DBeaver evidence
```

Bronze preserves replay/audit evidence. Silver is the canonical clean layer.
Gold is consumer-facing and idempotent on affected output partitions/prefixes.

### Keys and time

- `company_key = sha256(upper(ticker))[:16]`;
- `date_key = YYYYMMDD`;
- business-key dedupe keeps the latest `created_ts`;
- `dim_company` supports SCD2 history;
- financial facts resolve company history using a valid-time interval.

Four timestamps must not be confused:

| Timestamp | Meaning |
|---|---|
| `event_timestamp` | when the business event happened |
| `created_ts` | when the source/normalized record was created |
| `ingest_ts` | when the record entered Bronze |
| `report_release_date` | when a financial report became available to analysts |

Point-in-time features use the reference/release time and reject future market
or news rows. This is the core defense against training leakage.

### Gold outputs

- `dim_company`, `dim_date`;
- `fact_financial_statement`, `fact_market_price`, `fact_news_sentiment`,
  `fact_market_alert`;
- `distress_labels`;
- `obt_company_quarter_risk`;
- `feat_company_financial_4q`, `feat_company_market_30d`,
  `feat_company_news_30d`, `feat_company_unified`.

The OBT contains ratios such as current ratio, debt-to-asset, debt-to-equity,
ROA, ROE and EBIT-interest coverage, together with label reason, confidence,
source and rule version.

### Labeling logic

Phase 1 uses a transparent rule-based proxy, not learned inference:

- Altman Z''-inspired ratios;
- high debt-to-asset;
- low current ratio;
- two consecutive quarterly losses;
- negative equity;
- weak interest coverage;
- financial-sector exclusion policy;
- `training_eligible`, `label_confidence`, `label_source` and `rule_version`.

This design is useful for a baseline and for generating auditable labels, but it
must not be presented as a validated credit-risk model. In production, labels
need a business definition, historical outcome window and approval process.

### Quality and governance

Critical failures halt downstream publication. Warning failures are recorded
and can route rows to failed-record storage while allowing the run to continue.

Typical checks:

- required/business keys not null;
- business-key uniqueness;
- schema matches registry;
- dimension/fact referential integrity;
- non-negative assets and bounded sentiment;
- freshness SLA;
- volume/retention change.

`ops` records pipeline runs, DQ results, dataset freshness, schema
versions, failed records, backfill requests, source request logs and collector
checkpoints. This is what makes a data result operationally explainable.

## 4. Production source migration: API to stakeholder research

### Correct interpretation

Do not replace every API with free text. Split the source domain by what each
source is authoritative for:

| Source family | Best use | Example canonical output |
|---|---|---|
| Official/company disclosure | reported financial facts, material events, governance | financial facts, disclosure events |
| Market/price feed | high-frequency price, volume, volatility | market facts/features |
| News/research documents | narrative context and cited claims | RAG documents/chunks |
| Internal analyst/stakeholder research | hypotheses, watchlists, risk drivers, review labels | stakeholder signals/annotations |
| Outcome/credit operations | confirmed distress outcome | approved target label |

The official SSC disclosure system is a suitable primary landing source for
public disclosures; the official disclosure guidance covers periodic financial
statements, annual reports, AGM materials and extraordinary/requested
disclosures. Current legal/compliance checks must be performed before relying
on any specific deadline or interpretation. See the [SSC disclosure portal](https://congbothongtin.ssc.gov.vn/)
and the [official disclosure guidance](https://ssc.gov.vn/webcenter/contentattachfile/idcplg?IdcService=GET_FILE&IsAttachment=1&Rendition=Th%C3%B4ng+t%C6%B0+96%2F2020%2FTT-BTC&allowInterrupt=1&dDocName=APPSSCGOVVN162136400&dID=98974&filename=Thong+tu+so+96+cua+Bo+truong+Bo+Tai+chinh+huong+dan+CBTT+tren+thi+truong+chung-khoan_ngay+16-11-2020_Final.pdf).

`vnstock` remains useful as an extraction/access library for market and
fundamental data, but the repository correctly treats the adapter—not the
vendor SDK—as the stable contract. Its current documentation covers market,
fundamental and disclosure/event groups, while its own project disclaimer says
data should be independently checked before financial decisions. See the
[vnstock project](https://github.com/thinh-vu/vnstock) and [fundamental data docs](https://vnstocks.com/docs/vnstock-data/fundamental-layer-v3).

### Proposed stakeholder domain model

Keep original documents and human observations separate:

1. `research_document`: immutable document/meeting/transcript metadata;
2. `research_chunk`: normalized text chunks for RAG, with source URI and hash;
3. `stakeholder_observation`: a structured human assertion or signal;
4. `stakeholder_review`: review/approval/rejection history;
5. `stakeholder_label`: only approved outcome labels used for training.

Minimum `stakeholder_observation` contract:

```text
observation_id
ticker / company_key
observation_type              # risk_driver, watchlist, covenant, outlook, event, etc.
claim_text
value_numeric / value_text / unit
observation_date
effective_from / effective_to
source_type                   # analyst, IR, lender, auditor, public_disclosure, etc.
source_uri / document_hash / page_or_section
author_role / contributor_id
confidence                    # controlled scale, e.g. low/medium/high
review_status                 # draft/reviewed/approved/rejected
access_class / pii_status
created_ts / updated_ts
schema_version / run_id
```

Never overwrite a conflicting observation. Store both observations, record the
conflict and expose a resolved view only after an explicit precedence or review
decision.

### Proposed end-to-end ingestion

```text
Portal / upload / approved connector / meeting capture
    -> raw document or structured observation in Bronze
    -> hash + source metadata + access/PII scan
    -> entity/period normalization and schema validation
    -> Silver research_document / stakeholder_observation
    -> human review and conflict resolution
    -> Gold fact_stakeholder_signal + approved labels
    -> PIT join with financial/market facts
    -> dashboard, ML features, RAG retrieval and audit trail
```

For documents, the RAG path is:

```text
fetch -> parse -> normalize -> chunk -> content-hash dedupe
      -> license/access/PII governance -> embedding -> PGVector/versioned store
```

The existing Phase 2 RAG code already models this shape: source metadata,
parser version, content hash, access class, governance/quarantine and embedding
version are explicit. The production connector should replace the committed
fixture fetcher without changing chunk/dedupe/write contracts.

### Source precedence and conflict rules

Use precedence per field, not one global ranking:

- audited/reviewed financial numbers: official filing/audited statement;
- market prices: exchange/licensed market source;
- business outlook/risk rationale: stakeholder/analyst observation with
  confidence and review status;
- confirmed distress outcome: approved outcome/credit event, not an analyst
  opinion;
- contradictory claims: retain both, quarantine/flag the conflict, require
  reviewer resolution for a Gold “current view”.

`created_ts` is not evidence of truth. A late-entered old observation must keep
its `observation_date`/`effective_from`; the system should order business truth
by effective time and preserve ingestion time separately.

### Label leakage rule for stakeholder information

An analyst's opinion after the distress event cannot be used as a feature for a
prediction made before that event. Define:

```text
prediction_reference_time <= feature_effective_time <= label_observation_time
```

For every training row, store the feature snapshot ID, label snapshot ID and
source publication/review time. A human research label is a target only if its
definition and observation window are explicit; otherwise it is a feature or a
weak annotation.

## 5. Migration plan for production

### Phase A — contract first

- Add a stakeholder source adapter implementing the same adapter boundary.
- Add schemas/config for documents, observations, review states and access
  classes.
- Keep raw input immutable and hash every document/row.
- Add source-specific mapping and version it in Git.

### Phase B — shadow run

- Run API and stakeholder sources together for a fixed sample of companies.
- Compare entity resolution, periods, units, duplicates, nulls and freshness.
- Do not publish stakeholder data into the production Gold view yet.
- Log source request/checkpoint/DQ rows for both paths.

### Phase C — review and backfill

- Create a review queue for low-confidence, conflicting or PII-bearing rows.
- Approve a versioned historical snapshot.
- Backfill only affected partitions; preserve old versions for rollback.
- Re-run PIT leakage and row-level provenance checks.

### Phase D — controlled cutover

- Use a source registry with `enabled`, `priority`, `effective_from` and
  `fallback` fields.
- Route only the intended domain to stakeholder signals; retain APIs for
  structured market/financial values unless a reviewed official document is the
  designated authority.
- Monitor a defined period before deprecating the old source.
- Roll back by changing the source-registry version, not by deleting data.

### Production SLOs and observability

Track at least:

- ingestion success/error/retry rate per source;
- source latency, freshness lag and checkpoint age;
- rows/documents/chunks ingested and quarantined;
- schema drift and mapping failures;
- duplicate/conflicting observation rate;
- review queue age and approval rate;
- PII/governance violations;
- Gold publication latency;
- PIT leakage count (must be zero);
- data version, source version, model/embedding version and run ID.

## 6. Phase 2 production narrative

The intended Phase 2 story is two planes:

- **Persistent product plane:** Next.js + Supabase; analyst searches companies,
  views risk/provenance and sees cached results when live AI is unavailable.
- **Disposable evidence/inference plane:** orchestration, feature/RAG services,
  agents/MCP, model serving, observability and GitOps controls.

For the meeting, say “target production architecture” unless an executed
artifact proves a component is live. The current repository has stale Phase 2
wording in some docs (EKS/k3d versus the updated execution plan's GKE decision,
and older Istio/Envoy references). The current local rules and latest plan are
the authority; do not present the stale terms as one coherent deployed stack.

## 7. Slide outline and speaker script

### Slide 1 — Why

“We need an auditable early-warning dataset for Vietnamese listed companies,
not just a notebook that calculates ratios once.”

### Slide 2 — What the platform does

Show the flow: source → Bronze → Silver → Gold → DQ/metadata → analyst/ML/RAG.

### Slide 3 — Source contract

“Collectors depend on a stable adapter interface. Today the checked-in adapter
is deterministic for CI; production replaces only the adapter and source
mapping, not the downstream contract.”

### Slide 4 — Medallion architecture

Explain Bronze replay, Silver canonicalization/dedup, Gold consumer tables.

### Slide 5 — Trust controls

Explain business keys, SCD2, timestamps, PIT, DQ severity and PostgreSQL
metadata.

### Slide 6 — Risk output

Show `obt_company_quarter_risk`, ratios, rule-based label, reason, confidence,
training eligibility and provenance. State clearly that Phase 1 is not ML.

### Slide 7 — Production source evolution

“Structured APIs remain for structured truth. Stakeholder research becomes a
governed signal/document domain with review workflow, versioning and conflict
resolution.”

### Slide 8 — AI/product extension

Show RAG ingestion, PGVector, feature/RAG tools, analyst UI and cached/offline
state. Emphasize citations and access control.

### Slide 9 — Current status and gaps

Green: local E2E, contracts, DQ, metadata, PIT. Amber: live connector,
stakeholder workflow, full production deployment, model validation and source
licensing/compliance.

### Slide 10 — Next milestones

Stakeholder schema → adapter → shadow run → review/backfill → controlled
cutover → model/AI validation.

## 8. Likely questions and answers

**Q: Why use fixtures?**  
To make contract tests deterministic and fast. The fixture is not claimed as
production data; it proves pipeline semantics without depending on an unstable
network/vendor.

**Q: Why not put stakeholder text directly into the financial table?**  
Because a narrative claim has different grain, confidence, authority and
review lifecycle. It belongs in a separate observation/document contract and is
joined into Gold as a signal with provenance.

**Q: Which source wins when two sources disagree?**  
It depends on the field. Preserve both observations, apply field-level
precedence and require review for a resolved Gold view.

**Q: Can an analyst opinion become the ML label?**  
Only after the target definition, observation window, reviewer authority and
outcome semantics are documented. Otherwise it is an input signal/weak label,
not ground truth.

**Q: How do you prevent future leakage?**  
Use `report_release_date`/business effective time as the reference boundary and
exclude features published after it. Validate that future-feature leakage is
zero.

**Q: Is the current adapter already calling live vnstock?**  
No. The current `vnstock_adapter.py` is intentionally a fixture-backed
boundary. Implementing a live adapter is a production hardening step.

**Q: Is the project production-ready today?**  
The Phase 1 data contracts and local evidence path are production-shaped; the
full production source integration, stakeholder review controls and cloud
deployment still require delivery and evidence. The honest claim is “verified
foundation and production migration design,” not “fully deployed production.”

## Unresolved questions

- Which stakeholder roles are allowed to submit, approve or override a signal?
- What exact source will be used for stakeholder capture: structured form,
  governed file drop, approved document portal, meeting transcript or all of
  them?
- Which fields are authoritative from official disclosure versus internal
  research?
- What is the formal distress outcome definition and prediction horizon?
- What retention, consent, PII and licensing policy applies to internal notes,
  transcripts and uploaded documents?
- Which Phase 2 platform decision is final for the actual deployment: the latest
  GKE plan or an older EKS/k3d evidence document?
