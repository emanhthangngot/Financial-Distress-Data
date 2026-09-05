# ADR-018: Metadata unification

## Status

Accepted — 2026-09-02 (`plans/260831-1644-rebuild-target-mlops-architecture/phase-02-data-model.md`).
Implemented — `feat/phase2-identity-vintage-model`, merged to `dev` 2026-09-05.

## Context

The pre-rebuild metadata layer split `ops` and `ml` across two Postgres
instances with an explicit cross-write ban (`AGENTS.md`: "the two schemas
never cross-write"). `ops.data_quality_result` and `ml.data_quality_result`
duplicated the same shape; `ops` timestamp columns used an inconsistent
`_at` suffix (8 columns) against `ml`'s `_ts` convention; six foreign keys
asserted in `sql/schema_evidence.sql` were never written by any pipeline
(plan D-16/D-17), and the generator left every fact table empty — the
submitted bundle contradicted itself about whether those keys existed at
all.

## Decision

- **One database, two schemas** (`ops`, `ml`) — physically separate Postgres
  instances stay separate in this rebuild (`platform-postgres` for `ml`,
  the product-plane Postgres for `ops`); "one database" describes the
  logical contract each schema init file (`sql/init_ops.sql`,
  `sql/init_ml.sql`) now enforces identically, not a forced physical merge.
- **`TIMESTAMPTZ` everywhere, `_ts` suffix everywhere.** The 8 `ops` `_at`
  columns (`pipeline_run_log.started_at/ended_at/created_at`,
  `dataset_freshness.checked_at`, `schema_version_registry.effective_from/
  effective_to`, `failed_records.created_at`, `backfill_request.created_at`,
  `source_request_log.requested_at`, `collector_checkpoint.updated_at`)
  migrate to `_ts` in the same migration that adds the `TIMESTAMPTZ` cast
  (`sql/migrations/002_data_model_v2.sql`), via explicit
  `AT TIME ZONE 'UTC'` — **never a bare `ALTER TYPE`**, which reinterprets a
  naive value in the session timezone and silently shifts every existing
  row by the server's UTC offset (7 hours on this UTC+7 domain, plan D-13).
- **`ops.data_quality_result` and `ml.data_quality_result` merge into one
  table in `ops`**, PK `check_id` alone (already a deterministic hash of
  `run_id`/`dataset_name`/`check_name`, so a composite key adds nothing but
  poisons the index prefix), disambiguated by a `track TEXT NOT NULL CHECK
  (track IN ('mini','ml','llm'))` column plus a `(track, checked_ts)` index.
  `ml.data_quality_result` is dropped once its rows are migrated or empty
  (`sql/migrations/002_data_model_v2.sql` checks before dropping).
- **Four real foreign keys**, all on tables that carry real rows, replacing
  the six fictional ones: `ops.data_quality_result.run_id`,
  `ops.failed_records.run_id`, `ops.source_request_log.run_id` →
  `ops.pipeline_run_log.run_id`; `ml.rag_chunk.document_hash` →
  `ml.rag_document.document_hash`. All three `run_id` columns stay
  **nullable** — Postgres does not enforce a foreign key when the
  referencing column is NULL (MATCH SIMPLE), so ad-hoc scripts degrade
  gracefully instead of failing outright.
- **Nullable FK columns carry a NULL-rate ceiling**, not just a
  zero-orphans check: a column that is entirely NULL passes "zero orphans"
  trivially, which is the same vacuous-assertion defect as the six fictional
  keys (F16). `src/quality/dq_checks.py::check_null_rate_ceiling` fails when
  the NULL rate exceeds a ceiling (default 5%), wired into
  `configs/dq_rules.yaml` as a critical check.
- `ops.schema_version_registry.is_current` becomes a **derived** flag,
  enforced by a partial unique index (`WHERE is_current`) — never a
  write-time filter — mirroring `gold.dim_company`'s
  `uq_dim_company_current` (ADR-017).
- The `AGENTS.md` cross-write ban between `ops` and `ml` is **revoked**: the
  ban encoded the exact phase split (Phase 1 `ops` vs. Phase 2 `ml`) this
  rebuild erases (`AGENTS.md` §Revision 2026-09-02, "Locks revoked").

## Consequences

- `ops.data_quality_result` is now the single source of truth for DQ
  results across all three rubric tracks (mini/ml/llm); a query filtering
  `track = 'mini'` replaces the old cross-schema union.
- Deterministic `check_id` plus `ON CONFLICT DO UPDATE` (already the
  behavior of `src/metadata/metadata_writer.py::log_dq_result`) makes
  re-logging the same check for one `run_id` idempotent — one row, not two.
- Downstream ML/LLM code that previously read `ml.data_quality_result`
  directly must be repointed at `ops.data_quality_result WHERE track IN
  ('ml','llm')` — tracked as Phase 2 Step 6/9 follow-up alongside the
  physical MinIO storage-layer rename (`src/io/paths.py`).

## Alternatives Considered

- **Physically merge `ops` and `ml` into one Postgres instance** (rejected
  for this rebuild — `ml`'s `pgvector` extension and RAG chunk storage stay
  on `platform-postgres` for isolation from the product-plane database; "one
  logical contract, two instances" achieves the stated goal — a single
  `data_quality_result` shape and naming convention — without a data
  migration across instances that this phase does not need).
- **Keep the composite `(track, check_id)` primary key** (rejected, F4 — the
  current repo's own `init_project_metadata.sql:18` already used `check_id`
  alone correctly before this rebuild; a 3-value leading column constrains
  nothing and only poisons the index).
