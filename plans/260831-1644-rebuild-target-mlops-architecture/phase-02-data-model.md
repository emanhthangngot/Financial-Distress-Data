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
  - `is_latest_vintage` is a **derived** boolean, enforced by a partial unique index, not a filter
    applied at write time.
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
  - `feat_*.event_timestamp = known_from_ts` is a **design decision**, not a fallback — Feast's
    default tie-break selects the newest `created_timestamp`, which is precisely the leakage this
    model exists to prevent (F14).
  - Gold is partitioned; `src/io/paths.py` no longer resolves to a single `data.parquet`.
  - `scripts/build_schema_evidence.py` loads **real** Gold output, can fail, and asserts a NULL-rate
    ceiling on every nullable FK column (F16).
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
    ticker              VARCHAR NOT NULL,
    report_period       VARCHAR NOT NULL,
    statement_variant   VARCHAR NOT NULL,
    known_from_ts       TIMESTAMPTZ NOT NULL,
    is_latest_vintage   BOOLEAN NOT NULL,
    total_assets        DECIMAL(18,0),
    total_liabilities   DECIMAL(18,0),
    total_equity        DECIMAL(18,0),
    created_ts          TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, report_period, statement_variant, known_from_ts)
);
CREATE UNIQUE INDEX uq_ffs_latest ON gold.fact_financial_statement (ticker, report_period)
    WHERE is_latest_vintage;

CREATE TABLE gold.fact_market_price (
    company_version_key VARCHAR NOT NULL REFERENCES gold.dim_company(company_version_key),
    date_key            INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
    ticker              VARCHAR NOT NULL,
    trading_date        DATE NOT NULL,
    close_price         DECIMAL(18,0),         -- đồng, normalized at the adapter (F17)
    known_from_ts       TIMESTAMPTZ NOT NULL,
    created_ts          TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, trading_date, known_from_ts)
);

CREATE TABLE gold.fact_market_alert (           -- was missing from the ERD (F8)
    company_version_key VARCHAR NOT NULL REFERENCES gold.dim_company(company_version_key),
    date_key            INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
    ticker              VARCHAR NOT NULL,
    alert_type          VARCHAR NOT NULL,
    raised_ts           TIMESTAMPTZ NOT NULL,
    known_from_ts       TIMESTAMPTZ NOT NULL,
    created_ts          TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, alert_type, raised_ts)
);

CREATE TABLE gold.fact_news_sentiment (         -- was missing from the ERD (F8)
    company_version_key VARCHAR NOT NULL REFERENCES gold.dim_company(company_version_key),
    date_key            INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
    ticker              VARCHAR NOT NULL,
    article_hash        VARCHAR NOT NULL,
    sentiment_score     DECIMAL(18,6),
    published_ts        TIMESTAMPTZ NOT NULL,
    known_from_ts       TIMESTAMPTZ NOT NULL,
    created_ts          TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, article_hash)
);

CREATE TABLE gold.fact_distress_label (         -- renamed from distress_labels (F8, F9)
    ticker         VARCHAR NOT NULL,
    report_period  VARCHAR NOT NULL,
    label_version  VARCHAR NOT NULL,
    distress_label SMALLINT NOT NULL,
    decision_ts    TIMESTAMPTZ NOT NULL,        -- the boundary known_from_ts is compared against
    created_ts     TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, report_period, label_version)
);

CREATE TABLE gold.obt_company_quarter_risk (
    company_version_key VARCHAR NOT NULL REFERENCES gold.dim_company(company_version_key),
    date_key            INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
    ticker              VARCHAR NOT NULL,
    report_period       VARCHAR NOT NULL,
    known_from_ts       TIMESTAMPTZ NOT NULL,
    debt_to_asset       DECIMAL(18,6),
    distress_label      SMALLINT,
    PRIMARY KEY (ticker, report_period, known_from_ts)
);

-- GOLD features: Feast axis is knowledge time (F14); real PKs (F7).
CREATE TABLE gold.feat_company_unified (
    ticker            VARCHAR NOT NULL,
    event_timestamp   TIMESTAMPTZ NOT NULL,     -- RESERVED Feast name = known_from_ts
    created_timestamp TIMESTAMPTZ NOT NULL,     -- RESERVED Feast tie-break
    known_from_ts     TIMESTAMPTZ NOT NULL,
    report_period     VARCHAR NOT NULL,
    PRIMARY KEY (ticker, event_timestamp),
    CHECK (event_timestamp = known_from_ts)
);
-- feat_company_financial_4q / _market_30d / _news_30d follow the same shape.
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
- **Create**: `src/transforms/gold/dim_date.py` — generate 2015-01-01…2030-12-31 with fiscal
  attributes; must cover every `date_key` any fact emits (F12, F13)
- Modify: `src/transforms/gold/fact_financial_statement.py` — drop `company_key`; **keep and populate
  `company_version_key` by joining `dim_company` on `(ticker, known_from_ts)`**; add `known_from_ts`
  and `statement_variant`; drop `fiscal_year`/`fiscal_quarter`; **delete the
  `f"{fiscal_year}-01-01"` fallback and raise instead** (D-6)
- Modify: `src/transforms/gold/fact_market_price.py`, `fact_market_alert.py`, `fact_news_sentiment.py`
  — same key treatment; declare their own grain
- Modify: `src/transforms/gold/obt_company_quarter_risk.py` — join on `company_version_key`, filter
  the vintage axis
- Modify: `src/transforms/silver/core.py`, `silver/spark.py` — dedup on the key **including**
  vintage; emit `is_latest_vintage`; `silver.stg_companies` retains snapshot history keyed
  `(ticker, created_ts)`; `_created_timestamp` **raises** instead of returning `datetime.min` (D-5)
- Modify: `src/transforms/features/pit.py` — `_parse_timestamp` raises; PIT join filters to a
  knowledge-time cutoff
- Modify: `src/ml/leakage_guard.py` — compare `feature.known_from_ts` against
  `fact_distress_label.decision_ts`; raise on a missing timestamp instead of skipping the row
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
- Create: `scripts/lint_naming_convention.py`, wired into `scripts/run_quality_gates.py` (F10)
- Create: `tests/test_bitemporal_contract.py`, `tests/test_restatement_leakage.py`,
  `tests/test_naming_convention.py`, `tests/test_dim_date_coverage.py`
- Restore: `tests/test_schema_evidence.py` — currently deleted; only the `.pyc` survives

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
3. **Silver: vintage-preserving dedup** (1-2 d) — dedup key gains the vintage axis; emit
   `is_latest_vintage`; `silver.stg_companies` keyed `(ticker, created_ts)` so SCD2 has history to read;
   `_created_timestamp` raises on unparseable input. Verify Bronze replay is still idempotent and
   that two vintages of one quarter both survive to Silver.
4. **Gold: keys, dimensions, grain, partitioning** (2-3 d) — delete `company_key`; retain and
   **populate** `company_version_key` on every fact; **no durable-key column** (U-2); build and populate
   the enriched `dim_date`; drop `fiscal_year`/`fiscal_quarter` from facts; keep the SCD2 column
   names and expand the tracked set; remove the `date_key` fiscal-year fallback; partition Gold by
   `month(known_from_ts)` (statements) and `day(trading_date)` (prices).
5. **PIT and leakage guard** (1-2 d) — PIT join takes a knowledge-time cutoff; the guard compares
   `known_from_ts` to `fact_distress_label.decision_ts`; both raise on missing timestamps. The step-1
   test must now pass, and must fail again if the vintage filter is removed.
6. **Metadata unification and the naming cutover** (1-2 d) — one database, two schemas,
   `TIMESTAMPTZ` via explicit `AT TIME ZONE 'UTC'`, the 8 `ops` `_at` → `_ts` renames in the same
   migration, merged `data_quality_result` with PK `check_id` + `track` CHECK enum + `(track,
   checked_ts)` index, four foreign keys, deterministic `check_id`, partial unique index on
   `is_current`, `ml.label_table` → `ml.distress_label`.
7. **Naming convention: write it and lint it** (0.5 d) — the §Naming Convention block into
   `docs/architecture/data-model.md`; `scripts/lint_naming_convention.py` asserts gold prefixes,
   singular gold table names, plural bronze/silver, `_ts`/`_date` suffixes with the two reserved
   Feast exceptions, no version token in any table name, no `_at`; wire it into
   `scripts/run_quality_gates.py`.
8. **Falsifiable schema evidence** (1 d) — rewrite `build_schema_evidence.py` against real Gold
   output covering **all 12** Gold datasets; restore `tests/test_schema_evidence.py`; prove it fails
   when a fact row's `company_version_key` is absent from `dim_company`, when a `date_key` is absent
   from `dim_date`, and when a nullable FK column exceeds its NULL-rate ceiling.
9. **Migration and regression** (1 d) — `sql/migrations/002_data_model_v2.sql` as one transaction;
   run `scripts/run_quality_gates.py` and `pytest tests`; re-freeze the contracts.

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
- [ ] AC-P2-13: Engineer → runs `scripts/run_quality_gates.py` and `pytest tests` → both pass, zero skips
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
- [ ] AC-P2-19 **(F9, F10, mini 43)**: `scripts/lint_naming_convention.py` → runs on the repo →
      exits 0; zero Gold tables without a declared prefix, zero plural Gold table names, zero
      version tokens in table names, zero `_at`-suffixed columns in `ops`, and both reserved Feast
      names untouched
- [ ] AC-P2-20 **(F12, F13)**: `scripts/build_schema_evidence.py` → checks `dim_date` → every
      `date_key` present in any fact table resolves in `dim_date`, `dim_date` carries
      `fiscal_year`/`fiscal_quarter`/`quarter_end_date`, and **no fact table carries
      `fiscal_year` or `fiscal_quarter`**
- [ ] AC-P2-21 **(F14)**: Engineer → reads any `feat_*` row → `event_timestamp = known_from_ts`; the
      CHECK is declared in the ERD; ADR-017 states the mapping and the reason Feast's default
      tie-break is unsuitable
- [ ] AC-P2-22 **(F11)**: Engineer → reads ADR-017 → it records the real vnstock reporting unit, the
      chosen scale, and the fact that Iceberg permits precision widening but prohibits scale change
- [ ] AC-P2-23 **(F17)**: Reviewer → reads `docs/architecture/data-contracts.md` → `open`, `high`,
      `low`, `close` are documented as **đồng**, and the price adapter's ×1000 normalization is
      stated with the `quote.py:345` citation; no document still claims vnstock returns prices in VND
- [ ] AC-P2-24 **(F18, mini 43)**: `scripts/lint_naming_convention.py` → runs → every Bronze table
      starts with `raw_` and every Silver table with `stg_`; zero unprefixed tables in either zone;
      `src/io/paths.py` dataset names match
- [ ] AC-P2-25 **(U-1d)**: Contract checker → receives a row whose `source_unit` is not in the
      recognized set → routes it to `ops.failed_records` with a `failure_reason` naming the unit;
      **it is never normalized by guess**. Every money-bearing Bronze table carries `source_name`
      and `source_unit` as `NOT NULL`

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
or an unprefixed `bronze.`/`silver.` table name. Mitigation: grep `docs/phase2/rubric-matrix.csv`
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
table lands without a prefix and nothing complains. Mitigation: `lint_naming_convention.py` is wired
into `scripts/run_quality_gates.py`, which is the repo's definition of done. Response: fix the name,
not the lint.

**Risk:** raising instead of silently defaulting turns previously-passing pipeline runs into
failures. Signal: `failed_records` volume jumps after P2. Mitigation: this is the intended
behavior — those rows were silently corrupt. Route them to `ops.failed_records` with the new
`failure_reason` and report the count as evidence. Response: none; do not restore the silent default.

## Unresolved — none

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
