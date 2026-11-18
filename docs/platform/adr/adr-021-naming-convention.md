# ADR-021: Naming convention

## Status

Accepted — 2026-09-02 (`plans/260831-1644-rebuild-target-mlops-architecture/phase-02-data-model.md`
§Naming Convention). Enforced by `scripts/lint_naming_convention.py`
(created and wired into `scripts/run_lakehouse_quality_gates.py`,
`feat/phase2-identity-vintage-model`, merged to `dev` 2026-09-05).

## Context

The repo ran three timestamp suffix conventions simultaneously before this
rebuild (`_ts` 21 uses, `_timestamp` 19, `_at` ~20, measured 2026-09-02
across `sql/*.sql` + `schema_registry.py`), with `ops` on `_at` and `ml` on
`_ts`. mini rubric row 43 is scored on naming convention, and its full text
has two clauses most of the pre-rebuild plan only served one of: a Gold-zone
prefix clause (served) and a Bronze/Silver `raw_`/`stg_` prefix clause
(missed — F18).

## Decision

The convention, verbatim from `phase-02-data-model.md` §Naming Convention:

```text
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
  feat_<entity>_<win> feature table                              feat_company_market_30d
  NO version in a table name — versions live in Iceberg tags/branches

COLUMN
  <x>_key             surrogate key                             company_version_key, date_key
  ticker               natural key AND durable key — GROUP BY axis; never a fact join key
  <x>_ts              TIMESTAMPTZ                               created_ts, known_from_ts, valid_from_ts
  <x>_date            DATE                                      trading_date, listing_date
  is_<x>              BOOLEAN                                   is_current, is_latest_vintage
  event_timestamp     RESERVED — Feast contract, never renamed
  created_timestamp   RESERVED — Feast tie-break, never renamed
  NO `_at` suffix — the 8 `ops` columns migrate to `_ts` (ADR-018)
  NO "table" inside a table or column name

TYPE
  money               DECIMAL(18,0)   scale 0: source granularity is 1,000đ (ADR-017, ADR-020). Irreversible
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

### The renames this convention forces

| Old | New | Driver |
|---|---|---|
| `gold.distress_labels` | `gold.fact_distress_label` | mini row 43 — no prefix, and plural among singular peers |
| `gold.distress_holdout_v1` | `gold.distress_holdout` | version belongs in the Iceberg tag, not the table name |
| `ml.label_table` | `ml.distress_label` | "table" inside a table name — landed in `sql/init_ml.sql` |
| `ops.*_at` (8 columns) | `ops.*_ts` | one suffix, project-wide — landed in `sql/migrations/002_data_model_v2.sql` |
| `bronze.companies` | `bronze.raw_companies` | mini row 43 clause 2 (F18) — landed in `sql/schema_evidence.sql` |
| `bronze.financial_statements` | `bronze.raw_financial_statements` | mini row 43 clause 2 (F18) — landed |
| `bronze.market_prices_daily` | `bronze.raw_market_prices_daily` | mini row 43 clause 2 (F18) — landed |
| `silver.companies` | `silver.stg_companies` | mini row 43 clause 2 (F18) — landed |
| `silver.financial_statements` | `silver.stg_financial_statements` | mini row 43 clause 2 (F18) — landed |
| `silver.market_prices_daily` | `silver.stg_market_prices_daily` | mini row 43 clause 2 (F18) — landed |

`event_timestamp` and `created_timestamp` are the two Feast-reserved
exceptions to the `_ts`/`_timestamp` suffix rule — never renamed, checked by
`scripts/lint_naming_convention.py`'s `RESERVED_FEAST_NAMES` set.

## Enforcement

`scripts/lint_naming_convention.py` parses `sql/schema_evidence.sql`,
`sql/init_ops.sql`, and `sql/init_ml.sql` and fails on: a Gold table with no
declared prefix, a plural Gold table name, any version token (`_v\d+`) in a
table name, an `ops` column with the banned `_at` suffix, or a `feat_*`
table missing either reserved Feast column. It is wired into
`scripts/run_lakehouse_quality_gates.py` as the `naming-convention` gate,
run on every `pytest tests` + `ruff` + `black` pass — the repo's definition
of done. Verified 2026-09-05: `0 findings across 3 SQL files`.

## Consequences

- `src/io/paths.py`'s physical MinIO object names (`bronze/companies/`,
  `gold/distress_labels/`, ...) still use the pre-convention names — the
  logical schema (this ADR, `sql/schema_evidence.sql`) and the physical
  storage layer are **not yet in sync**. Renaming the physical layer
  requires rewiring every read/write call in
  `src/jobs/lakehouse_spark_lakehouse_job.py` in lockstep and verifying
  against a running Spark+MinIO stack — explicitly deferred, tracked as
  Phase 2 follow-up (see `src/io/paths.py`'s own module docstring).
- A drifted table name is now a lint failure, not a silent convention
  violation discovered later at grading time.

## Alternatives Considered

- **Loose reading of mini row 43 clause 2** ("the zone is already encoded in
  the object path, which is 'or similar'") — rejected 2026-09-02: the
  previous revision took this reading and it does not satisfy the clause
  under a strict grading read; six renames inside a phase already rewriting
  `sql/` and `src/io/paths.py` cost little against 2 points at risk.
- **`ops` adopts `_at`, `ml` keeps `_ts`** (meet in the middle) — rejected:
  `ml` was already the better half on every axis this phase touches
  (`TIMESTAMPTZ`, `_ts` suffix, a real FK, composite natural PKs), so the
  migration direction is pulling `ops` up to `ml`'s standard, not averaging
  them.
