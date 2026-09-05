# ADR-017: Entity and temporal model

## Status

Accepted — 2026-09-02 (`plans/260831-1644-rebuild-target-mlops-architecture/phase-02-data-model.md`).
Implemented — `feat/phase2-identity-vintage-model`, merged to `dev` 2026-09-05.

## Context

The pre-rebuild data model carried three defects verified against source
(`phase-02-data-model.md` §Architecture, F1, U-1, U-2):

- `company_key = sha256(upper(ticker))[:16]` was written to every fact row
  and read by nothing — a surrogate that decouples nothing (pure function of
  `ticker`) and is not compact (16 bytes replacing a 3-byte natural key).
- `company_version_key`, the real SCD2 version surrogate
  (`sha256(f"{ticker}|{valid_from}")[:16]`), was written by `dim_company.py`
  but never joined on by any fact builder — a usage defect, not a design
  defect.
- Facts carried no knowledge-time axis at all. Silver deduplicated to the
  latest `created_ts` per business key, destroying every restatement before
  a leakage guard could ever see it (plan D-3/D-4) — the guard was a correct
  check installed downstream of the transformation that removes the
  information it needs.

## Decision

### Identity — two key layers, not zero and not three

- `company_key` is **deleted** from every table (fact, feature, dim) and
  from `src/transforms/` entirely (`src/transforms/keys.py`:
  `company_version_key(ticker, valid_from)` replaces `stable_company_key`).
- `company_version_key` is **retained** as `gold.dim_company`'s primary key
  and **every fact table's join key** — Kimball practice: facts join the
  dimension surrogate, never the natural key. `src/transforms/keys.py`'s
  `resolve_company_version_key(ticker, known_from_ts, dim_company_rows)`
  performs the SCD2 range lookup (`valid_from_ts <= known_from_ts <
  coalesce(valid_to_ts, infinity)`) and raises on zero or multiple matches —
  never silently picks one.
- `ticker` is both the natural key **and** the durable key — the axis
  analysts `GROUP BY` across versions. **No `company_durable_key` column is
  created** (U-2): a hash of `ticker` alone would be `company_key` renamed,
  repeating the same defect. A real `entity_id` sourced from a curated
  registry is deferred — vnstock exposes no delisting endpoint, so the
  mapping cannot be sourced today (plan D-21, R-18) — and ticker-reuse
  ambiguity is a recorded, unhandled limitation until it lands.

### Time — bi-temporal facts, single-axis dimension

- **One identifier for the knowledge axis, project-wide: `known_from_ts`.**
  Not `known_from`, not `knowledge_ts`. Every Gold fact and feature table
  carries it (`sql/schema_evidence.sql`).
- `gold.dim_company` keeps `valid_from_ts` / `valid_to_ts` / `is_current`
  **verbatim** — mini rubric row 40 names those three columns without the
  "or similar" clause rows 42 and 43 carry, so renaming them to
  `known_from_ts`-style vocabulary would lose the point without gaining
  standard vocabulary. The axis `dim_company` tracks **is** knowledge time
  (the semantic correction is recorded here); `gold.dim_company_sys`
  (`sql/views/dim_company_sys.sql`) exposes the same columns under SQL:2011
  names (`sys_start`/`sys_end`) for anyone who wants that vocabulary
  instead, without creating a second source of truth.
- Intervals are closed-open `[from, to)` per SQL:2011.
- `fact_financial_statement`'s grain is
  `(ticker, report_period, statement_variant, known_from_ts)`, declared as a
  real `PRIMARY KEY` (`sql/schema_evidence.sql`), not only asserted by a DQ
  check. `is_latest_vintage` is **derived**, enforced by a partial unique
  index in Postgres deployments (`sql/init_ops.sql`-style) and by
  `src/quality/dq_checks.py::check_latest_vintage_unique` where the target
  engine (DuckDB) does not support partial indexes.

### Feast — knowledge time is the join axis

`feat_*.event_timestamp = known_from_ts` is a design decision, not a
fallback. Feast's documented tie-break selects the **highest**
`created_timestamp` for a given `event_timestamp` — i.e. the newest vintage,
exactly the leakage this model exists to prevent. `created_timestamp` stays
a tie-break for retries of one ingest only. `event_timestamp` and
`created_timestamp` are Feast-reserved names and are never renamed to fit
the project's `_ts` suffix convention.

### Money — scale is irreversible under Iceberg

Iceberg permits precision widening (`decimal(9,2)` → `decimal(18,2)`) but
**prohibits scale change** — scale alters the Parquet/Avro byte layout and
would corrupt historical reads. Money is `DECIMAL(18,0)`: vnstock's KBS and
VCI explorers both deliver whole VND đồng at 1,000đ granularity
(`kbs/financial.py:572,369,259`; live VCI call, VNM `current_assets`
2026-Q2 = `4.089226e+13`), so scale 0 carries no information loss. Ratios
and rates are `DECIMAL(18,6)`. Every money-bearing Bronze contract carries a
`source_unit` field; an unrecognized unit routes the row to
`ops.failed_records` rather than being normalized by guess
(`src/metadata/schema_registry.py`'s v2 contracts).

## Consequences

- Facts resolving `company_version_key` requires a build-time SCD2 range
  lookup instead of a query-time range join — moved cost, not avoided cost;
  `resolve_company_version_key` asserts exactly-one-match cardinality so a
  zero- or multi-resolution row fails loudly instead of joining wrong.
- Silver row counts multiply with the vintage axis; `is_latest_vintage`
  filtering is mandatory at every downstream consumer, enforced by
  `check_latest_vintage_unique` in the DQ gate.
- `tests/test_restatement_leakage.py` and `tests/test_bitemporal_contract.py`
  encode this ADR as executable contracts: an original and a restated
  vintage of one `(ticker, report_period)` both survive Silver, exactly one
  carries `is_latest_vintage=True`, and the leakage guard raises when a
  feature/label pairing crosses the restated vintage's `known_from_ts`
  against an earlier `decision_ts`.

## Alternatives Considered

- **Delete `company_key` and `company_version_key` both, join facts on
  `ticker`** (rejected, reverses a 2026-09-01 decision — every fact→dim join
  becomes a range join Spark cannot hash- or broadcast-join at the 10-50M-row
  scale phase-04 targets, and the graded ERD loses its only declarable
  fact→dim foreign key, which mini row 42 is scored on).
- **`company_durable_key = hash(ticker)`** (rejected, U-2 — a pure function
  of `ticker` in the same row is `company_key` under a new name).
- **Rename `valid_from_ts`/`valid_to_ts`/`is_current` to knowledge-time
  vocabulary** (rejected — mini row 40 names those exact columns; renaming
  loses the point in the reading where the rubric's parenthetical is
  literal, and gains nothing in the reading where it is not).
