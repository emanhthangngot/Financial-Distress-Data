---
phase: 2
title: "Phase 2: Data model v2 and metadata unification"
status: pending
priority: P1
effort: "9-13 days"
dependencies: ["phase-01-naming-cutover.md"]
owns: ["src/transforms/", "src/metadata/", "src/quality/", "src/io/paths.py", "sql/"]
---

# Phase 2: Data model v2 and metadata unification

## Revision 2026-09-02 — schema audit applied

Sixteen findings from [`reports/research-260902-1402-schema-design-audit.md`](./reports/research-260902-1402-schema-design-audit.md)
are folded in. Four reverse a decision the 2026-09-01 revision made:

| # | Previous decision | Now | Ground |
|---|---|---|---|
| F1 | Delete `company_key` **and** `company_version_key`; `ticker` is the fact join key | Delete `company_key` only. `company_version_key` stays the `dim_company` PK and the fact join key. **`ticker` is the declared durable key — no separate durable column** (see U-2, resolved 2026-09-02) | The two keys are not the same key. `company_key = sha256(ticker)[:16]` fails all three surrogate tests; `company_version_key = sha256(f"{ticker}\|{valid_from}")[:16]` (`dim_company.py:50`) **carries version identity**. Kimball: facts join the dimension surrogate, never the natural key. Dropping it makes every fact→dim join a range join and leaves the ERD with no declarable FK — which defeats mini row 42 |
| F2 | Rename `valid_from_ts`/`valid_to_ts` → `known_from_ts`/`known_to_ts` on `dim_company` | Keep `valid_from_ts` / `valid_to_ts` / `is_current`. Record the semantic correction in ADR-017 and the data dictionary | mini rubric row 40 (2 pts) names those exact three columns. `known_from_ts` is not standard vocabulary either — SQL:2011 uses `_valid_from`/`_valid_to` for application time and `_sys_start`/`_sys_end` for system time. Renaming a graded column to a non-standard term loses the point without gaining the standard |
| F3 | `known_from` (facts), `known_from_ts` (dim), `knowledge_ts` (grain) | **`known_from_ts` everywhere.** One identifier | Three names for one axis inside one phase file, on top of three timestamp suffix conventions already live in the repo (`_ts` 21 uses, `_timestamp` 19, `_at` ~20). P2 exit re-freezes the contract, so this becomes permanent |
| F4 | `ops.data_quality_result` PK `(track, check_id)` | PK `check_id`; `track` is a `NOT NULL` column with a CHECK enum and its own index | `check_id` is already a deterministic hash of `(run_id, dataset_name, check_name)`, so it is unique alone. A 3-value leading column constrains nothing and poisons the index prefix. The current repo (`init_project_metadata.sql:18`) already does this correctly |

## Revision 2026-09-02b — three open questions closed with source evidence

U-1, U-2 and U-3 are resolved. Two of the closures reverse a recommendation made earlier the same
day, and two new defects surfaced. Evidence: `vnstock` 4.0.7 wheel source, measured Parquet writes,
measured Spark decimal promotion, raw mini-rubric CSV cells.

| # | Question | Resolution | Ground |
|---|---|---|---|
| **U-1** | vnstock money unit | **Statements arrive in VND đồng as exact multiples of 1,000đ. Prices arrive in nghìn đồng.** Money → `DECIMAL(18,0)`; prices normalized to đồng at the adapter, then `DECIMAL(18,0)`; ratios stay `DECIMAL(18,6)` | `vnstock/explorer/kbs/financial.py:572` sends `"unit": 1000  # Đơn vị ngàn đồng`; `:369` passes `unit_multiplier=1000.0`; `:259` applies `value * unit_multiplier` → output is whole đồng, granularity 1,000đ. `vnstock/explorer/kbs/quote.py:345,506` divide OHLC and match price by 1000 for stock/ETF → output is nghìn đồng |
| **U-2** | Is `company_durable_key = hash(ticker)` acceptable? | **No — do not create it.** `ticker` is the durable key | The column would be a pure function of `ticker` in the same row, i.e. `company_key` renamed. That repeats D-2 verbatim ("16 bytes replacing a 3-byte natural key"). Kimball's durable key earns its place when the natural key can change or be reused; inside this dataset (2018-2025, 300 tickers, `exclude_financial_sector: true`) it cannot. A real `entity_id` arrives with the Tier-2 registry, not as a hash placeholder now |
| **U-3** | Does mini row 40 mandate its three column names? | **Question does not need answering — keeping them is dominant** | The rubric author writes "or similar" where flexibility is intended: row 42 `(… DBeaver or similar tools)`, row 43 `(… prefix or similar)`. Row 40's `(valid_from_ts, valid_to_ts, is_current)` has no such clause. Regardless of how it resolves: keeping the names scores 2 points in both readings, renaming scores 2 in one and 0 in the other. Keep + expose standards vocabulary through `dim_company_sys` |

### New defects found while closing them

| # | Defect | Evidence | Impact |
|---|---|---|---|
| **F17** | `docs/07_data_contracts.md:92-95` declares `open`/`high`/`low`/`close` as `DOUBLE … VND`. **vnstock v4 returns nghìn đồng**, so the declared unit is wrong by 1000× | `vnstock/explorer/kbs/quote.py:345` `df[col] = df[col] / 1000` for non-derivative, non-index assets; `:506` same for match price | Every price-derived feature — market cap, return, volatility — is off by three orders of magnitude while passing every existing check |
| **F18** | mini rubric row 43 has a **second clause** this plan missed: `(- Bronze & Silver layer: `raw_`, `stg_` prefix or similar)`. Bronze and Silver tables carry no prefix at all | raw CSV cell, mini scored row 43 | 2 points at risk. The 2026-09-02 naming convention wrote "bronze/silver plural mirror source", which does not satisfy the clause |

### Measurement corrections — earlier claims in this plan were wrong

| Claim made 2026-09-02 | Measured 2026-09-02b | Effect |
|---|---|---|
| "`DECIMAL(20,2)` stores in 8 bytes vs 16 for `DECIMAL(38,2)`" | pyarrow 25.0.0, 200k rows, uncompressed: `DECIMAL(18,x)` = **9.36 B/value**, `DECIMAL(19,2)`/`(20,x)` = **10.21**, `DECIMAL(38,2)` = **16.66**. pyarrow writes **every** decimal as `FIXED_LEN_BYTE_ARRAY` with length scaled to precision — there is no INT64→FLBA step at 18 | `DECIMAL(20,2)` is 10.2 B, not 8. To reach 9.36 the precision must be ≤ 18 |
| "`DECIMAL(20,2)` is the recommendation" | Wrong on both axes: it pays 16-byte-class storage **and** carries the thinnest aggregation headroom | Corrected to `DECIMAL(18,0)` |
| "maximum precision is the safe choice" | Spark 4.2.0 measured: `SUM(DECIMAL(p,s)) → DECIMAL(p+10, s)`, capped at 38. `DECIMAL(18,0)` → `DECIMAL(28,0)`; `DECIMAL(38,2)` → `DECIMAL(38,2)` — **no promotion left** | Precision 38 is the only choice with zero aggregation headroom. Precision 18 has nine orders of magnitude |

## Revision 2026-09-10 — model semantics reconciliation (M1 … M11)

The v2 decisions of 2026-09-02 / 02b are **unchanged and binding**: `company_key` deleted,
`company_version_key` the `dim_company` PK and fact join key, `ticker` the durable key,
`valid_from_ts` / `valid_to_ts` / `is_current` verbatim, `known_from_ts` as the one knowledge-time
identifier, money `DECIMAL(18,0)`, ratios `DECIMAL(18,6)`, `raw_` / `stg_` prefixes,
`data_quality_result` PK `check_id`. **No accepted primary key is changed by this revision.** What
follows fixes semantics that revision left ambiguous or self-contradictory. Every item below is a
defect read out of the current source, not a new feature.

| # | Defect (verified in source) | Evidence | Resolution |
|---|---|---|---|
| **M1** | The OBT joins labels by `company_version_key` **first**. That key is `sha256(f"{ticker}\|{valid_from}")[:16]` — it identifies a *dimension version*, not a period, and one version stays current across many quarters. `label_by_version` therefore keeps **one label per version** and hands it to every `report_period` that version covers | `obt_company_quarter_risk.py:18-29`, `keys.py:42` | Labels join on **`(ticker, report_period, label_version)`** only; `company_version_key` is never a label join key. §Label boundary versus predictor availability |
| **M2** | The OBT drops every non-latest vintage (`if row.get("is_latest_vintage") is False: continue`), so the analyst/training table is latest-only — while its declared PK `(ticker, report_period, known_from_ts)` anticipates many vintages. The bi-temporal model dies at the last hop, which is the same class as D-3 | `obt_company_quarter_risk.py:24-25`, `sql/schema_evidence.sql:175-184` | The OBT **retains every vintage**; a separate view `gold.obt_company_quarter_risk_latest` serves analyst/DBeaver evidence. §OBT vintage retention |
| **M3** | `merge_dim_company` compares each snapshot only against the **current** row. Re-merging a batch that has already been superseded re-emits the older snapshot: `company_version_key = hash(ticker\|created_ts)` **collides with the existing row's PK**, and `previous["valid_to_ts"] = valid_from` writes `valid_to_ts < valid_from_ts` — a **negative interval** | `dim_company.py:44-70`, `keys.py:31-42` | The merge becomes **idempotent and monotonic**: out-of-order snapshots are rejected, an interval is never closed backwards, an existing version key is never re-minted. §SCD2 replay and backfill |
| **M4** | `daily_return` lags `close_price` over rows sorted by `(ticker, trading_date)` **only**. With the vintage axis a corrected close for one `trading_date` is a *second row*, so "previous close" is whichever vintage happened to sort last — a **future correction leaks into a past return**. The Spark window has the same defect (`partitionBy(ticker).orderBy(trading_date)`, no vintage tie-break, so `lag` is nondeterministic) | `fact_market_price.py:26-42`, `:57-58` | Every derived series is computed **after** as-of vintage selection collapses the vintage axis. §As-of vintage selection |
| **M5** | `feat_company_financial_4q`, `_market_30d` and `_news_30d` **aggregate nothing** — each is a per-input-row projection, so "4q" and "30d" are false names; and PK `(ticker, event_timestamp)` breaks the moment one ticker's two `report_period`s share an instant (a backfill, or a Q4 + FY drop) | `pit.py:18-81`, `sql/schema_evidence.sql:197-205` | Feature rows become **as-of snapshots**: one row per `(ticker, cutoff_ts)`, aggregating a declared window. `report_period` becomes an attribute, so `(ticker, event_timestamp)` is unique by construction — the accepted PK is kept, not changed. §Feature window semantics |
| **M6** | `statement_variant` defaults **any** unknown or missing value to `'consolidated'`; and it is part of the PK while `UNIQUE (ticker, report_period) WHERE is_latest_vintage` is *not* variant-scoped, so two variants of one period can both be flagged latest and the partial unique index fails | `fact_financial_statement.py:37-39`, `silver/core.py:41-92` | PK unchanged. A **closed enum plus a deterministic precedence rank** elects exactly one latest row per `(ticker, report_period)`; an unrecognized variant fails closed to `ops.failed_records`. §Statement variant precedence |
| **M7** | `compute_distress_labels` sets `decision_ts = row["known_from_ts"]` — the knowledge time of the very statement the rule read. The guard tests `feature_time > label_time`, so that statement passes **at equality** and is admitted as its own predictor. The guard cannot fail on the leakage it exists to catch | `compute_distress_labels.py:234,287`, `leakage_guard.py:100` | **Two boundaries, two columns**: `decision_ts` = the predictor cutoff, `label_available_ts` = when the label became computable. §Label boundary versus predictor availability |
| **M8** | Feast reads `fact_financial_statement`, `obt_company_quarter_risk` and `fact_market_price` with `timestamp_field="known_from_ts"`, **no `created_timestamp_column` at all**, from a **single `data.parquet`** object — while this plan declares the `feat_*` tables as the Feast contract carrying `event_timestamp` / `created_timestamp`, and D-15 removes the single-object layout | `feature_definitions.py:57-70,86-133`, `paths.py:13-21` | The `feat_*` tables are the Feast source of record; sources declare **both** reserved columns and read the **partitioned prefix**. §Feast source parity |
| **M9** | `date_key` means three different things: knowledge date on statements (`date_key(known_from_ts)`), trading date on prices, event date on news/alerts — while `dim_date` carries the `fiscal_year` / `fiscal_quarter` that F13 moved *off* the fact. Joining a statement's `date_key` to `dim_date` yields the **filing** quarter, not the reported one, so F13 loses the attribute it was supposed to relocate | `fact_financial_statement.py:36`, `fact_market_price.py:33`, `fact_news_sentiment.py:42`, `fact_market_alert.py:42` | `date_key` is **role-declared per table**, and every fact carrying `report_period` also carries `report_period_end_date_key`, so fiscal attributes resolve from valid time. The fiscal-calendar assumption is declared and policed. §date_key roles and the fiscal-calendar guard |
| **M10** | News and alert facts are deduplicated by **`event_id`** at runtime and asserted unique on `event_id` by the publisher and the DQ job — but the DDL declares `PRIMARY KEY (ticker, article_hash)` / `(ticker, alert_type, raised_ts)`, and **no builder emits `event_id`, `article_hash`, `published_ts` or `raised_ts`** into those tables | `fact_news_sentiment.py:26-34`, `fact_market_alert.py:26-34`, `lakehouse_publish.py:66-67`, `lakehouse_dq_job.py:105-113`, `sql/schema_evidence.sql:142-163` | The DDL adopts the **runtime grain `event_id`** plus the event-time column the builders actually emit. §Event grain reconciliation |
| **M11** | `docs/07_data_contracts.md` documents objects that exist under **neither** the current nor the target names (`raw_company`, `raw_market_price`, `stg_company`, `stg_company_quarter`, a Silver-zone `fact_company_quarter_financials`), prices as `DOUBLE … VND`, periods as `(period_year, period_quarter)`, labels as `is_distressed BOOLEAN`, and `stg_company` PK `ticker` — contradicting F6, F17, F18 and the `report_period` decision. AC-P2-23 and AC-P4-27 cite `docs/architecture/data-contracts.md`, which **does not exist** | `docs/07_data_contracts.md:31,52,75,100,123,149,279,300,320`, filesystem | An explicit **legacy → target mapping** is migrated into `docs/architecture/data-contracts.md` and the legacy file is retired in the same commit. §Legacy contract migration |

Ownership of the fixes: **P2 owns the contract, the DDL and the pure-Python reference
implementation** (including the `*_spark` transform functions that live under `src/transforms/`);
**P4 owns the Spark job wiring** in `src/jobs/` and must mirror P2's semantics, with parity asserted
(AC-P2-38); **P5 consumes** the `feat_*` snapshot contract and owns the Feast registry, TTL and
materialization (P5 §Feast source parity, §TTL policy).

## Overview

Fix the data model. Source-only; runs against the local Docker Compose lakehouse, no GKE capacity
required. **Resident cost: 0.**

This phase exists because the previous plan froze a model with 18 verified defects (`plan.md`
§Data Model Findings, D-1 … D-18) plus 16 schema-audit findings (F1 … F16). Four are load-bearing:

- **D-3 + D-4:** Silver keeps only the latest `created_ts` per `(ticker, report_period)`, so every
  restatement is destroyed. The PIT leakage guard compares timestamp *columns*, never values, so it
  passes on restated data **by construction** and cannot detect the project's largest leakage source.
  The guard is a correct guard installed downstream of the transformation that removes the
  information it needs.
- **D-1 (amended by F1):** `company_key` is written to every fact row and read by nothing.
  `company_version_key` is written and also never joined on — but that is a **usage** defect, not a
  design defect. The fix is to make joins use it, not to delete it.
- **D-16 + D-17:** the graded ERD asserts six foreign keys the pipeline never writes, its generator
  leaves all fact tables empty, and the submitted bundle contradicts itself about whether those keys
  exist.
- **F5 + F6 + F7:** Bronze carries a PRIMARY KEY that forbids the append-only duplicate behaviour the
  project is graded on; `silver.stg_companies` carries a PRIMARY KEY that makes SCD2 structurally unable
  to emit a second version; and **no** Gold fact or feature table declares any key at all.

**Exit of this phase re-freezes the contracts.** After P2, G-3 ("data contracts immutable") applies
again.

## Requirements

- Functional:
  - Facts carry a **knowledge-time** axis (`known_from_ts`) that Silver is forbidden to overwrite.
    **One identifier for this axis project-wide** (F3).
  - `fact_financial_statement` grain = `(ticker, report_period, statement_variant, known_from_ts)`,
    declared as a **real PRIMARY KEY** in the graded ERD, not only as a DQ assertion (F7).
  - `is_latest_vintage` is a **derived** boolean, enforced by a partial unique index, and elected by
    a **deterministic precedence** across `statement_variant` so that exactly one row per
    `(ticker, report_period)` carries it (M6).
  - `company_key` is deleted from all fact and feature tables. **`company_version_key` is retained**
    as the `dim_company` PK and the fact join key. **`ticker` is the declared durable key** — no
    separate `company_durable_key` column is created (U-2) — and stays a natural-key attribute (F1).
  - `dim_company` keeps `valid_from_ts` / `valid_to_ts` / `is_current` **verbatim** (mini row 40) and
    adds `company_name` + `listing_date` to the SCD2 change set (F2).
  - Bronze declares **no** PRIMARY KEY and no UNIQUE (F5). `silver.stg_companies` PK = `(ticker, created_ts)` (F6).
  - `dim_date` is enriched with fiscal attributes and **populated for every `date_key` any fact
    emits**; `fiscal_year` / `fiscal_quarter` move off the fact (F12, F13).
  - The graded ERD covers **all 12 Gold datasets**, not 9 (F8).
  - Gold naming follows the declared convention: `fact_distress_label` (not `distress_labels`),
    `distress_holdout` (no `_v1` — version lives in the Iceberg tag), `ml.distress_label` (not
    `label_table`) (F9).
  - One Postgres database, two schemas (`ops`, `ml`), `TIMESTAMPTZ` everywhere, `_ts` suffix
    everywhere except the two reserved Feast names, four real foreign keys, one
    `data_quality_result` with PK `check_id` (F3, F4).
  - Money is **`DECIMAL(18,0)`**; ratios and rates are `DECIMAL(18,6)`. Prices are **normalized to
    đồng at the adapter** and stored as `DECIMAL(18,0)` like every other money column. The scale
    choice is recorded with its reason, because Iceberg permits precision widening but **prohibits
    scale change** (F11, U-1).
  - Every money-bearing contract carries a **`source_unit`** field, and the adapter asserts the
    normalization it applied. The unit is a property of *which adapter answered*, not of "vnstock"
    (U-1d) — `configs/collector_config.yaml` lists four fallback sources whose units are unverified.
  - Bronze tables are prefixed **`raw_`** and Silver tables **`stg_`** (F18, mini row 43).
  - `feat_*` tables carry **both** Feast reserved columns: `event_timestamp = known_from_ts` (a
    design decision, not a fallback — Feast's default tie-break selects the newest
    `created_timestamp`, which is precisely the leakage this model exists to prevent, F14) and
    `created_timestamp` = the ingest wall clock. Feast sources point at the **`feat_*` partitioned
    prefixes**, not at facts and not at a single `data.parquet` (M8).
  - Gold is partitioned; `src/io/paths.py` no longer resolves to a single `data.parquet`.
  - `scripts/build_schema_evidence.py` loads **real** Gold output, can fail, and asserts a NULL-rate
    ceiling on every nullable FK column (F16).
  - `feat_*` rows are **as-of snapshots**: one row per `(ticker, cutoff_ts)` aggregating a declared
    window, with the window's observation count and a completeness flag on the row (M5).
  - The label carries **two distinct timestamps** — `decision_ts` (the predictor cutoff) and
    `label_available_ts` (when the label became computable) — and is joined on
    `(ticker, report_period, label_version)`, never on `company_version_key` (M1, M7).
  - `gold.obt_company_quarter_risk` retains **every vintage**; `gold.obt_company_quarter_risk_latest`
    is the latest-vintage view (M2).
  - `merge_dim_company` is **idempotent under replay and safe under backfill**: no duplicate
    `company_version_key`, no interval where `valid_to_ts < valid_from_ts` (M3).
  - Every fact declares the **role** its `date_key` plays, and every fact carrying `report_period`
    also carries `report_period_end_date_key` (M9). The fiscal-calendar assumption is stated and
    checked, not implied.
  - `fact_market_alert` and `fact_news_sentiment` declare the **`event_id`** grain the builders,
    publisher and DQ job already use (M10).
  - `docs/architecture/data-contracts.md` exists, carries the legacy → target mapping, and
    `docs/07_data_contracts.md` is retired in the same commit (M11).
- Non-functional: contract version bumped to `v2` in `ops.schema_version_registry` — the mechanism
  already exists and has never been used for its purpose; `v1` rows are retained, not deleted.
  The naming convention is written down **and linted**, not merely described (F10).

## Architecture

### Identity — two key layers, not zero and not three (F1, U-2)

A surrogate key exists to decouple facts from natural-key volatility, to be a compact join key, and
to carry version identity. The repo has two candidates and they score differently:

| Key | Source | Content | Decouples? | Compact? | Version identity? | Verdict |
|---|---|---|---|---|---|---|
| `company_key` | `keys.py:14-17` | `sha256(upper(ticker))[:16]` | No — pure function of `ticker` | No — 16 B for a 3 B key | No | **delete** |
| `company_version_key` | `dim_company.py:50` | `sha256(f"{ticker}\|{valid_from}")[:16]` | Partly | No | **Yes** | **retain as PK + fact FK** |

The 2026-09-01 revision applied the `company_key` critique to both. That was wrong:
`company_version_key` is a valid SCD2 version surrogate, and Kimball practice is unambiguous — the
fact table joins the dimension's **surrogate**, and the natural key stays in the dimension as a
descriptive attribute. Dropping it would have:

- turned every fact→dim join into a range join on `(ticker, known_from_ts BETWEEN valid_from_ts AND
  COALESCE(valid_to_ts,'infinity'))` — a predicate Spark cannot hash- or broadcast-join, at the
  10-50M-row scale P4 targets;
- allowed a >1-row fan-out whenever two SCD2 windows overlap, with no constraint to stop it;
- left the graded ERD with **no declarable foreign key** from fact to dimension, which is what
  mini row 42 ("Relationship between dim & fact tables — export via DBeaver") is scored on. DBeaver
  renders relationships from constraints, not from DQ configuration.

```
Tier 0  delete `company_key` from every table (fact, feature, dim)
        retain `company_version_key` as dim_company PK and the fact join key
        declare `ticker` the DURABLE key — used for GROUP BY across versions.
             NO `company_durable_key` column is created (U-2, resolved 2026-09-02b):
             it would be a pure function of `ticker` in the same row, i.e.
             `company_key` under a new name, repeating D-2 exactly.
             `ticker` is 3 bytes, human-readable, already on every row.
        add UNIQUE (ticker) WHERE is_current so the natural key is enforced
Tier 1  add `exchange` + listing validity window to dim_company so an
        HNX→HOSE transfer is representable instead of silently overwritten
Tier 2  DEFERRED — a durable entity_id sourced from reality requires a curated
        registry of (ticker, exchange, valid_from, valid_to, entity_id). vnstock
        exposes no delisting endpoint (verified 2026-09-01), so the mapping cannot
        be sourced. Until then `ticker` fills the durable-key slot and inherits
        ticker-reuse ambiguity — recorded as a known, unhandled limitation in
        ADR-017. When the registry lands, `entity_id` is added THEN; a hash
        placeholder now would buy nothing and cost 10-50M rows of dead bytes.
        Accepted cost: queries that group by `ticker` today must switch to
        `entity_id` at that migration.
```

### Time — bi-temporal facts, single-axis dimension

```
valid time      = report_period            (which period the numbers describe)  — already present
knowledge time  = known_from_ts            (when THIS VERSION became knowable)  — NEW
                  ONE identifier, project-wide (F3)

dim_company     stays single-axis; the axis IS knowledge time.
                Column names stay valid_from_ts / valid_to_ts / is_current
                because mini rubric row 40 names them (F2). The semantic
                correction — that this axis is system time, not application
                time — is recorded in ADR-017 and the data dictionary, and
                exposed under standard names by the view `dim_company_sys`
                (sys_start / sys_end) for anyone who wants SQL:2011 vocabulary.
                Intervals are closed-open [from, to) per SQL:2011.
```

Deciding case: a company files Q2-2023 in Aug-2023 showing equity 500bn; auditors force a
restatement in Mar-2024 to 120bn; the firm enters distress in Q4-2024. A model trained on the 120bn
figure stamped as available in 2023 has been handed the answer. One time axis cannot encode two
independent facts.

### SCD2 replay and backfill (M3) — idempotent, monotonic, never a negative interval

`merge_dim_company` today reads only the **current** row per ticker, so it cannot see that a
snapshot it is about to apply belongs *before* an interval that is already closed. Two concrete
failures, both reachable from a re-run:

```
batch 1: {AAA, name="Alpha",  created_ts=t1}   → version hash(AAA|t1), [t1, ∞), is_current
batch 2: {AAA, name="Alpha2", created_ts=t2}   → hash(AAA|t1) closed at t2; hash(AAA|t2) current
replay batch 1 (same rows, t1 < t2):
        tracked fields differ from the current row  → "changed"
        emits company_version_key = hash(AAA|t1)    → DUPLICATE PRIMARY KEY
        sets  hash(AAA|t2).valid_to_ts = t1         → valid_to_ts < valid_from_ts (NEGATIVE)
        and marks the OLDEST row is_current         → uq_dim_company_current now names the wrong row
```

Rules the rewritten merge obeys, in this order:

```
1  WATERMARK   a snapshot whose created_ts <= the ticker's max(valid_from_ts) is NOT a new version.
               If its tracked attributes match the version in force at that instant → no-op (this
               is what makes replay idempotent). If they differ → ops.failed_records with reason
               `late_scd2_snapshot`; history is never rewritten in place.
2  IDENTITY    company_version_key is minted only for a valid_from_ts that does not already exist
               for that ticker. A collision is an error, never an overwrite.
3  INTERVAL    closing an interval requires new.valid_from_ts > previous.valid_from_ts; the writer
               asserts valid_to_ts > valid_from_ts on every row it closes.
4  CURRENCY    exactly one is_current row per ticker, and it is the one with max(valid_from_ts)
               (uq_dim_company_current, F1).
5  FLAP        an A → B → A attribute sequence produces THREE versions with three distinct
               valid_from_ts values; it never reuses the first version's key.
```

Backfilling genuinely older history (a corrected listing date for a period already closed) is a
**rebuild**, not a merge: the ticker's history is recomputed from the full ordered snapshot set and
rewritten as one transaction, so intervals stay contiguous and keys stay stable. That path is
explicit and asserted (AC-P2-27), not a side effect of re-running the daily merge.

### As-of vintage selection (M4) — one read semantics for every fact

```
as_of_ts        the knowledge instant a read is taken at (a training cutoff, a request, or the
                arriving row's own known_from_ts when a stored derived column is computed)
as-of vintage   per business key: the row with the GREATEST known_from_ts <= as_of_ts
latest vintage  the as-of vintage at as_of_ts = now  ⇒ is_latest_vintage

RULE  every derived series — returns, deltas, rolling windows, ratios across periods — is computed
      AFTER as-of selection has collapsed the vintage axis to one row per business key.
      Lagging across vintages is forbidden; a stored derived column is computed at the arriving
      row's own known_from_ts, so each vintage carries the value that was knowable when it landed.
```

`fact_market_price.daily_return` is the load-bearing case. Under the rule, the vintage row for
trading day *D* takes its previous close from the as-of vintage of the previous **trading** day at
`as_of_ts = ` that row's own `known_from_ts` — so a correction that arrives later cannot change a
return that was already published, and the corrected vintage gets its own return row. The Spark
window gains the same total order (`partitionBy(ticker, trading_date)` for selection, then
`orderBy(trading_date)` over the selected rows), removing the nondeterministic `lag` at
`fact_market_price.py:57-58`. Regression case AC-P2-28 pins the numbers.

### Grain, the vintage flag, and real constraints (F7)

```
fact_financial_statement
  grain: (ticker, report_period, statement_variant, known_from_ts)
         statement_variant ∈ {consolidated, separate} × {audited, unaudited}
                            — the contract already has a nullable `statement_type`
                              (schema_registry.py:127) that is currently unused in the key
  derived: is_latest_vintage BOOLEAN

  DECLARED, not merely asserted:
    PRIMARY KEY (ticker, report_period, statement_variant, known_from_ts)
    UNIQUE INDEX (ticker, report_period) WHERE is_latest_vintage
```

A DQ check runs after the write, outside the transaction, and can be skipped. The previous revision
expressed the grain only as a DQ assertion. It is now a constraint in the graded ERD (Postgres /
DuckDB) **and** a DQ check for the Iceberg tables, where constraints cannot be enforced. That
duality is what makes `build_schema_evidence.py` falsifiable under O-5.

`statement_variant` is part of the grain for `fact_financial_statement` **only**. `fact_market_price`
and `fact_market_alert` have no variant concept; their grain is declared per table below.

### Statement variant precedence (M6) — deterministic, PK unchanged

The accepted PK keeps `statement_variant`, and the accepted partial unique index is *not*
variant-scoped. Both stay. The conflict between them is resolved by making the **election** of
`is_latest_vintage` total, not by widening the index or shrinking the PK.

```
CLOSED ENUM (four tokens = the accepted {consolidated, separate} × {audited, unaudited})
  statement_variant     variant_rank    meaning
  consolidated_audited       1          group accounts, auditor signed  ← preferred
  consolidated_unaudited     2          group accounts, management figures
  separate_audited           3          parent-only accounts, auditor signed
  separate_unaudited         4          parent-only, management figures

SILVER dedup key = (ticker, report_period, statement_variant) × known_from_ts
  → all four variants and all vintages survive; the accepted PK is exactly this tuple

ELECTION of is_latest_vintage, per (ticker, report_period) — a total order, no ties possible:
  ROW_NUMBER() OVER (
    PARTITION BY ticker, report_period
    ORDER BY known_from_ts DESC,     -- newest knowledge first
             variant_rank ASC,       -- audited group accounts beat management parent accounts
             created_ts DESC,        -- newest ingest of the same variant+vintage
             statement_variant ASC   -- final lexical tie-break; guarantees determinism
  ) = 1
  → exactly one row per (ticker, report_period) ⇒ uq_ffs_latest holds with the PK untouched
```

`variant_rank` is **derived from the enum, not stored** — a stored rank would be a second source of
truth for a four-value lookup. Precedence rationale: audited figures supersede management figures
for the same period because the audit is the later, authoritative statement of the same facts, and
consolidated accounts are the basis of the distress rules (group leverage, not parent-only).

Fail-closed replacement for the `or "consolidated"` default (`fact_financial_statement.py:37-39`):
the legacy nullable `statement_type` (`schema_registry.py:127`) maps through an **explicit table in
the v2 contract**; a value that is absent, empty, or unmapped routes the row to
`ops.failed_records` with `failure_reason = 'unknown_statement_variant'`. It is never defaulted,
because defaulting a *separate* statement to *consolidated* silently doubles group leverage.

### Date and fiscal period — stop denormalising onto the fact (F12, F13)

`gold.dim_date` currently has two columns (`schema_evidence.sql:58-61`): `date_key`, `calendar_date`.
A date dimension with no date attributes is why `fiscal_year` and `fiscal_quarter` ended up
denormalised onto the fact — they had nowhere else to live. That is D-9's root cause, and deriving
`report_period` from them with a consistency check treats the symptom.

```
dim_date       date_key INTEGER PK  (YYYYMMDD smart integer key — keys.py:20-27, keep)
               calendar_date, fiscal_year, fiscal_quarter, month,
               quarter_end_date, is_quarter_end, day_of_week, is_trading_day
               generated for 2015-01-01 … 2030-12-31

fact_*         carry date_key (+ report_period as a degenerate dimension used for
               partitioning). fiscal_year / fiscal_quarter are DROPPED from facts.
```

Consequence: D-9's cross-field consistency check becomes unnecessary, because the redundancy is gone
rather than policed. `dim_date` generation is now an explicit P2 deliverable — the previous revision
declared a foreign key into it (`schema_evidence.sql:64`) and an AC demanding zero orphans, without
owning the table that has to be populated.

### `date_key` roles and the fiscal-calendar guard (M9)

`date_key` is a **role-playing** foreign key, and the role differs per fact. That is legitimate
Kimball practice, but only when the role is declared — today it is not, which is why a statement's
`date_key` (its *filing* date, `fact_financial_statement.py:36`) resolves to the filing quarter's
fiscal attributes and F13's relocation of `fiscal_year` / `fiscal_quarter` silently loses the
reported period.

| Table | `date_key` role | Source expression | Also declares |
|---|---|---|---|
| `fact_financial_statement` | **knowledge date** — when this vintage became knowable | `known_from_ts::date` | `report_period_end_date_key` (valid time) |
| `obt_company_quarter_risk` | **knowledge date** of the statement vintage the row is built from | `known_from_ts::date` | `report_period_end_date_key` |
| `fact_market_price` | **observation date** — the trading day | `trading_date` | — (no report period exists) |
| `fact_market_alert` | **event date** | `event_timestamp::date` | — |
| `fact_news_sentiment` | **event date** — publication/arrival | `event_timestamp::date` | — |
| `fact_distress_label` | **report-period end date** — the label's own grain is valid time | `report_period_end_ts::date` | — |

So: knowledge-date roles answer "when could this be known", valid-time roles answer "which period
does this describe", and **fiscal attributes are only ever read through a valid-time role**. A
consumer that needs the fiscal quarter of a statement joins `report_period_end_date_key`, never
`date_key`. The naming stays `date_key` (it is already in the graded ERD and in AC-P2-15 / AC-P2-20)
with the role recorded in the data dictionary and in the column comment.

**Fiscal-calendar assumption, declared and policed.** `dim_date` is generated with
`fiscal_year = year(calendar_date)` and `fiscal_quarter = quarter(calendar_date)` — i.e. the fiscal
year equals the calendar year. Grounds: the free tier returns statement periods as calendar labels
only (`2026-Q2`, `2025-Q4`; phase-04 §Free-tier data ceiling) and exposes **no fiscal-year-end
field**, and `exclude_financial_sector: true` removes the sector most likely to diverge. The
assumption is therefore not inferrable from the source and is instead:

```
1  ASSERTED at generation   dim_date rows satisfy fiscal_year = year(calendar_date)
                            and fiscal_quarter = quarter(calendar_date); the generator fails
                            if a future fiscal-calendar table is introduced without updating it
2  CHECKED per row          a report_period whose derived period end is not a calendar quarter end
                            routes to ops.failed_records, reason `fiscal_calendar_mismatch`
3  RECORDED                 ADR-017 states the assumption, its evidence, and that a per-issuer
                            fiscal-year-end registry would replace it (same deferral shape as the
                            Tier-2 entity registry, U-2)
```

A non-calendar fiscal year is therefore a *rejected row with a named reason*, never a silently
mislabelled quarter.

### Feast contract — the default is the adversary (F14)

Verified behaviour: `event_timestamp` is the **inclusive upper bound** of Feast's point-in-time join;
`created_timestamp_column` is a tie-breaker and Feast selects the row with the **highest**
`created_timestamp` for a given `event_timestamp`. Feast's documented stance on restatements is that
its built-in "last known good" logic prioritises the most recent information, and that seeing the
world as it was known at the time requires explicit version management or custom filtering.

So mapping `known_from_ts` onto `created_timestamp` would make Feast always pick the newest vintage —
the exact leakage this phase exists to prevent.

```
feat_*  event_timestamp   := known_from_ts     ← knowledge time IS Feast's join axis
        created_timestamp := ingest wall clock ← tie-break for retries of one ingest only
        report_period     := feature attribute, NOT a time axis
        CHECK (event_timestamp = known_from_ts)
```

This is a design decision recorded in ADR-017, not a risk response. `phase-05` inherits it.

The existing `feat_company_unified` CHECK (`schema_evidence.sql:102`)
`feature_event_timestamp <= event_timestamp` is replaced: with a knowledge axis the correct invariant
compares the feature's knowledge time to the **label decision boundary**, which lives on
`fact_distress_label.decision_ts`.

### Feast source parity (M8) — the contract is the `feat_*` table, not the fact

The live registry (`feature_definitions.py:57-70,86-133`) contradicts the paragraph above in three
ways at once, and each one defeats a different part of the design:

| Live | Consequence | Target |
|---|---|---|
| `FileSource(path=<fact/obt single data.parquet>)` for `fact_financial_statement`, `obt_company_quarter_risk`, `fact_market_price` | Feast joins the **raw fact**, so it sees every vintage as an independent row and the `feat_*` CHECK never applies; and the path is the single-object layout D-15 deletes | sources point at the **`feat_*` partitioned prefix** (`feat_company_financial_4q`, `_market_30d`, `_news_30d`, `_unified`) |
| `timestamp_field="known_from_ts"` | works, but the graded column and the CHECK are on `event_timestamp`; two names for Feast's join axis reopens F3 | `timestamp_field="event_timestamp"`, with the ERD CHECK `event_timestamp = known_from_ts` keeping the two provably equal |
| **no `created_timestamp_column`** | Feast has no declared tie-break, so retry duplicates of one ingest are resolved arbitrarily — and the DDL's `created_timestamp NOT NULL` column is written by nobody (`pit.py` emits `created_ts`) | `created_timestamp_column="created_timestamp"`; the builders emit **both** reserved names, and `created_ts` is not a Feast name |

P2 owns the two reserved columns and the CHECK; **P5 owns the registry, the FileSource wiring and
the TTL table**, and P5 §TTL policy carries the FeatureView ↔ `feat_*` table ↔ TTL mapping.

### Label boundary versus predictor availability (M1, M7)

A distress label produced by a rule over a statement becomes *knowable* exactly when that statement
is filed. Setting the guard's boundary to that instant (`decision_ts = known_from_ts`,
`compute_distress_labels.py:234,287`) therefore admits the label's own source row as a predictor —
the guard compares `feature_time > label_time` (`leakage_guard.py:100`) and equality passes. The two
concepts must be two columns:

```
report_period_end_ts   valid-time close of the reported period      (derived via dim_date)
decision_ts            PREDICTOR CUTOFF := report_period_end_ts     ← the guard's boundary
label_available_ts     max(known_from_ts) over the statement vintages the rule actually read
                       — when the label became computable; a publish/schedule gate, never a
                       predictor boundary

INVARIANTS
  feature.known_from_ts <= label.decision_ts            enforced by the guard (LeakageError)
  label.decision_ts     <= label.label_available_ts     enforced by a CHECK + DQ rule
  the statement that PRODUCED the label is filed after the period end, so its known_from_ts
  is strictly greater than decision_ts and it can never be its own predictor
```

**Why period end is the conservative default.** The tightest correct cutoff would be "the instant
before the label's source filing", which requires a per-issuer filing calendar the source does not
expose (phase-04 §Free-tier data ceiling). Period end is the latest instant that is provably free of
the label's own information for every issuer, and it is derivable from `report_period` alone. It is
deliberately conservative: it also excludes same-period market and news features published between
period end and the filing. Any relaxation is a modelling decision that belongs to P7/P11 with its
own evidence, and it must move `decision_ts` explicitly in the contract — not by widening a
comparison operator.

**Join key.** The label is joined on `(ticker, report_period, label_version)`. `company_version_key`
is not period-scoped (`keys.py:42`) and is therefore never a label join key (M1); it remains the
fact→dimension join key. `label_version` is pinned per training run so a re-labelled cohort cannot
silently change a frozen dataset.

### Feature window semantics and missing history (M5)

```
cutoff_ts   a knowledge instant at which a snapshot is taken. The snapshot set per ticker =
            the distinct known_from_ts values of that ticker's own inputs (statement filings for
            financial_4q, trading days for market_30d, article arrivals for news_30d) plus any
            explicit training cutoff requested by P7/P11.
GRAIN       one row per (ticker, cutoff_ts)
            event_timestamp = known_from_ts = cutoff_ts   ⇒ PK (ticker, event_timestamp) is unique
            report_period / trading_date / article identity are ATTRIBUTES, not key parts
INPUTS      each window reads the AS-OF VINTAGE at cutoff_ts (§As-of vintage selection), so a
            later correction cannot alter a snapshot that already exists
```

| Feature table | Window | Aggregates | Minimum history | Below the minimum |
|---|---|---|---|---|
| `feat_company_financial_4q` | the 4 most recent distinct `report_period`s whose as-of vintage is known at `cutoff_ts` | per ratio: latest value, 4-period mean, QoQ delta, YoY delta | **4 distinct periods** | every aggregate `NULL`; `window_period_count` recorded; `feature_completeness = 'insufficient'`; `training_eligible = false` |
| `feat_company_market_30d` | trailing **30 calendar days** ending at `cutoff_ts`, as-of vintage per `trading_date` | mean and last close, realized volatility, cumulative return, max drawdown, mean volume | **18 trading days** (≈ 60 % of the ~22 expected in 30 calendar days) | same rule; `window_trading_day_count` recorded |
| `feat_company_news_30d` | trailing **30 calendar days** by `known_from_ts` | article count, mean and minimum sentiment, risk-keyword count | **none** — zero articles is a real observation, not missing data | `news_article_count = 0`; score aggregates `NULL`; `feature_completeness = 'empty_window'` |
| `feat_company_unified` | the join of the three above at one `cutoff_ts` | pass-through of each leg | every leg present | the missing leg's columns `NULL`; `feature_completeness` is the **worst** of the legs |

Conservative defaults, stated once and applied everywhere:

```
NULL, never zero-fill        a missing ratio is unknown, not zero (0.0 debt_to_asset reads as healthy)
No forward-fill past TTL     a stale value never answers a query beyond its table's TTL (P5 §TTL)
No imputation in the feature layer   imputation is a model decision; it belongs to P7/P11 where it
                                     is versioned with the model, not silently baked into Gold
Partial windows are labelled, not averaged   window_*_count is on every row, so a consumer can
                                     reject a thin window instead of trusting a mean of two points
```

### OBT vintage retention (M2)

```
gold.obt_company_quarter_risk          ALL vintages. PK (ticker, report_period, known_from_ts) —
                                       unchanged, and now actually multi-row as it was declared to be
gold.obt_company_quarter_risk_latest   VIEW: WHERE is_latest_vintage  ← analyst + DBeaver evidence
                                       (mini row 42 renders relationships from the base tables)
```

The training consumer reads the base table with an explicit `as_of_ts`; the human consumer reads the
view. Dropping non-latest rows at build time (`obt_company_quarter_risk.py:24-25`) is exactly D-3
one layer later: the row that proves the restatement existed is the row being deleted.

### Event grain reconciliation (M10)

The runtime already agrees with itself and only the DDL disagrees: the builders key on `event_id`
(`fact_news_sentiment.py:31-34`, `fact_market_alert.py:31-34`), the publisher asserts uniqueness on
`event_id` (`lakehouse_publish.py:66-67`), the DQ job checks `event_id` uniqueness
(`lakehouse_dq_job.py:105-113`), and `event_id` is a stable content hash of the event payload
(`streaming/events.py:17-20`). The DDL's `article_hash` / `(alert_type, raised_ts)` columns are
produced by nothing.

```
fact_market_alert    PRIMARY KEY (event_id)        + UNIQUE (ticker, alert_type, event_timestamp)
fact_news_sentiment  PRIMARY KEY (event_id)        + INDEX  (ticker, event_timestamp)
```

`event_id` is the grain because it is the deduplication key the stream contract already guarantees
(`flink_contract.py:138-142`, `problem_factory.py:110-133` injects colliding `event_id`s precisely to
be deduplicated). The secondary UNIQUE on alerts keeps the business rule "one alert of a type per
ticker per event instant" declarable, which is what the old PK was reaching for.

### Legacy contract migration (M11) — truthful, not a fresh document

`docs/07_data_contracts.md` is not merely out of date; it describes a *different* model. Every row
below is a real divergence, and the mapping is migrated into `docs/architecture/data-contracts.md`
so no reader is left believing the old names:

| Legacy object / field (`docs/07_data_contracts.md`) | Target | Divergence |
|---|---|---|
| `raw_company` :31 | `bronze.raw_companies` | singular; F18 prefix matches only by coincidence |
| `raw_financial_statement` :52 | `bronze.raw_financial_statements` | singular |
| `raw_market_price` :75 | `bronze.raw_market_prices_daily` | singular **and** drops `_daily` |
| `stg_company` :100, PK `ticker` | `silver.stg_companies`, PK `(ticker, created_ts)` | legacy PK makes SCD2 structurally impossible (F6) |
| `stg_company_quarter` :123 | `silver.stg_financial_statements` | legacy pivots long→wide in Silver and has no vintage axis |
| `fact_company_quarter_financials` :149 (in the **Silver** zone) | `gold.fact_financial_statement` | a fact documented in Silver; zone violation |
| `(period_year, period_quarter)` :130,156,320 | `report_period` | the accepted single period identifier (D-9) |
| `open/high/low/close DOUBLE … VND` :92-95 | `DECIMAL(18,0)` đồng | wrong by 1000× (F17) |
| `total_assets … DOUBLE … VND` :141-147 | `DECIMAL(18,0)` đồng | float money; unit unqualified (U-1) |
| Source "TCBS market price API" :80 | vnstock v4 (KBS / VCI) | TCBS REST paths 404 (phase-04 §Source-data reality) |
| `fact_market_alert` PK `(ticker, alert_date, alert_type)` :279 | PK `event_id` | no `alert_date` is produced (M10) |
| `fact_news_sentiment` PK `(ticker, news_date)` :300, `article_count` | PK `event_id`; counts live on `feat_company_news_30d` | grain is the event, not the day (M10) |
| `fact_distress_label` `is_distressed BOOLEAN` :331 | `distress_label SMALLINT` + `decision_ts` + `label_available_ts` | a boolean cannot carry the two boundaries (M7) |
| every legacy table: `Partition columns \| none` | partitioned Gold | contradicts AC-P2-12 |
| no knowledge-time column anywhere | `known_from_ts` on every fact | the legacy doc predates the bi-temporal model |

Retirement is part of the same commit: `docs/architecture/data-contracts.md` is created **with** this
mapping as its §Migration section, and `docs/07_data_contracts.md` is **deleted** — not left as a
stale second source of truth, and not silently overwritten as though it had always said this.
`docs/architecture/feature-contracts.md` already exists (P5 owns its TTL content), so P2 adds only
the `feat_*` column contract to it and does not claim to create it.

### Money and numeric types (F11, U-1) — resolved with measurement, not judgement

Iceberg permits **precision widening** (`decimal(9,2)` → `decimal(18,2)`) but **prohibits scale
change** (`decimal(9,2)` → `decimal(9,4)`), because scale alters the Parquet/Avro byte layout and
would corrupt historical reads. So precision is the escape hatch and scale is a one-way door.

**The source unit is now known.** `vnstock/explorer/kbs/financial.py:572` requests the SAS finance
endpoint with `"unit": 1000  # Đơn vị ngàn đồng`; `:369` passes `unit_multiplier=1000.0`; `:259`
applies `value = float(value) * unit_multiplier`. Statement values therefore arrive in **whole VND
đồng at 1,000đ granularity** — a fractional đồng cannot exist in the source. Scale 0 is not a guess.

Prices go the **other way**: `vnstock/explorer/kbs/quote.py:345` divides OHLC by 1000 for stock and
ETF assets and `:506` does the same for match price, so vnstock returns prices in **nghìn đồng**
with a rounded fractional part. This plan normalizes them back to đồng at the adapter so the
lakehouse has exactly one money unit (see F17).

**Measured storage cost** (pyarrow 25.0.0, 200 000 rows, uncompressed):

| Type | Parquet physical | Bytes/value |
|---|---|---|
| `DECIMAL(18,0)` / `DECIMAL(18,2)` | `FIXED_LEN_BYTE_ARRAY` | **9.36** |
| `DECIMAL(19,2)` / `DECIMAL(20,0)` / `DECIMAL(20,2)` | `FIXED_LEN_BYTE_ARRAY` | **10.21** |
| `DECIMAL(38,2)` | `FIXED_LEN_BYTE_ARRAY` | **16.66** |

pyarrow writes **every** decimal as `FIXED_LEN_BYTE_ARRAY` with length scaled to precision. There is
no INT64→FLBA step at precision 18, so the earlier claim in this plan that `DECIMAL(20,2)` costs
8 bytes was wrong: it costs 10.2.

**Measured aggregation behaviour** (Spark 4.2.0): `SUM(DECIMAL(p,s)) → DECIMAL(p+10, s)`, capped at
38.

| Column type | `SUM` result type | Aggregation headroom |
|---|---|---|
| `DECIMAL(18,0)` | `DECIMAL(28,0)` | ~1e28 |
| `DECIMAL(20,2)` | `DECIMAL(30,2)` | ~1e28 |
| `DECIMAL(38,2)` | `DECIMAL(38,2)` | **none — already at the cap** |

So maximum precision is the only choice that cannot promote on aggregation. Choosing 38 to be "safe"
removes the safety margin it was chosen for.

| Use | Type | Range | Reason |
|---|---|---|---|
| Money — statements and prices | **`DECIMAL(18,0)`** | ±1e18 đồng ≈ 90× Vietnam's annual GDP | Source granularity is 1,000đ, so there is no sub-đồng information to store. Cheapest measured width (9.36 B). `SUM` promotes to `DECIMAL(28,0)`. Precision widening to 38 remains available if ever needed |
| Ratio / rate | `DECIMAL(18,6)` | — | Six decimal places for `debt_to_asset`, growth rates, FX |
| `sentiment_score` | `DECIMAL(18,6)` | — | Same class as ratios |

Per-row headroom check: `exclude_financial_sector: true` in `configs/collector_config.yaml` removes
banks, so the largest single `total_assets` is a non-financial balance sheet — orders of magnitude
below 1e18. An unqualified `SUM(total_assets)` over every ticker, quarter and vintage promotes to
`DECIMAL(28,0)` and cannot overflow.

**The unit is a property of the adapter, not of "vnstock" (U-1d).**
`configs/collector_config.yaml` declares `fallback_sources: [cafe_f, vietstock, tcbs, ssi]`. Their
units are **not verified** — grepping `vnstock/explorer/vci/financial.py` found no multiplier, but
absence of a grep hit is weak evidence of absence. Therefore every money-bearing contract carries a
`source_unit` field, and each adapter asserts the normalization it applied before the row reaches
Bronze. A row whose `source_unit` is unrecognized goes to `ops.failed_records`; it is never
normalized by guess.

AC-P2-11 (`assets = liabilities + equity` holds exactly, no arbitrary tolerance) is satisfied by any
DECIMAL and is exact under scale 0. It never required precision 38.

### Naming convention — declared and linted (F3, F9, F10, F18)

The repo currently runs three timestamp suffix conventions simultaneously (measured 2026-09-02 over
`sql/*.sql` + `schema_registry.py`): `_ts` 21 uses, `_timestamp` 19 uses, `_at` ~20 uses — with `ops`
(`ops`) on `_at` and `ml` (`ml`) on `_ts`. mini row 43 is scored on naming
convention, and its **full** text has two clauses, not one:

```
Naming convention
(- Gold layer: `dim_`, `fact_`, `obt_`, `feat_`, `raw`, prefix or similar)
(- Bronze & Silver layer: `raw_`, `stg_` prefix or similar)
```

The 2026-09-02 revision only served the Gold clause and declared "bronze/silver plural, mirrors the
source" — which does not satisfy the second clause (F18). Bronze and Silver carry **no prefix at all**
today. Two readings exist: strict (tables need `raw_`/`stg_`) and loose (the zone is already encoded
in the object path, which is "or similar"). This plan takes the **strict** reading: six renames
inside a phase that is already rewriting `sql/` and `src/io/paths.py`, against 2 points at risk.

`ml` is already the better half on every axis P2 touches: `TIMESTAMPTZ`, `_ts` suffix, a real
FK (`rag_chunk.document_hash → rag_document`, `init_ml_metadata.sql:55`), and composite natural PKs.
The migration direction is therefore **pull `ops` up to `ml`'s standard**, not meet in the middle.

```
ZONE / SCHEMA
  bronze              `raw_` prefix, PLURAL feed name             raw_companies, raw_financial_statements
  silver              `stg_` prefix, PLURAL feed name             stg_companies, stg_financial_statements
  gold                SINGULAR + prefix                           dim_ fact_ obt_ feat_
  ops                 operational metadata                      pipeline_run_log, data_quality_result
  ml                  ML metadata                               distress_label, feast_registry_revision

TABLE
  dim_<entity>        dimension, singular                       dim_company, dim_date
  fact_<event>        fact, singular                            fact_financial_statement
  obt_<subject>       one big table                             obt_company_quarter_risk
  feat_<entity>_<win> feature table                             feat_company_market_30d
  NO version in a table name — versions live in Iceberg tags/branches

COLUMN
  <x>_key             surrogate key                             company_version_key, date_key
  ticker              natural key AND durable key — GROUP BY axis; never a fact join key
  <x>_ts              TIMESTAMPTZ                               created_ts, known_from_ts, valid_from_ts
  <x>_date            DATE                                      trading_date, listing_date
  is_<x>              BOOLEAN                                   is_current, is_latest_vintage
  event_timestamp     RESERVED — Feast contract, never renamed
  created_timestamp   RESERVED — Feast tie-break, never renamed
  NO `_at` suffix — the 8 `ops` columns migrate to `_ts` in step 6
  NO "table" inside a table or column name

TYPE
  money               DECIMAL(18,0)   scale 0: source granularity is 1,000đ (U-1). Irreversible
  ratio / rate        DECIMAL(18,6)
  timestamp           TIMESTAMPTZ     migrate via AT TIME ZONE 'UTC', never a bare ALTER TYPE
  date surrogate      INTEGER YYYYMMDD

CONSTRAINT
  bronze              NO PK, NO UNIQUE (append-only). Grain documented, not enforced
  silver              PK includes the snapshot / vintage axis
  gold fact           PK = the full grain; partial unique index for is_latest_vintage
  FK                  declared only on tables that carry real rows; every nullable FK
                      column carries a NULL-rate ceiling in the DQ gate
```

Renames this convention forces:

| Old | New | Driver |
|---|---|---|
| `gold.distress_labels` | `gold.fact_distress_label` | mini row 43 — no prefix, and plural among singular peers |
| `gold.distress_holdout_v1` | `gold.distress_holdout` | version belongs in the Iceberg tag `holdout-v1`, which P4 already creates. One version source, not two |
| `ml.label_table` | `ml.distress_label` | "table" inside a table name |
| `ops.*_at` (8 columns) | `ops.*_ts` | one suffix, project-wide |
| `bronze.companies` | `bronze.raw_companies` | mini row 43 clause 2 (F18) |
| `bronze.financial_statements` | `bronze.raw_financial_statements` | mini row 43 clause 2 (F18) |
| `bronze.market_prices_daily` | `bronze.raw_market_prices_daily` | mini row 43 clause 2 (F18) |
| `silver.companies` | `silver.stg_companies` | mini row 43 clause 2 (F18) |
| `silver.financial_statements` | `silver.stg_financial_statements` | mini row 43 clause 2 (F18) |
| `silver.market_prices_daily` | `silver.stg_market_prices_daily` | mini row 43 clause 2 (F18) |

`src/io/paths.py` dataset names change for all eight renamed datasets. Every one is greppable in the
rubric matrix before renaming — same mechanism §Risk already applies to `company_key`.

### Metadata unification

```
one database, two schemas — not one flat schema

ops.pipeline_run_log
ops.data_quality_result   ← merged from both schemas; PK (check_id);
                            track TEXT NOT NULL CHECK (track IN ('mini','ml','llm'))
                            + INDEX (track, checked_ts)            ← F4
ops.failed_records
ops.source_request_log
ops.dataset_freshness
ops.schema_version_registry   + partial unique index on (dataset_name) WHERE is_current
ops.backfill_request
ops.collector_checkpoint

ml.distress_label             ← renamed from ml.label_table (F9)
ml.feast_registry_revision
ml.stream_feature_checkpoint
ml.rag_document / rag_chunk / rag_quarantine / rag_ingestion_run

FOUR real foreign keys (all on populated tables):
  ops.data_quality_result.run_id  → ops.pipeline_run_log.run_id
  ops.failed_records.run_id       → ops.pipeline_run_log.run_id
  ops.source_request_log.run_id   → ops.pipeline_run_log.run_id
  ml.rag_chunk.document_hash      → ml.rag_document.document_hash
```

These four are the honest replacement for the six fictional ones in `sql/schema_evidence.sql`. All
three `run_id` columns stay **nullable** — Postgres does not enforce a foreign key when the
referencing column is NULL (MATCH SIMPLE), so ad-hoc scripts degrade gracefully instead of failing.

**But that is exactly why "zero orphans" alone is a vacuous assertion** (F16): a table whose `run_id`
is entirely NULL passes it trivially, which is the same defect class as D-16. So the DQ gate monitors
the **NULL rate** with a ceiling, and `build_schema_evidence.py` carries a negative test that seeds a
dangling `run_id` and must fail.

`TIMESTAMPTZ` migration uses explicit `AT TIME ZONE 'UTC'`, never a bare `ALTER TYPE` — a bare cast
reinterprets naive values in the session timezone, which is the exact 7-hour bug being fixed (D-13).
The `_at` → `_ts` rename rides the same migration.

### Target DDL (replaces `sql/schema_evidence.sql`)

```sql
-- BRONZE: append-only. No PK, no UNIQUE (F5). `raw_` prefix (F18).
CREATE TABLE bronze.raw_companies (
    ticker          VARCHAR NOT NULL,
    company_name    VARCHAR,
    exchange        VARCHAR,
    source_name     VARCHAR NOT NULL,          -- which adapter answered (U-1d)
    source_unit     VARCHAR NOT NULL,          -- unit as delivered, before normalization
    created_ts      TIMESTAMPTZ NOT NULL,
    ingest_batch_id VARCHAR NOT NULL
    -- grain, documented not enforced: (ticker, created_ts, ingest_batch_id)
);

CREATE TABLE bronze.raw_financial_statements (
    ticker           VARCHAR NOT NULL,
    report_period    VARCHAR NOT NULL,
    total_assets     DECIMAL(18,0),             -- already normalized to đồng (U-1)
    total_liabilities DECIMAL(18,0),
    total_equity     DECIMAL(18,0),
    source_name      VARCHAR NOT NULL,
    source_unit      VARCHAR NOT NULL,          -- e.g. 'VND', 'VND_THOUSAND' as delivered
    known_from_ts    TIMESTAMPTZ NOT NULL,
    created_ts       TIMESTAMPTZ NOT NULL,
    ingest_batch_id  VARCHAR NOT NULL
);

CREATE TABLE bronze.raw_market_prices_daily (
    ticker          VARCHAR NOT NULL,
    trading_date    DATE NOT NULL,
    close_price     DECIMAL(18,0),              -- đồng: adapter multiplies vnstock's nghìn đồng by 1000 (F17)
    source_name     VARCHAR NOT NULL,
    source_unit     VARCHAR NOT NULL,
    known_from_ts   TIMESTAMPTZ NOT NULL,
    created_ts      TIMESTAMPTZ NOT NULL,
    ingest_batch_id VARCHAR NOT NULL
);

-- SILVER: retains snapshot history so SCD2 has something to compare (F6). `stg_` prefix (F18).
CREATE TABLE silver.stg_companies (
    ticker        VARCHAR NOT NULL,
    company_name  VARCHAR NOT NULL,
    exchange      VARCHAR NOT NULL,
    industry      VARCHAR,
    sector        VARCHAR,
    delisted_flag BOOLEAN NOT NULL DEFAULT FALSE,
    created_ts    TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, created_ts)
);
-- silver.stg_financial_statements / stg_market_prices_daily follow the same pattern:
-- `stg_` prefix, PK includes the vintage axis, money in DECIMAL(18,0).

-- GOLD dimension: two key layers (F1, U-2); rubric-named SCD2 columns (F2).
CREATE TABLE gold.dim_company (
    company_version_key VARCHAR PRIMARY KEY,   -- surrogate; the fact join key
    ticker              VARCHAR NOT NULL,
    company_name        VARCHAR NOT NULL,
    exchange            VARCHAR NOT NULL,
    industry            VARCHAR,
    sector              VARCHAR,
    listing_date        DATE,
    delisted_flag       BOOLEAN NOT NULL DEFAULT FALSE,
    valid_from_ts       TIMESTAMPTZ NOT NULL,
    valid_to_ts         TIMESTAMPTZ,
    is_current          BOOLEAN NOT NULL
);
CREATE UNIQUE INDEX uq_dim_company_current ON gold.dim_company (ticker) WHERE is_current;
CREATE INDEX ix_dim_company_ticker ON gold.dim_company (ticker);  -- durable-key GROUP BY axis (U-2)

-- GOLD date dimension: enriched and populated (F12, F13).
CREATE TABLE gold.dim_date (
    date_key         INTEGER PRIMARY KEY,
    calendar_date    DATE UNIQUE NOT NULL,
    fiscal_year      SMALLINT NOT NULL,
    fiscal_quarter   SMALLINT NOT NULL,
    month            SMALLINT NOT NULL,
    quarter_end_date DATE NOT NULL,
    is_quarter_end   BOOLEAN NOT NULL,
    day_of_week      SMALLINT NOT NULL,
    is_trading_day   BOOLEAN NOT NULL
);

-- GOLD facts: real PKs (F7); fiscal attributes gone (F12); money DECIMAL(18,0) (F11, U-1).
CREATE TABLE gold.fact_financial_statement (
    company_version_key VARCHAR NOT NULL REFERENCES gold.dim_company(company_version_key),
    date_key            INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
                        -- ROLE: knowledge date = known_from_ts::date (M9)
    report_period_end_date_key INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
                        -- ROLE: valid time. Fiscal attributes are read ONLY through this key (M9)
    ticker              VARCHAR NOT NULL,
    report_period       VARCHAR NOT NULL,
    statement_variant   VARCHAR NOT NULL,       -- closed enum, 4 tokens (M6)
    known_from_ts       TIMESTAMPTZ NOT NULL,
    is_latest_vintage   BOOLEAN NOT NULL,       -- elected by the total order in §Statement variant precedence
    total_assets        DECIMAL(18,0),
    total_liabilities   DECIMAL(18,0),
    total_equity        DECIMAL(18,0),
    source_name         VARCHAR NOT NULL,       -- which adapter answered (U-1d)
    source_unit         VARCHAR NOT NULL,       -- unit as delivered, before normalization (U-1d)
    created_ts          TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, report_period, statement_variant, known_from_ts),
    CHECK (statement_variant IN ('consolidated_audited','consolidated_unaudited',
                                 'separate_audited','separate_unaudited'))
);
CREATE UNIQUE INDEX uq_ffs_latest ON gold.fact_financial_statement (ticker, report_period)
    WHERE is_latest_vintage;                    -- one row per period ACROSS variants (M6)

CREATE TABLE gold.fact_market_price (
    company_version_key VARCHAR NOT NULL REFERENCES gold.dim_company(company_version_key),
    date_key            INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
                        -- ROLE: observation date = trading_date (M9)
    ticker              VARCHAR NOT NULL,
    trading_date        DATE NOT NULL,
    close_price         DECIMAL(18,0),         -- đồng, normalized at the adapter (F17)
    daily_return        DECIMAL(18,6),         -- computed at THIS row's known_from_ts against the
                                               -- as-of vintage of the previous trading day (M4)
    source_name         VARCHAR NOT NULL,
    source_unit         VARCHAR NOT NULL,
    known_from_ts       TIMESTAMPTZ NOT NULL,
    created_ts          TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, trading_date, known_from_ts)
);

-- Event grain adopted from the runtime, publisher and DQ job (M10).
CREATE TABLE gold.fact_market_alert (           -- was missing from the ERD (F8)
    event_id            VARCHAR PRIMARY KEY,    -- stable content hash (streaming/events.py:17-20)
    company_version_key VARCHAR NOT NULL REFERENCES gold.dim_company(company_version_key),
    date_key            INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
                        -- ROLE: event date = event_timestamp::date (M9)
    ticker              VARCHAR NOT NULL,
    alert_type          VARCHAR NOT NULL,
    event_timestamp     TIMESTAMPTZ NOT NULL,   -- when the alert fired (the builders' own column)
    known_from_ts       TIMESTAMPTZ NOT NULL,
    created_ts          TIMESTAMPTZ NOT NULL,
    UNIQUE (ticker, alert_type, event_timestamp)  -- one alert of a type per ticker per instant
);

CREATE TABLE gold.fact_news_sentiment (         -- was missing from the ERD (F8)
    event_id            VARCHAR PRIMARY KEY,
    company_version_key VARCHAR NOT NULL REFERENCES gold.dim_company(company_version_key),
    date_key            INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
                        -- ROLE: event date = event_timestamp::date (M9)
    ticker              VARCHAR NOT NULL,
    sentiment_score     DECIMAL(18,6),
    risk_keyword_flag   BOOLEAN NOT NULL,
    severity_score      DECIMAL(18,6),
    event_timestamp     TIMESTAMPTZ NOT NULL,   -- publication / arrival instant
    known_from_ts       TIMESTAMPTZ NOT NULL,
    created_ts          TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_fns_ticker_event ON gold.fact_news_sentiment (ticker, event_timestamp);

CREATE TABLE gold.fact_distress_label (         -- renamed from distress_labels (F8, F9)
    ticker             VARCHAR NOT NULL,
    report_period      VARCHAR NOT NULL,
    label_version      VARCHAR NOT NULL,
    distress_label     SMALLINT NOT NULL,
    date_key           INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
                       -- ROLE: report-period end date (M9)
    report_period_end_ts TIMESTAMPTZ NOT NULL,  -- valid-time close of the reported period
    decision_ts        TIMESTAMPTZ NOT NULL,    -- PREDICTOR CUTOFF := report_period_end_ts (M7)
    label_available_ts TIMESTAMPTZ NOT NULL,    -- when the label became computable (M7)
    label_source       VARCHAR NOT NULL,        -- rule id / provenance
    training_eligible  BOOLEAN NOT NULL,
    created_ts         TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, report_period, label_version),
    CHECK (decision_ts = report_period_end_ts),
    CHECK (decision_ts <= label_available_ts)
);

-- OBT retains EVERY vintage (M2); the latest-only projection is a view, not a filter at write time.
CREATE TABLE gold.obt_company_quarter_risk (
    company_version_key VARCHAR NOT NULL REFERENCES gold.dim_company(company_version_key),
    date_key            INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
                        -- ROLE: knowledge date of the statement vintage this row is built from (M9)
    report_period_end_date_key INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
    ticker              VARCHAR NOT NULL,
    report_period       VARCHAR NOT NULL,
    known_from_ts       TIMESTAMPTZ NOT NULL,
    is_latest_vintage   BOOLEAN NOT NULL,
    statement_variant   VARCHAR NOT NULL,
    debt_to_asset       DECIMAL(18,6),
    current_ratio       DECIMAL(18,6),
    roa                 DECIMAL(18,6),
    label_version       VARCHAR,                -- label joined on (ticker, report_period, label_version)
    distress_label      SMALLINT,               -- NULL when no label exists for this period (M1)
    label_decision_ts   TIMESTAMPTZ,            -- carried through so the guard has both sides
    label_available_ts  TIMESTAMPTZ,
    created_ts          TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, report_period, known_from_ts)
);
CREATE VIEW gold.obt_company_quarter_risk_latest AS
    SELECT * FROM gold.obt_company_quarter_risk WHERE is_latest_vintage;

-- GOLD features: as-of snapshots, one row per (ticker, cutoff_ts) (M5); Feast axis is knowledge
-- time (F14); both reserved Feast names are declared and written (M8).
CREATE TABLE gold.feat_company_financial_4q (
    ticker              VARCHAR NOT NULL,
    event_timestamp     TIMESTAMPTZ NOT NULL,   -- RESERVED Feast join axis = known_from_ts = cutoff_ts
    created_timestamp   TIMESTAMPTZ NOT NULL,   -- RESERVED Feast tie-break = ingest wall clock
    known_from_ts       TIMESTAMPTZ NOT NULL,
    as_of_report_period VARCHAR NOT NULL,       -- newest period inside the window; ATTRIBUTE, not key
    window_period_count SMALLINT NOT NULL,      -- periods actually aggregated (M5)
    feature_completeness VARCHAR NOT NULL,      -- 'complete' | 'insufficient'
    debt_to_asset_latest  DECIMAL(18,6),
    debt_to_asset_mean_4q DECIMAL(18,6),
    debt_to_asset_qoq     DECIMAL(18,6),
    debt_to_asset_yoy     DECIMAL(18,6),
    -- current_ratio / roa / roe / ebit_interest_coverage / z_score carry the same four aggregates
    PRIMARY KEY (ticker, event_timestamp),
    CHECK (event_timestamp = known_from_ts),
    CHECK (feature_completeness IN ('complete','insufficient'))
);

CREATE TABLE gold.feat_company_market_30d (
    ticker              VARCHAR NOT NULL,
    event_timestamp     TIMESTAMPTZ NOT NULL,
    created_timestamp   TIMESTAMPTZ NOT NULL,
    known_from_ts       TIMESTAMPTZ NOT NULL,
    window_start_date   DATE NOT NULL,          -- cutoff - 30 calendar days
    window_end_date     DATE NOT NULL,          -- cutoff date; trading_date is NOT a key part (M5)
    window_trading_day_count SMALLINT NOT NULL,
    feature_completeness VARCHAR NOT NULL,
    close_last          DECIMAL(18,0),
    close_mean_30d      DECIMAL(18,0),
    return_cum_30d      DECIMAL(18,6),
    volatility_30d      DECIMAL(18,6),
    max_drawdown_30d    DECIMAL(18,6),
    volume_mean_30d     DECIMAL(18,0),
    PRIMARY KEY (ticker, event_timestamp),
    CHECK (event_timestamp = known_from_ts)
);

CREATE TABLE gold.feat_company_news_30d (
    ticker              VARCHAR NOT NULL,
    event_timestamp     TIMESTAMPTZ NOT NULL,
    created_timestamp   TIMESTAMPTZ NOT NULL,
    known_from_ts       TIMESTAMPTZ NOT NULL,
    window_start_ts     TIMESTAMPTZ NOT NULL,
    news_article_count  INTEGER NOT NULL,       -- 0 is an observation, not missing data (M5)
    feature_completeness VARCHAR NOT NULL,      -- 'complete' | 'empty_window'
    sentiment_mean_30d  DECIMAL(18,6),          -- NULL when the window is empty — never 0
    sentiment_min_30d   DECIMAL(18,6),
    risk_keyword_count  INTEGER NOT NULL,
    PRIMARY KEY (ticker, event_timestamp),      -- article identity is NOT a key part (M5)
    CHECK (event_timestamp = known_from_ts)
);

CREATE TABLE gold.feat_company_unified (
    ticker              VARCHAR NOT NULL,
    event_timestamp     TIMESTAMPTZ NOT NULL,
    created_timestamp   TIMESTAMPTZ NOT NULL,
    known_from_ts       TIMESTAMPTZ NOT NULL,
    as_of_report_period VARCHAR,                -- attribute of the financial leg
    feature_completeness VARCHAR NOT NULL,      -- worst of the three legs (M5)
    -- pass-through columns of feat_company_financial_4q / _market_30d / _news_30d
    PRIMARY KEY (ticker, event_timestamp),
    CHECK (event_timestamp = known_from_ts)
);
```

Iceberg partitioning: `month(known_from_ts)` for statements, `day(trading_date)` for prices. Two
verified constraints drive this — a table's footprint should reach roughly 1 TB before partitioning
buys much, and over-partitioning is the most common Iceberg mistake. At the 5-20 GB target of
AC-P4-8, **month** is right for statements and daily partitioning there would be wrong. Iceberg
supports partition evolution, so `month` → `day` stays available without a rewrite.

## Related Code Files

- Modify: `src/transforms/keys.py` — delete `stable_company_key`'s use as `company_key`; **retain**
  the version-key derivation used by `dim_company`; add `durable_company_key`; keep `date_key`
- Modify: `src/transforms/gold/dim_company.py` — **keep** `valid_from_ts`/`valid_to_ts`/`is_current`;
  add `company_name`, `listing_date` to the tracked set; **keep** `company_version_key`; drop
  `company_key`; **do not** emit a durable-key column — `ticker` fills that slot (U-2)
- **Move and enrich**: `build_dim_date` already exists in `src/transforms/gold/dim_company.py:86-106`
  and emits `quarter` / `year` / `is_weekend` — **not** the graded `fiscal_year`, `fiscal_quarter`,
  `quarter_end_date`, `is_quarter_end`, `is_trading_day`. Move it to
  `src/transforms/gold/dim_date.py`, generate 2015-01-01…2030-12-31 with the fiscal attributes,
  assert the calendar-fiscal identity (M9), and cover every `date_key` any fact emits (F12, F13).
  This is a move plus enrichment, not a green-field create
- Modify: `src/transforms/gold/fact_financial_statement.py` — drop `company_key`; **keep and populate
  `company_version_key` by joining `dim_company` on `(ticker, known_from_ts)`**; add `known_from_ts`
  and `statement_variant`; drop `fiscal_year`/`fiscal_quarter`; **delete the
  `f"{fiscal_year}-01-01"` fallback and raise instead** (D-6)
- Modify: `src/transforms/gold/fact_market_price.py` — same key treatment; **as-of vintage selection
  before the lag** so `daily_return` cannot read a future correction (M4); the Spark window gains the
  same total order, removing the nondeterministic `lag` at `:57-58`
- Modify: `src/transforms/gold/fact_market_alert.py`, `fact_news_sentiment.py` — keep the existing
  `event_id` dedup (it is the declared grain, M10); emit `event_timestamp` as the event-time column
  and stop implying `article_hash` / `raised_ts` / `published_ts`, which nothing produces
- Modify: `src/transforms/gold/obt_company_quarter_risk.py` — **delete `label_by_version`**; join
  labels on `(ticker, report_period, label_version)` (M1); **stop dropping non-latest vintages**
  (M2) and carry `is_latest_vintage`, `label_decision_ts`, `label_available_ts`; the latest-only
  projection moves to the `gold.obt_company_quarter_risk_latest` view
- Modify: `src/transforms/silver/core.py`, `silver/spark.py` — dedup on the key **including**
  vintage; emit `is_latest_vintage`; `silver.stg_companies` retains snapshot history keyed
  `(ticker, created_ts)`; `_created_timestamp` **raises** instead of returning `datetime.min` (D-5)
- Modify: `src/transforms/features/pit.py` — `_parse_timestamp` raises; the PIT join filters to a
  knowledge-time cutoff; **`build_feat_company_financial_4q` / `_market_30d` / `_news_30d` become
  real as-of window aggregations** with one row per `(ticker, cutoff_ts)`, `window_*_count` and
  `feature_completeness` (M5); the builders emit **both** `event_timestamp` and `created_timestamp`
  (M8), not `created_ts`
- Modify: `src/transforms/gold/dim_company.py` — `merge_dim_company` becomes idempotent and
  monotonic: watermark check, no re-minted `company_version_key`, no interval closed backwards, one
  `is_current` per ticker; out-of-order snapshots route to `ops.failed_records`
  (`late_scd2_snapshot`), and full-history rebuild is a separate explicit path (M3)
- Modify: `src/ml/leakage_guard.py` — compare `feature.known_from_ts` against
  `fact_distress_label.decision_ts`; raise on a missing timestamp instead of skipping the row; the
  alias list stops accepting `created_ts` as a feature axis (`leakage_guard.py:67-74`), because an
  ingest wall clock is not a knowledge time
- Modify: `src/transforms/compute_distress_labels.py` — `decision_ts` is the **report-period end**,
  not the statement's `known_from_ts` (`:234,287`); add `label_available_ts`, `report_period_end_ts`
  and `report_period` to the label row (M7)
- Modify: `src/ml/label_pipeline.py` — the projected label row and its upsert key move from
  `(ticker, event_timestamp, label_version)` to `(ticker, report_period, label_version)` so a label
  cannot lose its period (`:29-30,59-70`, M1). **Shared-file note:** `src/ml/` is not in this
  phase's `owns` list; this file and `leakage_guard.py` are P2 contract changes executed with the
  same serialization rule the plan applies to `pyproject.toml` (see §Requested dependency changes)
- Modify: `src/metadata/schema_registry.py` — v2 contracts; `report_period` as the single period
  identifier with `fiscal_year`/`fiscal_quarter` sourced from `dim_date`; `DECIMAL(18,0)` money /
  `DECIMAL(18,6)` ratio field types; a `source_unit` field on every money-bearing contract;
  `known_from_ts` naming
- Modify: `src/metadata/metadata_writer.py` — deterministic `check_id` = hash of
  `(run_id, dataset_name, check_name)`; PK `check_id`; `track` column; `ON CONFLICT DO UPDATE` (D-11)
- Modify: `src/io/paths.py` — partitioned layout; delete `dataset_object_key`'s single-file form
  (D-15); rename `distress_labels` → `fact_distress_label`, `distress_holdout_v1` → `distress_holdout`
- Modify: `src/quality/dq_checks.py`, `dq_runner.py`, `configs/dq_rules.yaml` — latest-vintage
  uniqueness, balance-sheet identity under `DECIMAL`, **NULL-rate ceiling per nullable FK column**;
  constrain `status`/`severity` to enums
- Rewrite: `sql/init_ops.sql`, `sql/init_ml.sql`, `sql/schema_evidence.sql` (all 12 Gold datasets)
- Rewrite: `scripts/build_schema_evidence.py` — load real Gold Parquet; assert zero orphans,
  `row_count > 0`, NULL-rate ceilings, the `feat_company_unified` knowledge-time CHECK on real rows,
  and grain uniqueness
- Create: `sql/migrations/002_data_model_v2.sql`
- Create: `sql/views/dim_company_sys.sql` — SQL:2011 alias view (`sys_start`/`sys_end`)
- Create: `docs/architecture/data-model.md` §Naming Convention — the block above, verbatim
- **Already exists and is already wired**: `scripts/lint_naming_convention.py` implements the gold
  prefix/singular rules, the `raw_`/`stg_` clause, the version-token ban, the `ops` `_at` ban and the
  two reserved Feast names (`:9-15,109-155`), and runs as the `naming-convention` gate in
  `scripts/run_lakehouse_quality_gates.py:34`. F10/F18 therefore need **no new script** — only the
  renames themselves, plus re-running the existing gate. Nothing in this phase may claim to create it
- Create: `docs/architecture/data-contracts.md` — the `feat_*` / fact column contract plus the
  §Migration mapping from `docs/07_data_contracts.md` (M11); **delete** the legacy file in the same
  commit. `docs/architecture/feature-contracts.md` already exists and is P5-owned; P2 adds only the
  column contract to it
- Create: `sql/views/obt_company_quarter_risk_latest.sql` — the latest-vintage view (M2)
- Create: `tests/test_bitemporal_contract.py`, `tests/test_restatement_leakage.py`,
  `tests/test_naming_convention.py`, `tests/test_dim_date_coverage.py`
- Restore: `tests/test_schema_evidence.py` — currently deleted; only the `.pyc` survives
- Create: `tests/test_scd2_replay.py`, `tests/test_obt_label_join.py`,
  `tests/test_as_of_return.py`, `tests/test_feature_window.py` — one regression per repaired defect
  (AC-P2-26 … AC-P2-31); each must fail against today's code before the fix

## Implementation Steps

1. **Write the failing tests first** (1 d) — `tests/test_restatement_leakage.py` builds a fixture
   with an original and a restated Q2 vintage, and asserts the leakage guard **raises**. It must
   fail against today's code. This test is the phase's definition of done.
2. **Contract v2** (1-2 d) — the money unit is already settled from the vnstock source
   (§Money and numeric types): statements arrive in whole đồng at 1,000đ granularity, prices in
   nghìn đồng. Write new `SchemaContract` entries with `field_types`, **`DECIMAL(18,0)` money**,
   `DECIMAL(18,6)` ratios, a **`source_unit`** field on every money-bearing contract,
   `known_from_ts`, `statement_variant`; seed `v2` into `ops.schema_version_registry` alongside `v1`.
   Confirming against one live payload is a P4 step (AC-P4-25), not a P2 blocker.
3. **Silver: vintage-preserving dedup and a safe SCD2 merge** (2 d) — dedup key gains the vintage
   axis and `statement_variant`; `is_latest_vintage` is elected by the total order in §Statement
   variant precedence; an unrecognized variant routes to `ops.failed_records`;
   `silver.stg_companies` keyed `(ticker, created_ts)` so SCD2 has history to read;
   `_created_timestamp` raises on unparseable input; `merge_dim_company` gains the watermark,
   identity, interval, currency and flap rules (M3). Verify Bronze replay is still idempotent, that
   two vintages of one quarter both survive to Silver, and that re-merging an already-superseded
   snapshot changes nothing.
4. **Gold: keys, roles, grain, partitioning** (3 d) — delete `company_key`; retain and **populate**
   `company_version_key` on every fact; **no durable-key column** (U-2); move and enrich `dim_date`
   with the asserted calendar-fiscal identity; drop `fiscal_year`/`fiscal_quarter` from facts and
   add `report_period_end_date_key` wherever `report_period` exists, with each `date_key` role
   recorded in the column comment and the data dictionary (M9); adopt the `event_id` grain on
   alerts and news (M10); compute `daily_return` **after** as-of vintage selection (M4); keep the
   SCD2 column names and expand the tracked set; remove the `date_key` fiscal-year fallback;
   partition Gold by `month(known_from_ts)` (statements) and `day(trading_date)` (prices).
4b. **OBT and label boundaries** (1-2 d) — OBT retains every vintage and gains the latest-only
   view; labels join on `(ticker, report_period, label_version)`; `decision_ts` becomes the
   report-period end and `label_available_ts` is added, with both CHECKs declared (M1, M2, M7).
4c. **Real feature windows** (2 d) — the three `feat_*` builders become as-of window aggregations
   with one row per `(ticker, cutoff_ts)`, `window_*_count`, `feature_completeness` and the
   conservative missing-history defaults; both reserved Feast names are written (M5, M8).
5. **PIT and leakage guard** (1-2 d) — the PIT join takes a knowledge-time cutoff; the guard
   compares `feature.known_from_ts` to `fact_distress_label.decision_ts` (now the period end, so
   the label's own source filing is excluded rather than admitted at equality) and stops treating
   `created_ts` as a feature axis; both raise on missing timestamps. The step-1 test must now pass,
   and must fail again if the vintage filter or the boundary separation is removed.
6. **Metadata unification and the naming cutover** (1-2 d) — one database, two schemas,
   `TIMESTAMPTZ` via explicit `AT TIME ZONE 'UTC'`, the 8 `ops` `_at` → `_ts` renames in the same
   migration, merged `data_quality_result` with PK `check_id` + `track` CHECK enum + `(track,
   checked_ts)` index, four foreign keys, deterministic `check_id`, partial unique index on
   `is_current`, `ml.label_table` → `ml.distress_label`.
7. **Naming convention: write it, then run the lint that already exists** (0.5 d) — the
   §Naming Convention block into `docs/architecture/data-model.md`; apply the eight renames; run the
   existing `naming-convention` gate (`scripts/run_lakehouse_quality_gates.py:34` →
   `scripts/lint_naming_convention.py`). Extend the lint only if a rule it does not already cover is
   needed; do not re-create it.
8. **Falsifiable schema evidence** (1 d) — rewrite `build_schema_evidence.py` against real Gold
   output covering **all 12** Gold datasets; restore `tests/test_schema_evidence.py`; prove it fails
   when a fact row's `company_version_key` is absent from `dim_company`, when a `date_key` is absent
   from `dim_date`, and when a nullable FK column exceeds its NULL-rate ceiling.
9. **Migration and regression** (1 d) — `sql/migrations/002_data_model_v2.sql` as one transaction;
   run `.venv/bin/python scripts/run_lakehouse_quality_gates.py` and the phase's regression tests;
   re-freeze the contracts.

## Success Criteria

- [ ] AC-P2-1: Data engineer → seeds an original and a restated vintage of one `(ticker,
      report_period)` → **both rows survive to Silver**; `is_latest_vintage` is true for exactly one
- [ ] AC-P2-2: `src/ml/leakage_guard.py` → runs against the restatement fixture without a
      knowledge-time filter → **raises `LeakageError`**; with the filter → passes
- [ ] AC-P2-3 **(F1, U-2)**: Engineer → greps `src/transforms/` for `company_key` and
      `durable_key` → **zero matches**; **every fact builder populates `company_version_key`**;
      `docs/architecture/data-model.md` declares `company_version_key` the fact join key and
      `ticker` both the natural key and the durable key
- [ ] AC-P2-4: DQ runner → checks `UNIQUE (ticker, report_period) WHERE is_latest_vintage` →
      passes on the multi-vintage fixture; the same rule exists as a partial unique index in the ERD
- [ ] AC-P2-5: `pit.py` and `silver/core.py` → receive an unparseable timestamp → **raise**; neither
      returns `datetime.min`
- [ ] AC-P2-6: Fact builder → receives a statement with null `report_release_date` and null
      `event_timestamp` → **raises**; no `fiscal_year-01-01` row is produced
- [ ] AC-P2-7 **(F4)**: DBA → inspects Postgres → one database, schemas `ops` and `ml`, every
      timestamp column `TIMESTAMPTZ` and `_ts`-suffixed, exactly four foreign keys, one
      `data_quality_result` with **PK `check_id`** and `track` as a CHECK-constrained column
- [ ] AC-P2-8: Metadata writer → logs the same DQ result twice for one `run_id` → one row, not two
      (deterministic `check_id` + `ON CONFLICT DO UPDATE`)
- [ ] AC-P2-9 **(F16)**: `scripts/build_schema_evidence.py` → runs against real Gold output → every
      declared FK resolves with zero orphans, every table reports `row_count > 0`, and **every
      nullable FK column is below its NULL-rate ceiling (≤ 5%)**
- [ ] AC-P2-10: Engineer → deletes one `dim_company` row and re-runs the schema-evidence script →
      **it fails** (proves the assertion is live, not vacuous)
- [ ] AC-P2-11: Analyst → sums `total_assets` across all companies under `DECIMAL(18,0)` →
      `assets = liabilities + equity` holds exactly; the DQ check needs no arbitrary tolerance
- [ ] AC-P2-12: Engineer → lists Gold objects → partitioned prefixes, not one `data.parquet` per dataset
- [ ] AC-P2-13: Engineer → runs `.venv/bin/python scripts/run_lakehouse_quality_gates.py` plus the
      phase's regression tests → both pass, zero skips. (The gate script is
      `run_lakehouse_quality_gates.py`; `scripts/run_quality_gates.py` does not exist)
- [ ] AC-P2-14 **(F2, mini 40)**: Reviewer → inspects `gold.dim_company` → columns
      `valid_from_ts`, `valid_to_ts`, `is_current` exist **under those exact names**; the SCD2 change
      set includes `company_name` and `listing_date`; `dim_company_sys` exposes `sys_start`/`sys_end`
- [ ] AC-P2-15 **(F7, mini 42)**: DBA → exports the ERD from the graded schema → **every** Gold fact,
      OBT and feature table declares a PRIMARY KEY, and every fact declares a resolvable FK to
      `dim_company` and `dim_date`
- [ ] AC-P2-16 **(F5)**: Bronze writer → receives the same business key twice → **both rows persist**;
      `bronze.*` declares no PRIMARY KEY and no UNIQUE constraint
- [ ] AC-P2-17 **(F6)**: Data engineer → lands two `silver.stg_companies` snapshots for one ticker with
      different `created_ts` → **both persist**, and `merge_dim_company` emits a second SCD2 version
- [ ] AC-P2-18 **(F8, mini 39)**: Reviewer → counts Gold tables in `sql/schema_evidence.sql` →
      **12**, matching `src/io/paths.py`; `fact_market_alert`, `fact_news_sentiment` and
      `fact_distress_label` are present
- [ ] AC-P2-19 **(F9, F10, mini 43)**: Engineer → runs the existing `naming-convention` gate
      (`scripts/run_lakehouse_quality_gates.py:34` → `scripts/lint_naming_convention.py`) after the
      renames → exits 0; zero Gold tables without a declared prefix, zero plural Gold table names,
      zero version tokens in table names, zero `_at`-suffixed columns in `ops`, and both reserved
      Feast names present on every `feat_*` table. **The script and its wiring already exist
      (`:9-15,109-155`); this AC is about the renames passing it, not about creating it**
- [ ] AC-P2-20 **(F12, F13)**: `scripts/build_schema_evidence.py` → checks `dim_date` → every
      `date_key` present in any fact table resolves in `dim_date`, `dim_date` carries
      `fiscal_year`/`fiscal_quarter`/`quarter_end_date`, and **no fact table carries
      `fiscal_year` or `fiscal_quarter`**
- [ ] AC-P2-21 **(F14, M8)**: Engineer → reads any `feat_*` row → `event_timestamp = known_from_ts`
      and `created_timestamp` is populated with the ingest wall clock; the CHECK is declared in the
      ERD; ADR-017 states the mapping and why Feast's default tie-break is unsuitable; no builder
      emits `created_ts` into a `feat_*` table
- [ ] AC-P2-22 **(F11)**: Engineer → reads ADR-017 → it records the real vnstock reporting unit, the
      chosen scale, and the fact that Iceberg permits precision widening but prohibits scale change
- [ ] AC-P2-23 **(F17, M11)**: Reviewer → reads `docs/architecture/data-contracts.md` → `open`,
      `high`, `low`, `close` are documented as **đồng** with the `quote.py:345` citation, the
      §Migration table maps every legacy object and field to its target, and
      `docs/07_data_contracts.md` **no longer exists**; a grep of `docs/` returns zero claims that
      vnstock returns prices in VND and zero references to `raw_market_price`, `stg_company_quarter`
      or `(period_year, period_quarter)` outside that migration table
- [ ] AC-P2-24 **(F18, mini 43)**: `scripts/lint_naming_convention.py` → runs → every Bronze table
      starts with `raw_` and every Silver table with `stg_`; zero unprefixed tables in either zone;
      `src/io/paths.py` dataset names match
- [ ] AC-P2-25 **(U-1d)**: Contract checker → receives a row whose `source_unit` is not in the
      recognized set → routes it to `ops.failed_records` with a `failure_reason` naming the unit;
      **it is never normalized by guess**. Every money-bearing Bronze table carries `source_name`
      and `source_unit` as `NOT NULL`

### Reconciliation ACs (2026-09-10, M1 … M11)

Each is WHO → ACTION → RESULT, and each names the observable a consumer sees. AC-P2-26 … AC-P2-31
are **regression cases** that must fail against today's code before the fix and pass after.

- [ ] AC-P2-26 **(M1, regression)**: Data engineer → builds the OBT for one ticker whose Q1-2023 and
      Q2-2023 statements resolve to the **same `company_version_key`**, with `fact_distress_label`
      holding `distress_label = 0` for `2023-Q1` and `distress_label = 1` for `2023-Q2` → the OBT row
      for `2023-Q1` reads `distress_label = 0` and the row for `2023-Q2` reads `distress_label = 1`;
      **neither row takes the other's label**, and `label_by_version` no longer exists in
      `src/transforms/gold/obt_company_quarter_risk.py`
- [ ] AC-P2-27 **(M3, regression)**: Data engineer → merges snapshot `{AAA, name="Alpha", t1}`, then
      `{AAA, name="Alpha2", t2}` (t1 < t2), then **re-merges the first batch** → `dim_company` holds
      exactly two rows; `company_version_key` values are distinct; **no row has
      `valid_to_ts < valid_from_ts`**; the single `is_current` row is the `t2` version; and the
      re-merged snapshot is either a no-op or an `ops.failed_records` row with
      `failure_reason = 'late_scd2_snapshot'` — never an in-place history rewrite
- [ ] AC-P2-28 **(M4, regression)**: Data engineer → loads close 100 for D1 (known at D1), close 110
      for D2 (known at D2), then a **correction to 200 for D2 known at D9** → reading
      `fact_market_price` as of D3 returns `close_price = 110` and `daily_return = +0.10` for D2;
      the corrected vintage carries its own `daily_return` row; **the D3 read never changes when the
      correction lands**, and no later vintage becomes the previous close of an earlier day
- [ ] AC-P2-29 **(M5, regression)**: Data engineer → lands two `report_period`s for one ticker with
      the **same `known_from_ts`** → `feat_company_financial_4q` holds **one** row for that
      `(ticker, event_timestamp)`, carrying the newer period as `as_of_report_period` and the
      aggregate over both; the PK insert does not fail and no row is silently discarded
- [ ] AC-P2-30 **(M5)**: ML engineer → reads a `feat_company_financial_4q` row for a ticker with only
      two known periods → every aggregate is `NULL`, `window_period_count = 2`,
      `feature_completeness = 'insufficient'`; **no zero-fill and no forward-fill appear anywhere in
      the feature output**, and a ticker with zero news in the window shows
      `news_article_count = 0` with `sentiment_mean_30d IS NULL`
- [ ] AC-P2-31 **(M7, regression)**: ML engineer → joins the label for `2023-Q2` to the statement
      vintage that produced it and runs `src/ml/leakage_guard.py` → **`LeakageError` is raised**,
      because the statement's `known_from_ts` (filing, after period end) is later than
      `decision_ts` (period end); the previous-quarter statement in the same fixture passes
- [ ] AC-P2-32 **(M2)**: Analyst → queries `gold.obt_company_quarter_risk` for a restated quarter →
      **both vintages are present** with distinct `known_from_ts` and `is_latest_vintage` true for
      exactly one; `gold.obt_company_quarter_risk_latest` returns exactly one row for that quarter
- [ ] AC-P2-33 **(M6)**: Data engineer → lands `consolidated_audited` and `separate_unaudited`
      statements for one `(ticker, report_period)` at the same `known_from_ts` → **both rows persist
      under the unchanged PK**, `uq_ffs_latest` holds, and the row flagged `is_latest_vintage` is the
      `consolidated_audited` one (precedence rank 1)
- [ ] AC-P2-34 **(M6)**: Contract checker → receives a statement whose `statement_type` is absent or
      unmapped → the row lands in `ops.failed_records` with
      `failure_reason = 'unknown_statement_variant'`; **no row is written with a defaulted
      `consolidated` variant**
- [ ] AC-P2-35 **(M9)**: Analyst → joins `fact_financial_statement.report_period_end_date_key` to
      `dim_date` → `fiscal_year`/`fiscal_quarter` match `report_period`; joining `date_key` instead
      returns the **filing** date's attributes, and the data dictionary plus the column comments state
      which key plays which role for every fact
- [ ] AC-P2-36 **(M9)**: DQ runner → receives a `report_period` whose derived period end is not a
      calendar quarter end → the row routes to `ops.failed_records` with
      `failure_reason = 'fiscal_calendar_mismatch'`; `dim_date` generation asserts
      `fiscal_year = year(calendar_date)` and `fiscal_quarter = quarter(calendar_date)`, and ADR-017
      records the assumption with its evidence
- [ ] AC-P2-37 **(M10)**: Data engineer → publishes the same alert event twice → **one row** in
      `gold.fact_market_alert` keyed by `event_id`; the ERD's PK is `event_id`, the secondary UNIQUE
      `(ticker, alert_type, event_timestamp)` holds, and `sql/schema_evidence.sql` contains no
      `article_hash`, `raised_ts` or `published_ts` column that no builder writes
- [ ] AC-P2-38 **(P2 ↔ P4 parity)**: Engineer → runs the pure-Python builder and the `*_spark`
      builder over one fixture → the two outputs agree row-for-row on `is_latest_vintage`,
      `daily_return`, `date_key`, `report_period_end_date_key` and the label columns; a divergence
      fails the gate. P4 mirrors, it does not redefine (plan §File ownership, P4)
- [ ] AC-P2-39 **(M8, hand-off to P5)**: Engineer → reads the P2 contract → each `feat_*` table
      declares `event_timestamp`, `created_timestamp`, `known_from_ts`, its window-count column and
      `feature_completeness`; P5's Feast sources bind to these tables and columns (P5
      §Feast source parity), and no Feast source points at a fact, an OBT, or a single `data.parquet`
- [ ] AC-P2-40 **(M11)**: Reviewer → greps the repo for the retired names → `docs/07_data_contracts.md`
      is gone, `docs/architecture/data-contracts.md` carries the mapping, and no ADR, doc or contract
      still asserts `is_distressed BOOLEAN`, `(period_year, period_quarter)`, `DOUBLE` money, or a
      Silver-zone `fact_company_quarter_financials`

## Risk Assessment

**Risk (tripwire, plan R-4):** the redesign changes the *set* of Gold tables rather than only their
columns, forcing mass re-authoring of rubric-matrix rows. Signal: more than 20 rows need new
`evidence_path` / `validation_command` values. Mitigation: the design changes columns, keys and
grain, and **renames eight datasets** — `distress_labels`, `distress_holdout_v1`, and the six
Bronze/Silver tables gaining `raw_`/`stg_` prefixes — but it does not change the table *count*;
`src/io/paths.py` keeps all 18 dataset names. Response: **if the count exceeds 20, stop and re-plan
deliberately** rather than discovering it in P4.

**Risk (F9, F18):** the eight dataset renames break rubric rows that cite an old path. Signal: a
matrix `evidence_path` or `validation_command` contains `distress_labels`, `distress_holdout_v1`,
or an unprefixed `bronze.`/`silver.` table name. Mitigation: grep `docs/platform/rubric-matrix.csv`
for all eight tokens **before** renaming — the same mechanism already applied to `company_key`.
Response: re-point the row in the same commit as the rename.

**Risk (F11):** the money scale is committed before the real reporting unit is known, and Iceberg
cannot change scale afterwards. Signal: step 2 begins without a recorded vnstock unit. Mitigation:
step 2 reads the vnstock source **first**. **Resolved 2026-09-02b:** statements arrive in whole đồng
at 1,000đ granularity (`kbs/financial.py:572,369,259`), so scale 0 carries no information loss.
Residual risk moves to the four unverified fallback adapters — mitigated by the `source_unit` column
and a fail-closed rule: an unrecognized `source_unit` routes the row to `ops.failed_records` rather
than being normalized by guess.

**Risk:** the vintage axis multiplies Silver and Gold row counts and a downstream consumer forgets
the filter — e.g. the OBT join fanning labels across three vintages. Signal: OBT row count is a
multiple of the quarter count. Mitigation: `is_latest_vintage`, the AC-P2-4 uniqueness assertion in
the DQ gate, and the partial unique index in the ERD. Response: add the filter at the consumer; the
constraint catches it before Gold is published.

**Risk (F1):** populating `company_version_key` on facts requires an SCD2 range lookup at build time
(`ticker` + `known_from_ts` → the version live at that instant), which is the range join the design
avoids at *query* time — moved to *write* time. Signal: the Gold build slows disproportionately, or a
fact row resolves to zero or two versions. Mitigation: `uq_dim_company_current` plus a build-time
assertion that every fact resolves to exactly one version; the lookup runs once per build instead of
once per query. Response: broadcast `dim_company` (small — one row per ticker per version) and
assert cardinality; a zero-resolution row goes to `ops.failed_records`, never to a NULL FK.

**Risk:** the bare `ALTER TYPE` trap. Signal: timestamps shift by 7 hours after migration.
Mitigation: the migration uses explicit `AT TIME ZONE 'UTC'` and a before/after row-level assertion
on a known value. Response: roll back the migration transaction; it is written as one transaction.

**Risk (F10):** the naming convention is documented but not enforced, and drifts again. Signal: a new
table lands without a prefix and nothing complains. Mitigation: `lint_naming_convention.py` is
already wired as the `naming-convention` gate in `scripts/run_lakehouse_quality_gates.py:34`, which
is the repo's definition of done. Response: fix the name, not the lint.

**Risk:** raising instead of silently defaulting turns previously-passing pipeline runs into
failures. Signal: `failed_records` volume jumps after P2. Mitigation: this is the intended
behavior — those rows were silently corrupt. Route them to `ops.failed_records` with the new
`failure_reason` and report the count as evidence. Response: none; do not restore the silent default.
**Risk (M5):** the feature layer becomes an aggregation engine and quietly absorbs modelling
decisions (imputation, winsorization, target encoding). Signal: a `feat_*` column whose value cannot
be derived from the declared window and its inputs alone. Mitigation: the window contract lists the
permitted aggregates, and `feature_completeness` / `window_*_count` make thin windows visible to the
consumer instead of hidden by a default. Response: move the transformation into the P7/P11 model
pipeline, where it is versioned with the model.

**Risk (M5):** as-of snapshot rows multiply — one row per ticker per input arrival instead of one per
input row. Signal: `feat_*` row count grows faster than the fact row count. Mitigation: the snapshot
set is the distinct `known_from_ts` values of the entity's own inputs, which is bounded by the fact
row count per ticker, not by their product; partitioning is by `month(event_timestamp)`. Response:
restrict the snapshot set to filing instants plus a fixed daily grid, recorded in the contract — not
by silently sampling.

**Risk (M7):** moving `decision_ts` to the period end drops predictors that are legitimately
available before the filing, weakening the model. Signal: P7 reports materially fewer usable feature
rows. Mitigation: the choice is explicit, conservative and recorded, and the alternative is stated in
§Label boundary; `label_available_ts` is retained so a horizon-based relaxation can be evaluated with
evidence. Response: P7/P11 propose a horizon; the contract moves `decision_ts` deliberately — never
by relaxing the guard's comparison.

**Risk (M3):** the SCD2 rebuild path is used as a routine repair and silently rewrites history.
Signal: `dim_company` row count changes on a day with no attribute change. Mitigation: rebuild is a
separate entry point requiring the full ordered snapshot set, logged to `ops.pipeline_run_log`;
the daily merge can only append. Response: revert the transaction and route the late snapshot to
`ops.failed_records` instead.

**Risk (M9):** `report_period_end_date_key` doubles the `dim_date` FK count per fact and a builder
populates one but not the other. Signal: a NULL or unresolvable `report_period_end_date_key`.
Mitigation: both keys are `NOT NULL` with declared FKs, and AC-P2-20's coverage check runs over both
columns. Response: fail the build; a fact without its valid-time key cannot report a fiscal quarter.

## Unresolved and requested dependency changes

### Requested dependency changes (parent decides; frontmatter untouched)

- **`src/ml/` shared-file exception.** P2's contract fixes require edits to `src/ml/leakage_guard.py`,
  `src/ml/label_pipeline.py` and `src/transforms/compute_distress_labels.py`. Only the third is
  inside P2's `owns` list. The plan's §File ownership assigns `src/ml/feast/` to P5 and ML pipelines
  to P7, and leaves the guard/label projection unassigned. **Request:** name P2 the owner of
  `src/ml/leakage_guard.py` and `src/ml/label_pipeline.py` for the duration of this phase, or
  serialize those two files as an integration boundary like `pyproject.toml`. No frontmatter is
  changed by this phase.
- **P5 consumes a P2 column contract.** P5's Feast sources must bind to the `feat_*` tables and to
  `created_timestamp`; that is an interface, not a new dependency edge — P5 already depends on P4,
  which depends on P2.
- **P4 parity assertion — RESOLVED 2026-09-10.** AC-P2-38 asserts Python↔Spark parity for
  transforms P2 owns and jobs P4 owns. The request to confirm the parity check runs in P4's gate
  as well is answered: `phase-04-data-plane.md` AC-P4-30 ports this exact check into P4's own
  success criteria, so a P4-side drift fails there, not only in P2's regression suite.

### Open items

- **U-5 (fiscal calendar).** The calendar-fiscal identity is an assumption, not a verified fact: the
  free tier exposes period labels only and no fiscal-year-end field. It is asserted at generation and
  policed per row (§date_key roles), and it would be replaced by a per-issuer fiscal-year-end
  registry — the same deferral shape as the Tier-2 entity registry (U-2). **Open:** whether any
  in-scope issuer actually diverges. Measurable only once P4 lands real periods; until then the
  `fiscal_calendar_mismatch` counter is the answer.
- **U-6 (label horizon).** `decision_ts = report_period_end_ts` is the conservative default. Whether
  a horizon-based cutoff (period end + k days) is better is a modelling question owned by P7/P11 and
  is **not** decided here.
- **U-7 (`ml.distress_label` key).** The reconciliation moves the upsert key from
  `(ticker, event_timestamp, label_version)` to `(ticker, report_period, label_version)`. Any
  consumer outside `src/ml/label_pipeline.py` that reads `ml.label_table` by `event_timestamp` must
  be repointed by its owner; P2 repoints the writer and the DDL.

### Closed earlier (retained for provenance)


U-1, U-2 and U-3 were closed on 2026-09-02b (§Revision 2026-09-02b). **U-4 closed the same day** by
installing `vnstock` 4.0.7 in a throwaway venv and calling it:

- **VCI delivers whole đồng.** Live: VNM `current_assets` 2026-Q2 = `4.089226e+13` ≈ 40 892 tỷ đồng,
  matching Vinamilk's published balance sheet. Same unit as KBS. `vci/const.py:105`
  `_UNIT_MAP = {"BILLION": "tỷ", …, "MILLION": "triệu"}` looked like a divergence risk and is **dead
  code** — one grep hit across the whole package, its own definition.
- **The four `fallback_sources` have no adapter**, so there was never a unit to verify:
  `source_mapping.yaml` declares three sources with two `enabled: false`; `ingestion_manifest.yaml`
  declares two, both `enabled: false` with `endpoint: fixture` and a comment that the HTTP handlers
  are "reserved future keys"; `vietstock` and `ssi` appear in **no** mapping file (plan D-22).

`DECIMAL(18,0)` therefore holds for every reachable source. The `source_unit` column and its
fail-closed rule (AC-P2-25) stay in place as a **regression guard**, not as an open question — if a
future adapter delivers tỷ or triệu, the row is rejected rather than silently mis-scaled.

One finding from that session belongs to P4, not P2: the free vnstock tier caps financial statements
at **4 periods**, so 28 of the 32 quarters `collector_config.yaml` asks for are unobtainable
(plan D-21, R-18, `phase-04` §Free-tier data ceiling). It does not affect the contract's types.

## Rubric Citations (phase-03 R-12 closure, appended 2026-09-05)

Every rubric row this phase owns per `docs/rubric-matrix-unified.csv`'s `owning_phase` column, cited so `scripts/verify_rubric_coverage.py` can resolve ownership to an assertion (R-12). Each line names the row's real `rubric_id`, its stated requirement, and its proof artifact/deliverable — the row's own matrix columns, not invented text. Rows whose capability is not yet implemented are forward specs, matching this file's other `AC-P2-*` entries.

- AC-P2-RUBRIC-1: `mini-26-data-storage-how-to-optimize-your-data-storage-dat` — data_engineer -> delivers "Datawarehouse (ví dụ indexing)" -> Datawarehouse (ví dụ indexing) (evidence: `docs/submission/rubric-(mini-coursework)/data_storage.md`)
- AC-P2-RUBRIC-2: `mini-39-documentation-schema-design-visualize-tables-on-al` — data_engineer -> delivers "Visualize tables on all zones" -> Capture màn hình trên DBeaver (evidence: `docs/submission/rubric-(mini-coursework)/schema_design.md`)
- AC-P2-RUBRIC-3: `mini-40-documentation-schema-design-dim-table-with-scd-2` — data_engineer -> delivers "Dim table with SCD 2" -> Dim table with SCD 2 (evidence: `docs/submission/rubric-(mini-coursework)/schema_design.md`)
- AC-P2-RUBRIC-4: `mini-41-documentation-schema-design-feature-tables-feat_-t` — data_engineer -> delivers "Feature tables (feat_ tables) with 2 columns event_timestamp and created" -> Feature tables (feat_ tables) with 2 columns event_timestamp and created (evidence: `docs/submission/rubric-(mini-coursework)/schema_design.md`)
- AC-P2-RUBRIC-5: `mini-42-documentation-schema-design-relationship-between-d` — data_engineer -> delivers "Relationship between dim & fact tables" -> Relationship between dim & fact tables (evidence: `docs/submission/rubric-(mini-coursework)/schema_design.md`)
- AC-P2-RUBRIC-6: `mini-43-documentation-schema-design-naming-convention` — data_engineer -> delivers "Naming convention" -> Naming convention (evidence: `docs/submission/rubric-(mini-coursework)/schema_design.md`)
- AC-P2-RUBRIC-7: `mini-44-novel-ideas-idea-1-idea-1` — data_engineer -> delivers "Idea 1" -> Document idea + proof it worked! (evidence: `docs/submission/rubric-(mini-coursework)/novel_ideas.md`)
