---
phase: 4
title: "Phase 4: Data plane — lakehouse, Iceberg, Spark, Airflow, DataHub, real source"
status: pending
priority: P1
effort: "12-16 days"
dependencies: ["phase-00-gates.md", "phase-02-data-model.md", "phase-03-contracts-rubric.md"]
owns: ["src/lakehouse/", "src/collectors/", "src/generator/", "src/jobs/", "platform/lakehouse/", "platform/orchestration/", "platform/governance/"]
---

# Phase 4: Data plane — lakehouse, Iceberg, Spark, Airflow, DataHub, real source

## Overview

Restore MinIO, Postgres, Lakekeeper, Spark Operator, Airflow and DataHub; bind `src/lakehouse/` to a
live Iceberg REST catalog; implement Bronze→Silver→Gold on the **v2 contract** in Iceberg; wire the
**real vnstock adapter**; teach the generator to emit **restatement vintages**; scale to 10-50M rows;
freeze `gold.distress_holdout @ holdout-v1` pinned to a knowledge-time cutoff (the `_v1` suffix is
dropped from the table name per P2 §Naming Convention — version lives in the Iceberg tag only).
**Resident cost: 2-3 vCPU (stores always-on).**

N-5 is revoked, so this is a **migration, not a parallel path**. Iceberg replaces the Parquet
semantics; it does not run beside them. That is what makes G-2 ("one table format; zero shims")
satisfiable for the first time.

## Requirements

- Functional:
  - Lakekeeper, MinIO, Spark Operator, source Postgres, Airflow, DataHub all `Synced/Healthy`.
  - `src/lakehouse/rest_catalog.py` lists registered Bronze/Silver/Gold tables against live Lakekeeper.
  - Bronze is append-only; Silver/Gold writes overwrite **affected partitions only** and are idempotent.
  - The real vnstock adapter fetches the company list and **full daily OHLCV 2018-2025** for
    ~300 companies across HOSE/HNX/UPCoM, plus the **most recent 4 quarters** of financial
    statements — which is the hard free-tier ceiling, measured (see §Free-tier data ceiling).
    Quarters before that window come from the generator, not from vnstock.
  - The generator emits multiple vintages per `(ticker, report_period)` with realistic revision
    magnitude and lag, plus drift simulation, generator configuration, and the label table.
  - `holdout-v1` resolves to byte-identical time-travel reads and is pinned to a knowledge-time cutoff.
- Non-functional: the fixture adapter remains the CI path; the live adapter is opt-in with
  checkpointing, retry/backoff and `ops.failed_records` routing; DataHub records Bronze→Silver→Gold
  lineage including the vintage axis.

## Architecture

```
ns: dataflow
  Vietnam APIs (vnstock: HOSE / HNX / UPCoM)  ──┐
  Data Generator (multi-vintage restatements) ──┴──►  Bronze  (Iceberg, append-only)
                                                        │
                                                        ▼
                                                      Silver  (Iceberg, idempotent
                                                               affected-partition overwrite,
                                                               vintage preserved)
                                                        │
                                                        ▼
                                                      Gold    (Iceberg, dims + facts + OBT
                                                               + feat_*, partitioned)
                                                        │
                                                        └─► gold.distress_holdout @ holdout-v1

  Lakekeeper  — Iceberg REST catalog, Postgres-backed metadata
  Postgres    — source system, wal_level = logical  (P5 CDC prerequisite)
  Spark Operator — batch transform jobs
  Airflow on Kubernetes — DAG orchestration
  DataHub     — lineage, including the knowledge-time axis
```

### Source-data reality (ADR-020) — updated 2026-09-02b with vnstock source evidence

Verified 2026-09-01: `src/collectors/source_adapters/vnstock_adapter.py` is 13 lines that re-export
`VnstockFixtureAdapter`; `vnstock` appears in no dependency file; `src/collectors/` makes zero
network calls; `configs/collector_config.yaml:1` nevertheless declares `source_mode: online`. The
pipeline currently runs on five synthetic tickers (AAA…EEE).

Verified 2026-09-02b by reading the `vnstock` 4.0.7 wheel — four facts that change this phase:

| # | Fact | Source | Consequence for P4 |
|---|---|---|---|
| 1 | Current version is **4.0.7** with a **Unified UI** (`Market`, `Reference`, `Fundamental`); `balance_sheet()` is served by **KBS**, not TCBS | PyPI metadata; `vnstock/ui/domains/fundamental/equity.py` | The adapter must target the v4 API. TCBS REST paths return 404 today |
| 2 | **Statements arrive in whole VND đồng at 1,000đ granularity**: the request carries `"unit": 1000  # Đơn vị ngàn đồng` and the parser applies `value * 1000.0` | `explorer/kbs/financial.py:572,369,259` | Money columns are `DECIMAL(18,0)` (P2). No rounding logic needed |
| 3 | **Prices arrive in nghìn đồng, not VND**: OHLC and match price are divided by 1000 for stock and ETF assets, then rounded | `explorer/kbs/quote.py:345,506` | **F17.** The adapter must multiply back by 1000 so the lakehouse has one money unit, and `docs/07_data_contracts.md:92-95` must stop claiming VND |
| 4 | Rate limits are **Guest 20 req/min · Community 60 (free registration) · Sponsor 180-600** | `core/utils/auth.py:135-137` | `min_request_delay_seconds: 1` in `collector_config.yaml` implies 60 req/min, so **Community registration is a prerequisite**, not optional. Guest tier needs a 3-second delay |

Two further facts to record in ADR-020, not to act on: `vnai` is a mandatory dependency initialized
by `vnai.setup()` on first use (`vnstock/__init__.py:35,160`), and the licence is
*"Custom: Personal, research, non-commercial"*. Coursework use is inside that grant; the plan states
it rather than leaving it implicit.

### Free-tier data ceiling — measured live 2026-09-02b, closes U-4

`vnstock` 4.0.7 installed in a throwaway venv, guest access, ticker VNM. Three measurements, and one
of them removes a requirement this phase previously asserted.

| Data | Measured on the free tier | Plan requirement | Verdict |
|---|---|---|---|
| Company list | `Listing.all_symbols()` → **1,751 symbols**; by exchange 3,586; by industry 8,186. No cap | ~300 (`max_companies: 300`) | ✅ far exceeds — 300 is self-imposed, not a tier limit |
| Daily OHLCV | `Quote.history('2018-01-01'…'2026-09-01','1D')` → **2,264 rows, 2017-08-08 → 2026-08-28**. No cap | 2018-2025 daily | ✅ full coverage |
| Financial statements | **4 periods, hard cap.** `period='quarter'` → 2026-Q2, 2026-Q1, 2025-Q4, 2025-Q3. `period='year'` → 2025, 2024, 2023, 2022. Both print *"Phiên bản cộng đồng: Dữ liệu báo cáo tài chính giới hạn tối đa 4 kỳ"* | 32 quarters (2018-2025 quarterly) | ❌ **28 of 32 quarters unobtainable** |

Three details that make the statement cap load-bearing rather than a nuisance:

1. **It is not a pagination window.** `_fetch_financial_data(page_size=4)` exists in the KBS
   explorer, but asking `period='year'` returned the four most recent *years*, so the cap applies to
   distinct periods returned per tier, not to one request's page.
2. **The notice appears without registering.** Guest and Community tiers share the 4-period cap;
   only a paid Sponsor plan lifts it. So R-16's "register for Community" does **not** solve this.
3. **KBS financial statements return `shape (0, 0)`** for VNM at every `period` value tried
   (`'quarter'`, `'Q'`, `'2'`, `'year'`). On the free tier only **VCI** serves statements at all.

Consequence for the live-vs-fixture split: the generator is required not only for volume
(ADR-020's original argument — real scale is ~64 000 statement rows against a 10-50M target) but
because **the historical statements do not exist at this tier**. Real vnstock supplies the entity
dimension and the full price history; the generator supplies 2018-2021 statements, the restatement
vintages, and the volume. That split is now measured, not assumed.

Corrected request volume: ~300 statement calls (one each, 4 periods, no pagination possible) +
~300 price-history calls + 1 listing call ≈ **601 requests**, not the 900+ estimated earlier. At
guest 20 req/min that is ~30 minutes; at Community 60 req/min, ~10 minutes.

### `fallback_sources` is dead configuration — U-4 has nothing left to verify

U-4 asked whether `cafe_f`, `vietstock`, `tcbs` and `ssi` deliver a different money unit. They
deliver nothing. Measured across three config files and the vnstock 4.0.7 package:

| Name | `collector_config.yaml` | `source_mapping.yaml` | `ingestion_manifest.yaml` | vnstock explorer? |
|---|---|---|---|---|
| `vnstock` | `primary_library` | `enabled: true` | reserved key | `kbs`, `vci` |
| `cafe_f` | fallback | `enabled: false`, adapter `html_table` | present as **`cafef`** — different spelling — `enabled: false`, `endpoint: fixture` | **no** |
| `tcbs` | fallback | `enabled: false`, adapter `http_json` | `enabled: false`, `endpoint: fixture` | **no** — removed after vnstock 3.x |
| `vietstock` | fallback | **absent** | **absent** | **no** |
| `ssi` | fallback | **absent** | **absent** | **no** |

`ingestion_manifest.yaml` states its own position in a comment: *"reserved future keys are
`vnstock`, `tcbs_http`, `cafef_scrape`"* — the HTTP handlers were never written, and both declared
sources route to `endpoint: fixture`. Two of the four names (`vietstock`, `ssi`) appear in exactly
one file with no mapping anywhere, and `cafe_f`/`cafef` is spelled two ways across two files.

This is the same defect class as D-18 (`source_mode: online` with zero network calls). **Resolution:
delete `vietstock` and `ssi` from `collector_config.yaml`; keep `cafe_f`/`tcbs` only if their
handlers are actually written, and reconcile the `cafef` spelling.** A fallback that cannot be
reached is not a fallback.

### Unit verification — U-4's real question, answered

Both live explorers deliver **whole VND đồng** for statements:

| Explorer | Evidence | Unit |
|---|---|---|
| KBS | source: `financial.py:572` requests `"unit": 1000  # Đơn vị ngàn đồng`, `:369` `unit_multiplier=1000.0`, `:259` applies it | whole đồng |
| VCI | **live call**: VNM `current_assets` 2026-Q2 = `4.089226e+13`, i.e. 40 892 tỷ đồng — matches Vinamilk's published balance sheet | whole đồng |

`vci/const.py:105` defines `_UNIT_MAP = {"BILLION": "tỷ", …, "MILLION": "triệu"}`, which looked like
a divergence risk. It is **dead code**: grep across the whole package returns exactly one hit, its
own definition. No scaling is applied and none is needed.

### Two sources with distinct, measured roles

| Source | Provides | Cannot provide |
|---|---|---|
| **vnstock live** | 1 751 listed symbols with sector/exchange; full daily OHLCV 2017-2026; the **most recent 4 quarters** of statements in whole đồng | Statements before that 4-period window (free-tier cap), delisting dates, ticker-reuse history, exchange-transfer dates, **and the statement as originally reported before restatement** |
| **Generator** | Statements for 2018-2021, volume to 10-50M rows, drift, skew, cardinality, schema evolution, duplicates, late arrival, **restatement vintages** | Authenticity |

Real scale is ~1600 tickers × ~40 quarters ≈ 64 000 statement rows — three orders of magnitude below
the 10-50M target, so synthesis is required regardless. Making that synthesis produce **restatements**
turns a volume chore into the live demonstration of the bi-temporal model, and gives the P2 leakage
guard something real to catch. This is ML novel idea 1.

## Related Code Files

- Restore from `financial-distress-gitops/archive/ml-track/`: `platform/data/lakehouse/`,
  `platform/orchestration/`, `platform/governance/datahub/`
- Modify: `src/lakehouse/rest_catalog.py`, `catalog.py`, `tables.py`, `snapshots.py`,
  `compaction.py` — bind to live Lakekeeper via `pyiceberg.catalog.rest.RestCatalog`
- Modify: `src/transforms/silver_to_gold.py` — Iceberg writer, idempotent partition overwrite
- **Implement**: `src/collectors/source_adapters/vnstock_adapter.py` — a real adapter, not a
  re-export; rate limiting, retry/backoff, checkpointing into `ops.collector_checkpoint`,
  failures into `ops.failed_records`
- Modify: `src/collectors/company_list_collector.py`, `financial_statement_collector.py`,
  `market_price_collector.py` — adapter selected by `collector_config.yaml:source_mode`
- Modify: `src/generator/offline.py`, `profile.py`, `config.py`, `src/drift/generator.py` —
  multi-vintage restatement emission with configurable magnitude and lag
- Modify: `configs/collector_config.yaml`, `configs/generator-config.yaml`
- Modify: `pyproject.toml` — add `pyiceberg`, `pyspark`, `vnstock`
- Create: `dags/lakehouse_daily_sync.py`, `dags/drift_check.py` (stub; P7 completes it)
- Create: the `gold.distress_holdout` Iceberg tag `holdout-v1` and its snapshot entry

## Implementation Steps

1. **Restore `platform-lakehouse`** (1-2 d) — MinIO, Lakekeeper + its Postgres, Spark Operator,
   source Postgres with `wal_level = logical` set at **initial deploy** (not after data exists).
2. **Bind the Iceberg REST catalog** (2 d) — `curl` Lakekeeper from a Spark pod first, then bind the
   Python client; add `pyiceberg` and `pyspark` to `pyproject.toml`; list Bronze/Silver/Gold identifiers.
3. **Implement the real vnstock adapter** (2 d) — honour `request_timeout_seconds`, `max_retries`,
   `retry_backoff_seconds`, `min_request_delay_seconds`, `checkpoint_every_tickers` and
   `exclude_financial_sector` from `collector_config.yaml`; persist raw payload hashes to
   `ops.source_request_log`; route failed tickers to `ops.failed_records`. Keep the fixture adapter
   as the CI path and make the choice explicit in config, not implicit in an import.
4. **Teach the generator restatements** (1-2 d) — for a configurable fraction of
   `(ticker, report_period)`, emit an original vintage and one or more revised vintages with a
   realistic lag and magnitude; make the revision rate higher for the distressed cohort so the
   leakage effect is measurable. Retain drift simulation, generator configuration and the label table.
5. **Bronze→Silver→Gold on Iceberg** (2-3 d) — Bronze appends duplicates and all vintages; Silver
   overwrites affected partitions only and preserves the vintage axis; Gold is partitioned per P2.
   Run each job twice and diff row count and content.
6. **Scale to 10-50M rows** (1 d) — extend the generator run; verify Bronze holds 10-50M rows /
   5-20 GB; confirm partition pruning works on a representative Gold query.
7. **Restore `platform-orchestration`** (2 d) — Airflow on Kubernetes; daily sync DAG; drift-check
   DAG stub.
8. **Restore `platform-governance`** (1 d) — DataHub; bind `src/governance/datahub_emitter.py`;
   assert the lineage graph carries the knowledge-time axis.
9. **Freeze the holdout** (1 d) — after the first full run, create the Iceberg tag `holdout-v1`
   pinned to a named knowledge-time cutoff; verify two time-travel reads are byte-identical.
10. **Regression** (1 d) — `scripts/run_quality_gates.py` and `pytest tests`.

## Success Criteria

- [ ] AC-P4-1: Argo CD → syncs `platform-lakehouse` → Lakekeeper, MinIO, Spark Operator and source
      Postgres report `Synced/Healthy`
- [ ] AC-P4-2: `src/lakehouse/rest_catalog.py` → lists tables against live Lakekeeper → returns
      Bronze/Silver/Gold identifiers; `tests/platform/pipelines/test_lakehouse_catalog.py` passes
- [ ] AC-P4-3: Spark `iceberg_silver_to_gold` → writes an affected partition twice → row count and
      content identical
- [ ] AC-P4-4: Bronze writer → receives a duplicate business key → appends only; **both vintages
      survive**; dedupe to `is_latest_vintage` happens at Silver, not at Bronze
- [ ] AC-P4-5: Collector → runs with `source_mode: online` → fetches real companies from vnstock
      across HOSE/HNX/UPCoM with sector and exchange, **full daily OHLCV for 2018-2025**, and the
      **most recent 4 quarters** of statements — the measured free-tier ceiling, not a target of 32;
      `ops.source_request_log` records per-request status and retry count; failed tickers land in
      `ops.failed_records`
- [ ] AC-P4-5b: Collector → is asked for a statement period older than the 4-period window →
      **records the gap in `ops.failed_records` with reason `tier_period_cap` and falls through to
      the generator**; it does not silently emit a synthesized row as if it were real, and it does
      not retry a request the tier will never satisfy
- [ ] AC-P4-6: Collector → runs with `source_mode: fixture` → produces the deterministic CI dataset;
      no network call is attempted
- [ ] AC-P4-7: Generator → runs with restatements enabled → produces ≥ 2 vintages for the configured
      fraction of `(ticker, report_period)`; the distressed cohort has a higher revision rate
- [ ] AC-P4-8: Generator → runs at scale → Bronze holds 10-50M rows / 5-20 GB; a Gold query on one
      `report_period` reads only that partition
- [ ] AC-P4-9: Airflow → runs the daily sync DAG → Bronze→Silver→Gold completes and DataHub records
      lineage edges including the knowledge-time axis
- [ ] AC-P4-10: Data engineer → tags the holdout → `gold.distress_holdout` resolves at
      `holdout-v1`, is pinned to a named knowledge-time cutoff, and two time-travel reads are
      byte-identical
- [ ] AC-P4-11: `scripts/run_quality_gates.py` → passes on the Iceberg path; no Parquet-only code
      path remains for Bronze/Silver/Gold

### Mini-track and previously uncited rows (added 2026-09-02)

P3 §`owning_phase` parts 2 and 3 assign these to P4. Each was implemented in the pre-rebuild tree
(`docs/evidence/generator/`, `docs/evidence/airflow/`, `docs/evidence/datahub/`,
`docs/spark-and-storage-optimization.md`) and must be **re-earned on the v2 contract and the Iceberg
path**. Baseline numbers come from tag `evidence-baseline-pre-rebuild` (P3 step 0).

- [ ] AC-P4-12 **(mini 4-7)**: Generator → runs with all offline problems enabled → the profile
      report shows a measured **skew** distribution, **high-cardinality** approx-distinct counts, a
      **schema-evolution** null pattern in old partitions, and a **duplicate rate** within the
      configured tolerance; each of the four is a separate named metric, not one aggregate
- [ ] AC-P4-13 **(mini 8, 13; ML 16; LLM 32)**: Engineer → changes one value in
      `configs/generator-config.yaml` and re-runs → the effective-config artifact records the new
      value and the output distribution shifts accordingly; **no generator behaviour is hardcoded
      outside config**
- [ ] AC-P4-14 **(mini 9)**: Generator → completes a run → the simulated dataset is persisted in a
      location Bronze ingestion reads directly, and a Bronze ingest run consumes it end to end
- [ ] AC-P4-15 **(mini 10-12)**: Generator → runs with streaming problems enabled → emits a
      measured **burst** rate, a measured **late-arrival** fraction with its lateness distribution,
      and a measured stream **duplicate** rate; all three appear in the runtime-validation artifact
- [ ] AC-P4-16 **(mini 14, 19)**: Spark → runs `iceberg_bronze_to_silver` **without** optimizations →
      the baseline runtime, shuffle-read volume and stage count are captured; the same job runs as a
      `SparkApplication` **inside the Airflow DAG**, not by hand
- [ ] AC-P4-17 **(mini 15-18)**: Spark → runs the optimized job → for **each** of skew, high
      cardinality, schema evolution and the fourth offline problem, the artifact pairs the baseline
      number with the optimized number **and a written explanation of which technique was applied and
      why**; `docs/spark-and-storage-optimization.md` carries the four explanations. The explanation
      is the scored part, not the speedup
- [ ] AC-P4-18 **(mini 25)**: Data engineer → runs Iceberg compaction on a Gold table with many small
      files → `rewrite_data_files` reduces the file count with the before/after counts and total size
      recorded; sort-order or z-order is applied and its choice is justified against a named query
- [ ] AC-P4-19 **(mini 27-28, DP1)**: Airflow → runs DP1 (raw → Bronze) → the DAG has a distinct
      **ingest** task and a distinct **validate** task; the validate task fails the run on a seeded
      contract violation
- [ ] AC-P4-20 **(mini 29-30, DP2)**: Airflow → runs DP2 (Bronze → Silver → Gold) → same two-task
      shape; the validate task fails the run on a seeded Gold grain violation
- [ ] AC-P4-21 **(mini 33-36)**: DataHub → shows DP1 and DP2 → each pipeline is linked to its
      upstream and downstream tables with lineage edges, **and** each has its data contract plus a
      validation result attached; the knowledge-time axis appears in both lineage graphs
- [ ] AC-P4-22 **(ML 15; LLM 31)**: `src/drift/generator.py` → runs the drift scenario → the
      distribution of at least one feature shifts measurably between two generated windows, and the
      shift magnitude is recorded
- [ ] AC-P4-23 **(ML 17; LLM 33)**: Generator → emits the label table → `gold.fact_distress_label`
      is populated with `(ticker, report_period, label_version, distress_label, decision_ts)` and
      joins to `obt_company_quarter_risk` with zero unmatched label rows
- [ ] AC-P4-24 **(mini 44-45, novel idea)**: Generator → runs with restatements enabled → the
      multi-vintage output is the artifact for the generator-restatement novel idea, with the
      measured revision rate, lag distribution and the distressed-cohort correlation recorded
- [ ] AC-P4-25 **(U-4 — CLOSED 2026-09-02b, retained as a regression guard)**: Collector → fetches
      the same ticker's balance sheet from every **reachable** source → magnitudes agree in whole
      đồng, and each row records its `source_unit`. Verified live: KBS by source
      (`financial.py:572,369,259` → ×1000 from ngàn đồng) and VCI by call (VNM `current_assets`
      2026-Q2 = `4.089226e+13`). `vci/const.py:105` `_UNIT_MAP` is dead code — one grep hit, its own
      definition. Any source whose unit cannot be determined is **removed from `fallback_sources`**,
      never guessed at
- [ ] AC-P4-25b **(dead config)**: `configs/collector_config.yaml` → lists only fallbacks that have
      a written handler → `vietstock` and `ssi` are **removed** (they appear in no mapping file at
      all); `cafe_f` and `tcbs` are removed too unless their handlers exist, and the
      `cafe_f`/`cafef` spelling is reconciled across `source_mapping.yaml` and
      `ingestion_manifest.yaml`. `scripts/run_manifest_smoke.py` passes against the reduced set
- [ ] AC-P4-26 **(F17, confirmed live)**: Price adapter → ingests one real OHLCV row → the stored
      `close_price` is in **đồng** (vnstock's nghìn đồng × 1000). Measured baseline: VNM `close`
      returns in the range **46.45 … 98.98**, i.e. 46 450 … 98 980 đồng. A known ticker's stored
      close matches the exchange's published price in đồng, not off by 1000×
- [ ] AC-P4-27 **(F17)**: `docs/architecture/data-contracts.md` → declares `open`/`high`/`low`/
      `close` as **đồng** with the `quote.py:345` citation; grep of `docs/` returns zero remaining
      claims that vnstock delivers prices in VND
- [ ] AC-P4-28 **(F18, mini 43)**: Data engineer → lists Bronze and Silver objects → every Bronze
      dataset is `raw_*` and every Silver dataset is `stg_*`; `src/io/paths.py` and the Iceberg
      catalog agree
- [ ] AC-P4-29: Platform operator → records the vnstock tier in `ops.source_request_log` → the
      collector's measured request rate stays under the active tier's limit (guest 20 / Community
      60 req/min), and the measured sweep — ~601 requests: ~300 statement calls + ~300 price-history
      calls + 1 listing call — completes inside its recorded wall-clock budget. **Community
      registration does not lift the 4-period statement cap** (§Free-tier data ceiling), so it is a
      throughput decision, not a coverage one

## Risk Assessment

**Risk:** Lakekeeper REST is unreachable from Spark pods. Signal: catalog calls time out from inside
the pod. Mitigation: `curl` from a Spark pod before binding the Python client. Response: revert
Lakekeeper to localhost mode for testing; fix DNS or NetworkPolicy before retrying.

**Risk:** Spark OOMs on 10-50M-row batches, made worse by the vintage axis. Signal: executor OOM
kill. Mitigation: partition jobs by date range; size executor memory against the multi-vintage row
count, not the single-vintage one. Response: 1M-row windows in parallel.

**Risk:** `wal_level = logical` requires a Postgres restart and disrupts P5's CDC. Signal: the
setting is applied after data exists. Mitigation: set it at initial deploy. Response: snapshot and
restore Postgres.

**Risk (R-8):** vnstock rate-limits or its upstream schema drifts. Signal: HTTP 429, or a required
contract field missing from the response. Mitigation: `min_request_delay_seconds` + jitter +
`checkpoint_every_tickers` from the existing config; the contract checker routes drifted rows to
`ops.failed_records` rather than failing the run. Response: fall back to `source_mode: fixture` for
the blocked ticker range and record the gap in ADR-020 — do not silently synthesize a real ticker.

**Risk:** restatement synthesis is too mild to produce a measurable leakage delta. Signal: the
holdout AUC gap between latest-vintage and as-known features is near zero. Mitigation: make revision
magnitude and cohort correlation configurable and calibrate before the P7 training run. Response:
regenerate with larger magnitudes; a near-zero gap invalidates the novel-idea evidence.

**Risk:** the Iceberg migration breaks a rubric row pinned to a Parquet path. Signal: a mini-track
`evidence_path` points at `s3a://.../data.parquet`. Mitigation: P3 already greps every
`evidence_path`; re-point affected rows in the same commit as the migration. Response: keep a
read-only Parquet export for the affected evidence row only, and record it as a P4 exception.
