---
phase: 3
title: "Phase 3: Unified rubric matrix, ADRs, verification tooling"
status: pending
priority: P1
effort: "7-10 days"
dependencies: ["phase-01-naming-cutover.md", "phase-02-data-model.md"]
owns: ["docs/platform/adr/", "docs/rubric-matrix-unified.csv", "scripts/verify_*.py", "scripts/_rubric_items.py"]
---

# Phase 3: Unified rubric matrix, ADRs, verification tooling

## Overview

Source-only. Build the single artifact that makes O-2 measurable: a 161-row / 300-point matrix where
**every row names its owning phase**, plus the two verifiers that gate the whole plan. Write the ADR
stack that records the revoked locks and the new data model. Delete both old evidence trees.
**Resident cost: 0.**

**P3 is a hard gate.** P4, P6, P7, P8 and P9 cannot open until:
- every one of the 161 rows has exactly one owning phase, and
- every one of the 161 rows is cited by at least one acceptance criterion in its owning phase file, and
- ADR-005, ADR-013, ADR-014, ADR-016, ADR-017, ADR-018, ADR-019, ADR-020, ADR-021 are **accepted**.

The reason is R-6 and R-12:

- **R-6:** 57 ML rows have never executed, and grep of the previous plan's phase files found
  no owner for `Ansible`, `property-based`, `mutation testing`, `equivalence partitioning`,
  `boundary value`, `rate limit`, `basic auth`, `KNative Eventing`, `TTL`, `Jupyter`/`notebook`, or
  `--atomic`/`rollingupdate`.
- **R-12 (found 2026-09-02):** measured across all 13 phase files — 162 AC lines, 74 rubric
  citations, and **zero citations of any `mini` row**. Plus 11 ML/LLM rows uncited (ML 15-17, 43;
  LLM 2-3, 31-33, 47, 55). Total **118 of 300 points had no acceptance criterion anywhere**, so
  executing every AC in the plan would have produced 182 points, not 300. §`owning_phase` parts 2
  and 3 close it.

An unowned rubric row is an unearned point. **An owned row with no AC is the same thing wearing a
hat** — ownership without an assertion produces no artifact, and `verify_rubric_coverage.py` would
then fail at P12 on a matrix that had looked complete since P3.

## Requirements

- Functional:
  - `docs/rubric-matrix-unified.csv`: 161 data rows, 20 columns (19 existing + `owning_phase`),
    300 points, no duplicate `rubric_id`, zero `design_only` at terminal state.
  - `scripts/verify_rubric_coverage.py`: fails if any row lacks an owning phase, an
    `evidence_path`, a `validation_command`, or a `behavioral_assertion`. **Additionally fails if
    `track=mini` has zero rows for any of P2/P4/P5/P11, or if any row's `rubric_id` is not cited by
    an `AC-P<n>-<m>` line in its owning phase file** (R-12).
  - `scripts/verify_target_architecture.py`: one check per target-image component (83 from
    `reports/debate-proposal.md:880-882`). Exits non-zero against an empty cluster listing all 83.
    **The `Phase` column in that source table uses the predecessor's 10-phase numbering and is
    stale** — every component is re-mapped to the current P0-P12 numbering as part of step 6.
  - ADR stack complete and accepted, including ADR-020 and ADR-021.
  - Old evidence trees deleted — **but only after the pre-rebuild baseline tag exists** (step 0).
- Non-functional: zero cluster changes; all scripts idempotent; no pinned evidence artifact survives.

## Architecture

```
docs/Coursework Tracking (Public) - rubic (mini-coursework).csv
    84 physical lines → 47 logical records → 44 scored rows / 100 pts
docs/Coursework Tracking (Public) - rubic final-coursework (final - ml).csv
    60 logical records → 57 scored rows / 100 pts
docs/Coursework Tracking (Public) - rubic final-coursework (final - llm).csv
    63 logical records → 60 scored rows / 100 pts
docs/platform/rubric-matrix.csv
    117 data rows / 19 cols — 60 LLM `executed` + 57 ML `design_only`
                        │
                  merge + normalize + assign owning_phase
                        ▼
docs/rubric-matrix-unified.csv    161 rows / 300 pts / 20 cols
```

All four row counts verified 2026-09-01.

### `owning_phase` assignment — part 1: the ML/LLM rows with no previous owner

| Rubric item | Rows | Points | Owning phase |
|---|---|---|---|
| Ansible configure + deploy, split into roles | ML 44, LLM 48 | 3 | **P6** |
| Property-based idempotency testing | ML 13, LLM 29 | 4 | **P11** |
| Mutation testing (mutmut) | ML 12, LLM 28 | 4 | **P11** |
| Equivalence partitioning / boundary value analysis | ML 11, LLM 27 | 4 | **P11** |
| Unit test coverage > 90 % | ML 10, LLM 26 | 3 | **P11** |
| Load test + HTML report | ML 14, LLM 30 | 4 | **P11** |
| Basic auth + rate limit on NGINX | ML 41, LLM 45 | 4 | **P9** |
| Domain + HTTPS | ML 42, LLM 46 | 2 | **P9** |
| KNative Eventing for the drift API | ML 34 | 1 | **P7** |
| Feast TTL per table **with rationale** | ML 21 | 2 | **P5** |
| Jupyter notebooks | ML 22, LLM 21, LLM 22 | 6 | **P7** (ML), **P8** (LLM) |
| Helm rollingupdate + `--atomic` auto-fallback | ML 4, ML 7, LLM 11, LLM 17 | 8 | **P9** |
| Notebook → pipeline step parity | ML 23 | 2 | **P7** |
| Incremental data versioning | ML 26 | 2 | **P7** |
| Distributed training | ML 24 | 2 | **P7** |
| Log viewer behind NGINX (Kibana/Loki) | ML 38, LLM 41 | 4 | **P9** routing, **P12** stack |
| Trace viewer behind NGINX (Jaeger) | ML 39, LLM 42 | 4 | **P9** routing, **P12** stack |
| Agent registry: deploy, publish ×3, UI | LLM 6, 14, 20, 24, 44 | 10 | **P8** |
| Warm-up / standby mode | LLM 25 | 2 | **P8** |
| Agent test UI + its authentication | LLM 43, LLM 45 | 4 | **P9** |
| LLM token metrics; agent + MCP call metrics | LLM 53, LLM 54 | 4 | **P12** |
| Clean code + clean repo | ML 55, LLM 58 | 4 | **P11** |
| Low-level design: 5 key classes | ML 56, LLM 59 | 2 | **P3** (authored here) |
| Novel ideas ×2 per track | ML 57-58, LLM 60-61 | 8 | **P7** / **P8**; the PIT restatement demo from P2 is ML idea 1 |

### `owning_phase` assignment — part 2: the 44 mini rows (added 2026-09-02)

Audit finding: **not one acceptance criterion in any phase file cited a `mini` row**, and part 1
above listed zero mini rows. That is 100 of the 300 points with no owner and no AC — the whole
`track=mini` set. The table below closes it. Row numbers are the scored-row index in
`docs/Coursework Tracking (Public) - rubic (mini-coursework).csv` (header excluded, total row excluded).

| Rubric item | Rows | Points | Owning phase |
|---|---|---|---|
| Docker & Docker Compose; optimized Dockerfile (multistage) | mini 2-3 | 3 | **P11** |
| Generator, offline problems: skew, high cardinality, schema evolution, duplicates | mini 4-7 | 8 | **P4** |
| Generator configuration (offline) | mini 8 | 2 | **P4** |
| Store simulated data for Bronze ingestion | mini 9 | 2 | **P4** |
| Generator, streaming problems: burst, late arrival, duplicates | mini 10-12 | 6 | **P4** |
| Generator configuration (streaming) | mini 13 | 2 | **P4** |
| Spark job: baseline without optimization | mini 14 | 2 | **P4** |
| Spark job: handle skew / cardinality / schema evolution / other, **each with explanation** | mini 15-18 | 12 | **P4** |
| Spark job integrated into the data pipelines | mini 19 | 2 | **P4** |
| Flink job: baseline without optimization | mini 20 | 2 | **P5** |
| Flink job: handle burst / late arrival / other, **each with explanation** | mini 21-23 | 9 | **P5** |
| Flink window processing | mini 24 | 2 | **P5** |
| Lakehouse storage optimization (compaction, z-order) | mini 25 | 2 | **P4** |
| Warehouse storage optimization (indexing) | mini 26 | 2 | **P2** |
| DP1 Bronze ingest: ingest stage + validate stage | mini 27-28 | 4 | **P4** |
| DP2 Bronze→Silver→Gold: ingest stage + validate stage | mini 29-30 | 4 | **P4** |
| DP3 offline feature table: ingest stage + validate stage | mini 31-32 | 4 | **P5** |
| DP1 governance: lineage + data validation/contract | mini 33-34 | 4 | **P4** |
| DP2 governance: lineage + data validation/contract | mini 35-36 | 4 | **P4** |
| DP3 governance: lineage + data validation/contract | mini 37-38 | 4 | **P5** |
| Schema design: visualize tables on all zones | mini 39 | 2 | **P2** (AC-P2-18) |
| Schema design: dim table with SCD2 (`valid_from_ts`, `valid_to_ts`, `is_current`) | mini 40 | 2 | **P2** (AC-P2-14) |
| Schema design: `feat_` tables with `event_timestamp` + `created_timestamp` | mini 41 | 2 | **P2** (AC-P2-21) |
| Schema design: relationship between dim & fact tables | mini 42 | 2 | **P2** (AC-P2-15) |
| Schema design: naming convention (`dim_` `fact_` `obt_` `feat_` `raw_`) | mini 43 | 2 | **P2** (AC-P2-19) |
| Novel ideas ×2 (5 points each) | mini 44-45 | 10 | **P2** (PIT restatement) / **P4** (generator restatement) |

Total: 44 rows / 100 points. Every row lands in P2, P4, P5 or P11 — no row lands in a phase later
than P5 except the Docker pair, so **the mini track can be captured before P6 opens**. That is what
makes it independent of the G0 quota gate.

**Implementation already exists for most of these** — `docs/evidence/flink/` (baseline, optimized,
comparison, restart), `docs/evidence/generator/`, `docs/evidence/docker/phase8-image-sizes.json`,
`docs/evidence/duckdb_index_benchmark.json`, `docs/evidence/airflow/`, `docs/evidence/datahub/`, and
`docs/submission/rubric-(mini-coursework)/` with all ten sections. P1's rename, P2's contract v2 and
P4's Iceberg cutover invalidate the *numbers* and the *paths*, not the capability. So mini is
**re-capture with content updates**, not a rebuild — provided the baseline is tagged before deletion
(step 0 below).

### `owning_phase` assignment — part 3: the 11 ML/LLM rows with no AC (added 2026-09-02)

| Rubric item | Rows | Points | Owning phase |
|---|---|---|---|
| Simulate data drift | ML 15, LLM 31 | 3 | **P4** |
| Generator configuration (drift) | ML 16, LLM 32 | 3 | **P4** |
| Label table (`id`, `label`) for joins | ML 17, LLM 33 | 4 | **P4** (table shape defined in P2 as `gold.fact_distress_label`) |
| Terraform to set up GKE / cloud services | ML 43, LLM 47 | 3 | **P6** |
| Deploy LLM inference platform | LLM 2 | 2 | **P8** |
| Set up a custom model on that platform | LLM 3 | 2 | **P8** |
| A/B test agents with different model configs | LLM 55 | 1 | **P8** |

The LLM-track equivalents of most part-1 items are already `executed` — the implementations exist and
the work is to **port the pattern to the ML track**, not to invent it.

### ADR stack

| ADR | Action | Content |
|---|---|---|
| ADR-005 | amend | Feast offline store = Postgres, not object storage |
| ADR-006 | un-defer | MLflow promotion active from P7 |
| ADR-010 | supersede | banner: "Superseded by ADR-016 (2026-09-01)" |
| ADR-013 | amend | CDC path = Debezium → Kafka → Flink, not Flink-CDC direct |
| ADR-014 | amend | Distributed training = Ray, not Kubeflow Trainer HTTP |
| **ADR-016** | new | Full platform restore; supersedes ADR-010; names Istio, Vault, Jenkins, Argo Rollouts, ML track |
| **ADR-017** | new | **Entity and temporal model.** Delete `company_key` only; **retain `company_version_key`** as the `dim_company` PK and the fact join key (Kimball: facts join the dimension surrogate, never the natural key); **`ticker` is both the natural key and the durable key — no `company_durable_key` column** (U-2: it would be a pure function of `ticker` in the same row, i.e. `company_key` renamed, repeating D-2). **Keep `valid_from_ts`/`valid_to_ts`/`is_current` verbatim** (mini row 40, whose parenthetical lacks the "or similar" clause that rows 42 and 43 carry) with the system-time semantics recorded here and aliased by `dim_company_sys`. One identifier for the knowledge axis: **`known_from_ts`**. Grain includes `statement_variant` + `known_from_ts`, declared as a real PRIMARY KEY. `is_latest_vintage` derived, enforced by a partial unique index. `feat_*.event_timestamp = known_from_ts` because Feast's default `created_timestamp` tie-break selects the newest vintage. Money **`DECIMAL(18,0)`**: vnstock statements arrive in whole đồng at 1,000đ granularity (`explorer/kbs/financial.py:572,369,259`), so scale 0 loses nothing; measured cost 9.36 B/value vs 16.66 at precision 38; Spark promotes `SUM` to `DECIMAL(28,0)` whereas precision 38 cannot promote at all. Iceberg permits precision widening but prohibits scale change. Tier-2 entity registry deferred with ticker reuse recorded as a known limitation |
| **ADR-018** | new | **Metadata unification.** One database, schemas `ops` + `ml`, `TIMESTAMPTZ` everywhere, `_ts` suffix everywhere (the 8 `ops` `_at` columns migrate), four foreign keys, merged `data_quality_result` with **PK `check_id`** and `track` as a CHECK-constrained column, nullable FK columns carry a NULL-rate ceiling. Revokes the `AGENTS.md` cross-write ban |
| **ADR-019** | new | **Naming cutover and its two exceptions** — `supabase/migrations/` and `plans/` |
| **ADR-020** | new | **Source data reality.** `vnstock_adapter.py` re-exports the fixture; `vnstock` is in no dependency file; there are zero network calls in `src/collectors/`; `collector_config.yaml` claims `source_mode: online`. Records the live-vs-fixture split adopted in P4 and the 2026-09-02b measurements: vnstock **4.0.7** Unified UI, `balance_sheet()` served by **KBS** and **VCI** only (TCBS removed after 3.x; the four named `fallback_sources` have no handler — `vietstock`/`ssi` appear in no mapping file, `cafe_f` is spelled two ways). **Both live explorers deliver whole đồng** — KBS by source (`financial.py:572,369,259`), VCI by live call (VNM `current_assets` 2026-Q2 = `4.089226e+13`); `vci/const.py:105` `_UNIT_MAP` is dead code. **Prices arrive in nghìn đồng**, confirmed live (VNM close 46.45…98.98), so `docs/07_data_contracts.md:92-95` is wrong by 1000× (F17). **The free tier caps statements at 4 periods** — not a pagination window, not lifted by Community registration — so 28 of 32 required quarters are unobtainable and synthesis is required for history, not only for volume. Company list (1 751 symbols) and daily OHLCV (2 264 rows, 2017-2026) are uncapped. Rate tiers Guest 20 / Community 60 / Sponsor 180-600 req/min; measured sweep ≈601 requests. Mandatory `vnai` dependency initialized via `vnai.setup()`; licence *"Custom: Personal, research, non-commercial"* — coursework use is inside the grant |
| **ADR-021** | new | **Naming convention.** The declared table/column/type/constraint convention from `phase-02` §Naming Convention, plus the renames it forces — `distress_labels` → `fact_distress_label`, `distress_holdout_v1` → `distress_holdout`, `label_table` → `distress_label`, `ops.*_at` → `ops.*_ts`, and **the six Bronze/Silver prefixes `raw_`/`stg_`** required by mini row 43's second clause (F18) — and the two reserved Feast names. Enforced by `scripts/lint_naming_convention.py` in `run_quality_gates.py` |
| ADR-002, ADR-004, ADR-009, ADR-012 | untouched | — |

## Related Code Files

- Create: `docs/rubric-matrix-unified.csv` (161 rows, 20 columns)
- Create: `docs/platform/adr/adr-016-full-platform-restore.md`
- Create: `docs/platform/adr/adr-017-entity-and-temporal-model.md`
- Create: `docs/platform/adr/adr-018-metadata-unification.md`
- Create: `docs/platform/adr/adr-019-naming-cutover.md`
- Create: `docs/platform/adr/adr-020-source-data-reality.md`
- Create: `docs/platform/adr/adr-021-naming-convention.md`
- Create: `scripts/verify_target_architecture.py`
- Create: `scripts/verify_rubric_coverage.py`
- Create: `tests/platform/verification/test_target_component_coverage.py`
- Create: `tests/platform/verification/test_rubric_row_ownership.py`
- Create: `docs/architecture/low-level-design.md` (5 key classes per track — ML 56, LLM 59)
- Modify: `docs/platform/adr/adr-005|006|010|013|014-*.md`
- Modify: `scripts/_rubric_items.py` — merge the two rubric-item modules into one
- Delete: `docs/phase1/`, `docs/platform/evidence-tree/` — **only after step 0's baseline tag exists**

## Implementation Steps

0. **Tag the pre-rebuild evidence baseline** (0.5 d) — **before anything is deleted**:
   `git tag evidence-baseline-pre-rebuild` covering `docs/evidence/` and `docs/submission/`.
   Rationale: those trees hold the only reference numbers for the ~100 mini points that this plan
   re-captures — `docs/evidence/flink/comparison.json`, `docs/evidence/generator/profile.json`,
   `docs/evidence/docker/phase8-image-sizes.json`, `docs/evidence/duckdb_index_benchmark.json`, and
   `docs/submission/rubric-(mini-coursework)/` with all ten sections. Deleting them before the mini
   ACs exist converts a re-capture into a rebuild. **This step gates step 8.**
1. **Normalize the mini rubric** (1 d) — parse with `csv.reader`, `quotechar='"'`; 47 logical
   records − 1 header − 2 = 44 scored rows; hand-inspect the 16 known multi-line cells; map to the
   19-column schema; set `track=mini`, `evidence_type=pending`, `points` from the source column.
2. **Merge into the unified matrix** (1 d) — append 44 mini rows to the existing 117 → 161. Add the
   20th column `owning_phase`. Validate: 161 rows, no duplicate `rubric_id`, points sum = 300,
   all 20 columns populated.
3. **Assign every owning phase and prove every row has an AC** (1-2 d) — apply §`owning_phase`
   parts 1, 2 and 3; then assert programmatically that (a) no row is unowned, (b) no owning phase is
   outside P2-P12, (c) `track=mini` has rows in P2, P4, P5 and P11, and (d) **every `rubric_id` is
   cited by an `AC-P<n>-<m>` line in its owning phase file**. This step closes R-6 and R-12.
4. **ADR stack** (2 d) — write ADR-016 through ADR-021; amend ADR-005/013/014; un-defer ADR-006;
   banner ADR-010. Each amendment names the superseding runtime, the date, and the `plan.md` line
   that locks it. **All must be accepted before P3 exits.**
5. **Low-level design document** (0.5 d) — 5 key classes for the ML track and 5 for the LLM track,
   with method signatures and the sequence flow (ML 56, LLM 59).
6. **Verification tooling** (1-2 d) — `verify_target_architecture.py` with one check per component
   (83 rows from `reports/debate-proposal.md:880-882`), **re-mapped from the stale 10-phase
   numbering in that table to the current P0-P12 phases**; run it against the empty cluster and
   confirm it exits non-zero listing all 83. `verify_rubric_coverage.py` reads the unified matrix and
   fails on any missing `owning_phase`, `evidence_path`, `validation_command`,
   `behavioral_assertion`, **missing mini coverage per phase, or missing AC citation**.
7. **Recompute the cut ladder** (0.5 d, plan R-9) — for each item in `plan.md` §Schedule Reality,
   compute rubric points at risk per day saved against the **regenerated** matrix. Replace the table
   in `plan.md` with the measured ordering.
8. **Delete old trees and validate** (0.5 d) — `rm -rf docs/phase1/ docs/platform/evidence-tree/`;
   grep for dangling references; run `pytest tests` with zero skips; grep the matrix's
   `evidence_path`, `artifact_path`, `validation_command`, `behavioral_assertion` fields for
   `phase2-data`, namespace-valued `monitoring`, `stage1`, `phase1`, `phase2` → zero matches.

## Success Criteria

- [ ] AC-P3-1: Data engineer → normalizes and merges the three rubric CSVs →
      `docs/rubric-matrix-unified.csv` has 161 data rows, 20 columns, points summing to 300, no
      duplicate `rubric_id`
- [ ] AC-P3-2: `scripts/verify_rubric_coverage.py` → runs against the unified matrix → reports
      **zero rows without an `owning_phase`**; every owning phase is in P2-P12
- [ ] AC-P3-2b **(R-12)**: `scripts/verify_rubric_coverage.py` → runs the AC-citation check →
      **all 161 `rubric_id`s are cited by an `AC-P<n>-<m>` line in their owning phase file**; zero
      uncited rows. Baseline measured 2026-09-02 was 106/161 cited (118 points uncited)
- [ ] AC-P3-2c **(R-12)**: `scripts/verify_rubric_coverage.py` → groups `track=mini` by
      `owning_phase` → **P2, P4, P5 and P11 each own ≥1 mini row**; total mini = 44 rows / 100 points
- [ ] AC-P3-3: Architect → writes ADR-016 → `adr-010-*.md` carries the superseded banner; ADR-016
      names Istio, Vault, Jenkins, Argo Rollouts and the ML track with `plan.md` line citations
- [ ] AC-P3-4: Architect → writes ADR-017 → it states that **`company_version_key` is retained** as
      the `dim_company` PK and the fact join key while `company_key` is deleted, that
      `known_from_ts` is the single knowledge-axis identifier, that
      `valid_from_ts`/`valid_to_ts`/`is_current` keep their names for mini row 40 with the system-time
      semantics recorded, that `feat_*.event_timestamp = known_from_ts`, that money scale is
      irreversible under Iceberg, and that ticker reuse is a known unhandled limitation with the
      vnstock evidence cited
- [ ] AC-P3-5: Architect → amends ADR-005/013/014 and un-defers ADR-006 → all four **accepted**
      before P3 exits; P4, P6, P7, P8, P9 stay blocked until then
- [ ] AC-P3-6: `scripts/verify_target_architecture.py` → run against an empty cluster → exits
      non-zero listing all 83 target components as missing
- [ ] AC-P3-7: Planner → greps the matrix's `evidence_path`, `artifact_path`,
      `validation_command`, `behavioral_assertion` for `phase2-data`, namespace-valued `monitoring`,
      `stage1`, `phase1`, `phase2` → returns zero matches
- [ ] AC-P3-8: Reader → opens `docs/architecture/low-level-design.md` → finds 5 ML classes and 5 LLM
      classes with signatures and a sequence flow
- [ ] AC-P3-9: Planner → recomputes the cut ladder against the regenerated matrix → `plan.md`
      §Schedule Reality carries measured points-at-risk per day-saved, not the estimated ordering
- [ ] AC-P3-10: Engineer → runs `pytest tests` after tree deletion → passes with zero skips
- [ ] AC-P3-11: Engineer → runs `git tag -l evidence-baseline-pre-rebuild` **before** step 8 →
      the tag exists and resolves to a commit containing `docs/evidence/` and `docs/submission/`;
      step 8's deletion is blocked until it does
- [ ] AC-P3-12: Architect → writes ADR-021 → it carries the naming convention verbatim from
      `phase-02` §Naming Convention plus the three forced renames, and
      `scripts/lint_naming_convention.py` exists and is wired into `scripts/run_quality_gates.py`

## Risk Assessment

**Risk:** the mini CSV parse misaligns on multi-line quoted cells. Signal: the reader returns other
than 47 logical records. Mitigation: the count is already verified at 47; assert it in the parser
and fail loudly on any other value. Response: hand-normalize the 44 rows.

**Risk:** a rubric row genuinely has no possible owner because no phase plans that capability.
Signal: AC-P3-2 fails and the row maps to nothing in P4-P12. Mitigation: this is exactly what the
gate is for — it surfaces the gap before implementation instead of at freeze. Response: **add the
capability to the owning phase and re-baseline that phase's effort**; do not mark the row unowned
and proceed.

**Risk (R-12):** step 3's AC-citation check fails for rows whose owning phase has the capability but
no assertion — the exact 2026-09-02 finding. Signal: AC-P3-2b lists uncited `rubric_id`s. Mitigation:
§`owning_phase` parts 2 and 3 pre-assign every one of them, and `phase-02`, `phase-04`, `phase-05`,
`phase-06`, `phase-08` and `phase-11` were amended on 2026-09-02 to carry the matching ACs. Response:
**write the AC in the owning phase file**; never relax the check.

**Risk:** the 83-component table's `Phase` column is stale (it predates the 13-phase split), so a
re-map error silently drops a component. Signal: a component maps to a phase that does not own its
manifests. Mitigation: step 6 re-maps against each phase's `owns:` frontmatter, not against the old
table. Response: correct the mapping; record any genuine orphan in ADR-016.

**Risk:** ADR acceptance stalls and blocks five phases. Signal: ADRs unaccepted past the P3 exit
date. Mitigation: ADR-017 and ADR-018 record decisions the user has already made in this session, so
acceptance is recording, not deliberating. Response: escalate; P4/P6/P7/P8/P9 remain blocked.

**Risk:** deleting the old evidence trees orphans an artifact a later phase expects. Signal: a P12
capture row fails looking for a deleted path. Mitigation: grep for every reference before deletion
and record redirects. Response: the matrix is authoritative — re-point the row, do not restore the tree.

**Risk:** the 83-component inventory does not match what the image actually shows. Signal: a
`verify_target_architecture.py` check has no corresponding resource in any phase's deliverables.
Mitigation: cross-check the 83 rows against the union of all phase `Related Code Files` sections
during step 6. Response: assign the orphan component to a phase, or record it as an image-reading
error in ADR-016.

## Rubric Citations (phase-03 R-12 closure, appended 2026-09-05)

Every rubric row this phase owns per `docs/rubric-matrix-unified.csv`'s `owning_phase` column, cited so `scripts/verify_rubric_coverage.py` can resolve ownership to an assertion (R-12). Each line names the row's real `rubric_id`, its stated requirement, and its proof artifact/deliverable — the row's own matrix columns, not invented text. Rows whose capability is not yet implemented are forward specs, matching this file's other `AC-P3-*` entries.

- AC-P3-RUBRIC-1: `LLM-documentation-low-level-ml-design` — llm_engineer -> delivers "Documentation ; (tất cả documents để trong folder `docs/`, và ở README.md thì mọi người link tới mấy document này nhé. README.md chỉ summari..." -> Document 5 key classes (evidence: `docs/platform/evidence/llm/LLM-documentation-low-level-ml-design.md`)
- AC-P3-RUBRIC-2: `ML-documentation-low-level-ml-design` — ml_engineer -> delivers "Documentation ; (tất cả documents để trong folder `docs/`, và ở README.md thì mọi người link tới mấy document này nhé. README.md chỉ summari..." -> Document 5 key classes (evidence: `docs/platform/evidence/ml/ML-documentation-low-level-ml-design.md`)
