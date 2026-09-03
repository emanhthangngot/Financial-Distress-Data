# Financial Distress Data — Agent Rules

Process memory only. WHY/architecture live in `docs/`; this file is HOW-TO-BEHAVE.

Revised 2026-09-02. Every data-contract rule below was rewritten after two audits
(`plans/260831-1644-rebuild-target-mlops-architecture/reports/advise-260902-1336-rubric-300-architecture-audit.md`
and `.../research-260902-1402-schema-design-audit.md`). The previous rules contradicted the
accepted plan and are deleted, not archived.

## Read This First — the repo is mid-migration

The unified rebuild plan is **accepted but `status: pending`**. Code on `dev` still runs the **v1**
contract. So two rule sets exist and you must know which one binds your task:

| Layer | Binds when | Where |
|---|---|---|
| **Current (v1)** | Any task touching code today | §Current Contract |
| **Target (v2)** | Only inside `plans/260831-1644-rebuild-target-mlops-architecture` phases P2 onward | §Target Contract |

**Never write v2 shapes into v1 code paths, and never "helpfully" migrate a file the active phase
does not own.** Phase file ownership is listed in `plan.md` §File ownership.

## Current Contract (v1 — what the code actually does today)

- Bronze: append-only. Silver/Gold: idempotent writes, `overwrite` on affected partitions only,
  never full-table overwrite.
- Dedupe by business key + latest `created_ts`. **This destroys restatement history** — it is a
  known defect (plan D-3), not a rule to preserve. Do not build new logic that depends on it.
- DQ results go to `ops.data_quality_result`; critical failures halt downstream tasks;
  warning-level failures route rows to `ops.failed_records` and may continue.
- PostgreSQL schemas are still split `ops` / `ml`. The cross-write ban is
  **revoked** by the plan but the schemas are not merged yet — do not cross-write until P2 lands.
- Money is still `DOUBLE`. Do not add new `DOUBLE` money columns; if you must add one now, add it as
  `DECIMAL(18,0)` so P2's migration has nothing to fix.

## Target Contract (v2 — decided, binds from P2)

### Keys

- `company_version_key` = `sha256(f"{ticker}|{valid_from}")[:16]` is the `dim_company` **primary key
  and the fact join key**. Facts join the dimension surrogate; they never join on `ticker`.
- `company_key` = `sha256(ticker)[:16]` is **deleted everywhere**. It decouples nothing and is
  16 bytes replacing a 3-byte natural key.
- `ticker` is the natural key **and** the durable key — the `GROUP BY`-across-versions axis.
  **Do not create a `company_durable_key` column**: it would be a pure function of `ticker` in the
  same row, i.e. `company_key` renamed.
- A real `entity_id` arrives only with the Tier-2 curated registry. Until then ticker reuse is a
  recorded, unhandled limitation.

### Time

- **One identifier for the knowledge axis: `known_from_ts`.** Not `known_from`, not `knowledge_ts`.
- `dim_company` keeps `valid_from_ts` / `valid_to_ts` / `is_current` **verbatim** — mini rubric
  row 40 names those three columns and, unlike rows 42 and 43, carries no "or similar" clause.
  SQL:2011 vocabulary is exposed through the `dim_company_sys` view instead.
- Intervals are closed-open `[from, to)`.
- Dedupe on the business key **including the vintage axis**; `is_latest_vintage` is derived, enforced
  by a partial unique index — never a write-time filter.

### Constraints

- **Bronze: no PRIMARY KEY, no UNIQUE.** Append-only plus a graded duplicate-rate requirement means
  a key would forbid the behaviour being scored. Grain is documented, not enforced.
- **Silver: PK includes the snapshot / vintage axis** (e.g. `(ticker, created_ts)`). A PK on `ticker`
  alone makes SCD2 structurally unable to emit a second version.
- **Gold fact: PK = the full grain.** For `fact_financial_statement` that is
  `(ticker, report_period, statement_variant, known_from_ts)`, plus
  `UNIQUE (ticker, report_period) WHERE is_latest_vintage`.
- A DQ check is not a constraint. Declare the grain in the ERD *and* check it in the DQ gate.
- Nullable FK columns need a **NULL-rate ceiling**. Postgres does not enforce a foreign key on NULL,
  so "zero orphans" passes trivially on a NULL-heavy column — that is a vacuous assertion.

### Types

- Money: **`DECIMAL(18,0)`**. Scale 0 because the source delivers whole đồng at 1,000đ granularity.
  Measured: 9.36 B/value at precision 18 versus 16.66 at 38; Spark promotes `SUM(DECIMAL(18,0))` to
  `DECIMAL(28,0)` whereas `DECIMAL(38,2)` cannot promote at all.
- Ratio / rate / sentiment: `DECIMAL(18,6)`.
- **Iceberg permits precision widening and prohibits scale change.** Scale is a one-way door — get it
  right before the first write.
- Timestamps: `TIMESTAMPTZ`. Migrate with an explicit `AT TIME ZONE 'UTC'`, **never a bare
  `ALTER TYPE`** — a bare cast reinterprets naive values in the session timezone, which is a 7-hour
  silent error on a UTC+7 domain.
- Date surrogate: `INTEGER YYYYMMDD`.

### Feast

- `feat_*.event_timestamp = known_from_ts`. Knowledge time **is** Feast's join axis.
- `created_timestamp` breaks ties between retries of one ingest, nothing more.
- Reason this is not optional: Feast's default tie-break selects the **highest**
  `created_timestamp` for a given `event_timestamp`, i.e. the newest vintage — exactly the leakage
  this data model exists to prevent. Feast's default is the adversary here.
- `event_timestamp` and `created_timestamp` are **reserved names**. Never rename them to fit the
  suffix convention.

## Naming Convention (graded — mini rubric row 43, both clauses)

```
ZONE
  bronze              `raw_` prefix, PLURAL feed name    raw_companies, raw_financial_statements
  silver              `stg_` prefix, PLURAL feed name    stg_companies, stg_financial_statements
  gold                SINGULAR + prefix                  dim_ fact_ obt_ feat_
  ops                 operational metadata               pipeline_run_log, data_quality_result
  ml                  ML metadata                        distress_label, feast_registry_revision

COLUMN
  <x>_key             surrogate key                      company_version_key, date_key
  ticker              natural key AND durable key
  <x>_ts              TIMESTAMPTZ                        created_ts, known_from_ts, valid_from_ts
  <x>_date            DATE                               trading_date, listing_date
  is_<x>              BOOLEAN                            is_current, is_latest_vintage
  event_timestamp     RESERVED — Feast contract
  created_timestamp   RESERVED — Feast tie-break

TYPE
  money               DECIMAL(18,0)    scale irreversible in Iceberg
  ratio / rate        DECIMAL(18,6)
  timestamp           TIMESTAMPTZ
  date surrogate      INTEGER YYYYMMDD
```

- **No `_at` suffix.** The eight `ops` columns migrate to `_ts` in P2.
- **No version token in a table name.** Versions live in Iceberg tags and branches —
  `gold.distress_holdout` at tag `holdout-v1`, never `distress_holdout_v1`.
- **No "table" inside a table or column name.**
- The convention is enforced by `scripts/lint_naming_convention.py`, not by review. A convention
  that is not linted is a convention that drifts.

## Source Data Reality (measured 2026-09-02 against vnstock 4.0.7)

These are facts, not preferences. Do not re-derive them from memory.

- `src/collectors/source_adapters/vnstock_adapter.py` is 13 lines that re-export the fixture.
  `vnstock` is in no dependency file. `src/collectors/` makes zero network calls. Meanwhile
  `configs/collector_config.yaml` declares `source_mode: online`. **The "live adapter" does not
  exist yet** — do not cite it as working.
- vnstock 4.0.7 uses a Unified UI (`Market`, `Reference`, `Fundamental`). Financial statements are
  served by the **`kbs`** and **`vci`** explorers only. TCBS was removed after 3.x; its REST paths
  return 404 today.
- **Statements arrive in whole VND đồng at 1,000đ granularity.** `kbs/financial.py:572` requests
  `"unit": 1000  # Đơn vị ngàn đồng`, `:369` passes `unit_multiplier=1000.0`, `:259` applies it.
  VCI confirmed by live call: VNM `current_assets` 2026-Q2 = `4.089226e+13`.
- **Prices arrive in nghìn đồng, not VND.** `kbs/quote.py:345,506` divide by 1000 for stock and ETF
  assets. Confirmed live: VNM `close` in the range 46.45 … 98.98. `docs/07_data_contracts.md:92-95`
  declares these as VND and is **wrong by 1000×**. Normalize to đồng at the adapter.
- **The free tier caps financial statements at 4 periods, hard.** `period='quarter'` returns the four
  most recent quarters; `period='year'` the four most recent years. It is not a pagination window,
  and Community registration does **not** lift it — only a paid Sponsor plan does. Against the
  configured 2018-2025 quarterly range, 28 of 32 quarters per company are unobtainable. KBS
  statements return `shape (0, 0)` entirely on the free tier; only VCI serves them.
- Company list (1,751 symbols) and daily OHLCV (2,264 rows, 2017-08 → 2026-08) are **not** capped.
- Therefore synthesis is required for statement **history**, not only for volume. When a requested
  period exceeds the tier cap, log it to `failed_records` with reason `tier_period_cap` and fall
  through to the generator. **Never emit a synthesized row as if it were real.**
- Every money-bearing contract carries `source_unit`. The unit is a property of *which adapter
  answered*, not of "vnstock". An unrecognized `source_unit` is **fail-closed**: route the row to
  `failed_records`, never normalize by guess.
- `fallback_sources: [cafe_f, vietstock, tcbs, ssi]` in `collector_config.yaml` is **dead config**.
  `source_mapping.yaml` declares three sources with two disabled; `ingestion_manifest.yaml` declares
  two, both disabled with `endpoint: fixture`; `vietstock` and `ssi` appear in no mapping file at
  all; `cafe_f` is spelled `cafef` in one of the three. Do not treat any of them as a fallback.
- Rate tiers: Guest 20 req/min (no registration), Community 60 (free registration), Sponsor 180-600.
  `min_request_delay_seconds: 1` implies 60/min, so Community registration is a prerequisite for
  that setting. `vnai` is a mandatory dependency initialized via `vnai.setup()`. Licence is
  *"Custom: Personal, research, non-commercial"* — coursework use is inside the grant.

## Rubric Rules

- Scope is **161 rows / 300 points** across three tracks: mini 44/100, ML 57/100, LLM 60/100.
  Verified by parsing the three CSVs in `docs/`; the last row of each CSV is a `100` total row and
  the first row (README + deployment diagram) carries no points.
- **Every rubric row must be cited by an acceptance criterion in its owning phase file.** An owned
  row with no AC produces no artifact. This was the largest measured gap in the plan — 118 of 300
  points had no AC anywhere, including all 44 mini rows.
- Write every acceptance criterion as `WHO -> ACTION -> RESULT` (e.g. "PySpark `silver_to_gold` job
  -> computes `debt_to_asset` -> `total_liabilities / total_assets`, 4dp"). Reject vague AC
  ("system should calculate correctly") before implementing against it — go back to the spec.
- When rubric points and target-image fidelity conflict, **points win** (user decision 2026-09-02).
  Image fidelity yields and the gap is documented, never silently claimed.
- Before deleting any evidence tree, confirm `git tag -l evidence-baseline-pre-rebuild` resolves.
  Those artifacts are the only reference numbers for the ~100 mini points being re-captured.

## Verify Commands

```bash
.venv/bin/python -m pytest tests            # full suite — the definition of done
.venv/bin/python -m pytest tests -m "not slow"   # fast loop, no Docker, no Postgres binaries
.venv/bin/python -m pytest tests -k <name>  # single test, use while iterating
.venv/bin/ruff check src dags tests scripts
.venv/bin/black --check src dags tests scripts
docker compose config                        # validates compose file without starting anything
.venv/bin/python scripts/run_stage1_quality_gates.py   # one-shot: runs all four above
```

Definition of done for any code change: the one-shot gate above passes. CI
(`.github/workflows/ci.yml`) runs the same gate on push/PR to `main`/`dev`.

Do not run the full suite for a one-file change — target it with `-k` first, run the full suite
before declaring done.

## Time-Costly — avoid unless the task needs it

- `scripts/run_stage1_quality_gates.py --include-services` and
  `scripts/stage1_readiness_report.py --include-services` need the Docker stack already running.
  Don't start the stack just to run these.
- `scripts/run_stage1_real_e2e.py` hits live Kafka/MinIO/Postgres/Airflow containers — full stack
  boot, not a quick check. `tests/test_real_e2e_contracts.py` pins that script's contracts against
  fixtures and `tmp_path`; it needs no live service and runs in the fast loop.
- `scripts/run_flink_benchmark.py` requires `ENABLE_FLINK=1` and the `flink` compose profile — skip
  unless the task is Flink streaming evidence. `tests/test_flink_integration.py` pins the Flink
  client and DAG opt-in behaviour with `urllib` fakes and `monkeypatch`, by design.
- `-m "postgres"` selects `tests/platform/product/*`, which spins an ephemeral Postgres cluster per
  session via local `initdb`/`pg_ctl` (skips without them, unless `PHASE2_REQUIRE_PG=1`, which CI
  sets). Markers select; they never skip.
- `--strict-markers` catches an unregistered marker used via `@pytest.mark.foo`, **not** a typo in an
  `-m` selection expression — `-m "not sloow"` silently matches zero tests rather than erroring.

## Git Conventions

- Commit subject: Conventional Commits, `type(scope): summary`. Types in use: `feat`, `fix`, `docs`,
  `chore`, `test`, `style`, `ci`.
- **Never add a co-author trailer (no `Co-Authored-By`) or any AI-attribution line.**
- Branch name: `type/kebab-slug` matching the commit type.
- Merge to `main`/`dev` through a PR; don't push directly to `main`.
- `AGENTS.md` is imported by `CLAUDE.md` via `@AGENTS.md` and referenced by seven docs plus
  `tests/test_rubric_coverage.py`. Deleting it breaks that import and a test — if it goes missing in
  the working tree, restore it rather than committing the deletion.

## Task Start Checklist

State before editing code or pipeline configs:

- Which contract binds — **v1 (current code)** or **v2 (a plan phase you are executing)**.
- The phase that owns the files you are about to touch, from `plan.md` §File ownership.
- Spec or plan file(s) read for this task.
- Acceptance criteria in `WHO -> ACTION -> RESULT` form, and the rubric row each one serves.
- Verify command(s) you'll run before calling it done.

## Claim Discipline

Load-bearing statements carry the grammar of their evidence:

- **Observed** — you ran it, read it, measured it this session: "X returns …".
- **Derived** — follows from observed facts via a mechanism you can state: "X implies …, because …".
- **Prior** — training knowledge, may be stale: "X is typically …" — verify if load-bearing.
- **Assumed** — unverified and required: "I am assuming X; if wrong, then …".

Version-sensitive claims (APIs, flags, defaults, prices, library versions) are stale until checked.
This session's TCBS endpoints returned 404 from exactly that failure mode. A claim a tool can settle
in seconds is never settled by reasoning alone.

## Mandatory Skill Activation

Before acting, classify the request using the installed `ak:*` skill catalog. Codex sessions and
Claude Code sessions use the same catalog — see `CLAUDE.md`; `.codex/skills/` is Codex-only.

- User names a skill -> use that skill.
- Codebase discovery or structure questions -> `ak:scout`.
- Bug investigation -> `ak:debug`; bug implementation -> `ak:fix`.
- Feature or configuration implementation -> `ak:plan` for multi-step work, then `ak:cook`; execute
  an existing plan directly when one is provided.
- Test strategy or execution -> `ak:test`; code review -> `ak:code-review`.
- Documentation changes -> `ak:docs`; frontend, backend, database, infrastructure, security, AI,
  media or office-file work -> the matching domain skill.
- Direct explanations and simple read-only answers -> no skill required; state that decision when it
  is not obvious.

When a skill is selected:

1. Read its complete `SKILL.md` before taking task actions.
2. Announce the selected skill and its purpose in the session progress update.
3. Follow its workflow, including required verification and review gates.
4. If multiple skills apply, use the smallest ordered set that covers the request.

Do not invoke skills merely for ceremony. Do not skip a clearly matching skill because the task
appears small; use its lightweight path when available.
