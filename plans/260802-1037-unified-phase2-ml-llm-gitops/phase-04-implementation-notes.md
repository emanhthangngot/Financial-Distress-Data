---
title: "Phase 4 implementation notes: publish data, Feast stores, RAG corpus"
description: "File-level execution supplement for phase-04 — module layout, Feast repo shape, RAG/PGVector contract, test-first order, evidence and CI plan."
status: pending
priority: P1
effort: 3d (4 sequential slices)
branch: dev
tags: [phase2, llm-track, feast, rag, pgvector, redis, ci-cd, evidence]
created: 2026-08-08
---

# Phase 4 — Implementation Notes (supplement)

Supplement to `phase-04-publish-data-feast-stores-and-rag-corpus.md`. That file
stays authoritative for scope, success criteria and risk. This file adds the
file-level plan, verified citations, and the decisions phase-04 left open.

Verification basis (re-grepped 2026-08-08, source SHA `39e31fc8`):
`src/drift/`, `feature_repo/`, `dags/phase2/`, `apps/`, `docs/phase2/evidence/llm/`
do **not** exist yet. `src/llm/` and `src/ml/` contain only `contracts.py`.
`.github/workflows/` contains only `ci.yml`.

---

## 0. Decisions this supplement locks

### D1 — Pinned artifact paths beat `phase-04.md` prose

`docs/phase2/rubric-matrix.csv` `artifact_path` is machine-checked by
`tests/phase2/requirements/*.py` (`assert artifact.is_file()`,
test_llm_ac_04_rag.py:62) and by `scripts/audit_phase2_evidence.py:_audit_executed`.
Verified pinned paths for this phase:

| rubric_id (csv line) | artifact_path | phase-04 step |
|---|---|---|
| `LLM-improve-the-data-generato-simulate-data-drift` (22) | `src/drift/generator.py` | 2 |
| `LLM-improve-the-data-generato-using-generator-configuration` (24) | `src/drift/generator_config.py` | 2 |
| `LLM-improve-the-data-generato-t-o-b-ng-label-c-2-c-t-id-v-la` (23) | `src/ml/label_pipeline.py` | 2 |
| `LLM-rag-rag-data-pipeline` (34) | `src/llm/rag_pipeline.py` | 3,7 |
| `LLM-rag-m-b-o-data-governance-cho-pipe` (33) | `src/llm/data_governance.py` | 7,9 |
| `LLM-ci-cd-job-1` (15) | `.github/workflows/phase2-ci.yaml` | 8 |
| `LLM-ci-cd-job-2` (16) | `.github/workflows/phase2-ci.yaml` | 8 |

Also-pinned by ML-track rows the same work produces for free (not scored in the
LLM-only submission, cost ≈ 0 because the jobs must live somewhere):
`src/ml/feast/feature_definitions.py` (row 77, TTL), `src/ml/feast/offline_job.py`
(78), `src/ml/feast/online_job.py` (79), `src/ml/feast/materialization.py` (80).

Consequence: **`phase-04.md`'s "Create: `src/llm/rag/`" is superseded.**
`src/llm/rag_pipeline.py` is the module. Helpers may live in `src/llm/rag/` only
if `rag_pipeline.py` re-exports the public surface.

### D2 — Two workflow-file facts must both hold

The matrix pins exactly one path, `.github/workflows/phase2-ci.yaml`, for four
CI/CD rows. The user requires three pipeline workflows. Resolution:

- `.github/workflows/phase2-ci.yaml` — reusable (`on: workflow_call`) job template:
  lint → test → build → push immutable digest → open GitOps digest PR. Exists at
  the pinned path, so the contract test passes.
- `phase2-rag-pipeline.yaml`, `phase2-stream-feature-offline.yaml`,
  `phase2-stream-feature-online.yaml` — three thin callers with distinct
  `paths:` triggers. Each produces its own separately-named run, which is what
  "Capture màn hình từng CI/CD pipeline đã run thành công" needs.
- `ci.yml` is untouched (Phase 1 gate).

### D3 — `src/generator/` is read-only

`phase-04.md:52` says "Modify: `src/generator/`". `AGENTS.md` forbids Phase 1
edits, and rubric rows pin `src/drift/` + `src/ml/` anyway. Resolution: treat
`src/generator/` as a read-only dependency.

`src/generator/config.py:127` (`load_generator_config`) constructs
`GeneratorConfig` from **named** keys only — a new top-level YAML key is
silently ignored, so it is safe. But we go further: drift config lives in a
**separate** file `configs/drift-config.yaml`, loaded by
`src/drift/generator_config.py`. Zero Phase 1 file touched. `src/drift/generator.py`
consumes `generate_offline_data()` (`src/generator/offline.py:68`) and
`generate_stream_events()` (`src/generator/streaming.py:21`) as pure inputs and
applies drift as a post-transform.

### D4 — Two Python environments, one import rule

`.venv` (test env, pyproject.toml:24-30) has `minio`, `pyarrow`, `psycopg[binary]`,
`duckdb`. It has **no** `feast`, **no** `redis`, **no** `hypothesis`.
`.venv-phase2` has `feast==0.65.0`, SQLAlchemy, pandas, pyarrow, but **no**
`redis`, **no** `psycopg`.

`AGENTS.md` definition of done runs `.venv/bin/python -m pytest tests`. Therefore:

> **Every new module under `src/drift/`, `src/ml/`, `src/llm/` must import
> `feast`, `redis` and `psycopg` lazily, inside the function that uses them** —
> mirroring the existing pattern at `src/io/minio_publish.py:11`
> (`from minio.commonconfig import CopySource` inside the function).

Module-level imports of `feast` will break the Phase 1 gate. This is the single
highest-probability failure in the phase.

### D5 — Embedding backend is pluggable, with a real default

Neither venv has torch/sentence-transformers (~2 GB). Plan:
`src/llm/rag_pipeline.py` defines a small `EmbeddingBackend` protocol
(`embed(texts) -> list[list[float]]`, `name`, `version`, `dims`) with two
implementations:

- `SentenceTransformerEmbedder` — `all-MiniLM-L6-v2`, 384-dim. Installed in
  `.venv-phase2` and in the phase-2 container image. **This is what the evidence
  run uses.**
- `DeterministicHashEmbedder` — numpy-only, 384-dim, seeded from the content
  hash. Used by unit tests and by CI lint/test jobs so the `.venv` fast loop
  stays dependency-free and byte-reproducible.

Same dimensionality either way, so the PGVector column type never changes.
`embedding_model` + `embedding_version` metadata on every chunk records which
produced it, so a hash-embedded row can never be mistaken for a model-embedded
one. **See Open Question Q1** — confirm before implementing.

### D6 — Hypothesis is not added

`phase-04.md:88` mentions "Hypothesis property tests". `hypothesis` is not in
`pyproject.toml` dev extras. Adding a dep for one phase violates YAGNI. Use
seeded parametrized tests instead (the generator is already seed-deterministic:
`GeneratorConfig.seed`, config.py:81). **See Open Question Q2.**

---

## 1. Target file inventory

```
configs/
  drift-config.yaml              NEW  drift scenarios (seeds, direction, magnitude)
  rag-sources.yaml               NEW  trusted-source registry (license, access class, rate limit)
  phase2-governance.yaml         NEW  DataHub datasets/pipelines for Phase 2 (mirrors configs/datahub/)

src/drift/
  __init__.py                    NEW
  generator_config.py            NEW  PINNED  typed drift config + loader
  generator.py                   NEW  PINNED  apply_drift(), before/after report

src/ml/
  label_pipeline.py              NEW  PINNED  label table build + write
  feast/__init__.py              NEW
  feast/feature_definitions.py   NEW  PINNED  entity, feature views, TTL rationale
  feast/materialization.py       NEW  PINNED  FeatureMaterializationService impl
  feast/offline_job.py           NEW  PINNED  deployable: stream -> OFFLINE
  feast/online_job.py            NEW  PINNED  deployable: stream -> ONLINE

src/llm/
  rag_pipeline.py                NEW  PINNED  RagIngestionService impl (5 methods)
  rag/__init__.py                NEW  optional helpers, re-exported by rag_pipeline
  rag/chunking.py                NEW  chunker + content hashing
  rag/pgvector_store.py          NEW  psycopg PGVector repository
  rag/embedding.py               NEW  EmbeddingBackend protocol + 2 impls
  data_governance.py             NEW  PINNED  PII/licensing/retry/DLQ/rate-limit gates

src/governance/
  phase2_lineage.py              NEW  Phase 2 lineage emitter (reuses datahub_emitter)

feature_repo/
  structured/feature_store.yaml  NEW  project: fd_structured; redis online
  structured/definitions.py      NEW  re-export from src.ml.feast.feature_definitions
  rag/feature_store.yaml         NEW  project: fd_rag; postgres/pgvector online
  rag/definitions.py             NEW  re-export from src.llm.rag_pipeline feature objects

dags/phase2/
  __init__.py                    NEW
  phase2_rag_ingest.py           NEW  wrapper -> src.llm.rag_pipeline
  phase2_feature_materialize.py  NEW  wrapper -> src.ml.feast.materialization
  phase2_stream_feature_offline.py NEW wrapper -> src.ml.feast.offline_job
  phase2_stream_feature_online.py  NEW wrapper -> src.ml.feast.online_job
  phase2_label_drift_build.py    NEW  wrapper -> src.ml.label_pipeline + src.drift.generator

sql/
  init_ml_metadata.sql           NEW  ml schema + pgvector ext + tables

.github/workflows/
  phase2-ci.yaml                 NEW  PINNED  reusable workflow_call template
  phase2-rag-pipeline.yaml       NEW
  phase2-stream-feature-offline.yaml NEW
  phase2-stream-feature-online.yaml  NEW

docker-compose.yml               MODIFY  append 3 services (see §8)

tests/phase2/                    see §9
docs/phase2/evidence/llm/*.md    see §10
```

**Files never touched:** everything under `src/collectors`, `src/generator`,
`src/streaming`, `src/transforms`, `src/quality`, `src/catalog`, `src/metadata`,
`dags/*.py` outside `phase2/`, `.github/workflows/ci.yml`, existing
`docker-compose.yml` service blocks, `sql/init_project_metadata.sql`.

---

## 2. Data flows

**Flow A — drift + labels (offline, batch)**
`configs/generator-config.yaml` + `configs/drift-config.yaml`
→ `src.generator.offline.generate_offline_data` (read-only)
→ `src.drift.generator.apply_drift(rows, scenario)` (deterministic, seeded)
→ before/after report JSON + Markdown → `outputs/phase2/drift/{run_id}/`
→ `src.ml.label_pipeline.build_labels(rows)` (reuses
`src.transforms.compute_distress_labels.compute_labels`,
verified at `src/transforms/compute_distress_labels.py:279`)
→ parquet to MinIO `phase2/offline/labels/` + row copy to
`ml.label_table` in the **new** phase-2 Postgres.

**Flow B — Feast materialization**
MinIO parquet (Phase 1 Gold, read-only) → Feast `FileSource` (s3 endpoint override)
→ `feast apply` → registry on MinIO → `materialize_incremental` → Redis online store
→ registry revision recorded in `ml.feast_registry_revision`.

**Flow C — stream features (two deployables)**
Kafka `market.events` → `src.ml.feast.offline_job` → parquet append to
MinIO `phase2/offline/stream_features/` + checkpoint row.
Kafka `market.events` → `src.ml.feast.online_job` → `store.push(..., to=PushMode.ONLINE)`
→ Redis + checkpoint row. Two processes, two images, two workflows.

**Flow D — RAG**
`configs/rag-sources.yaml` → `fetch_documents` (cache-first) →
`parse_and_chunk` → `deduplicate_chunks` (content hash) →
`enforce_licensing_and_metadata` (delegates to `data_governance`) →
`write_vectors` (embed → PGVector upsert) → ingestion version string
→ manifest to MinIO `phase2/rag/manifests/{ingestion_version}.json`.

**Flow E — lineage**
Every flow's run summary → `src/governance/phase2_lineage.py` →
`src.governance.datahub_emitter.emit_governance` (verified
`src/governance/datahub_emitter.py:139`) with a Phase-2-only `GovernanceModel`
loaded from `configs/phase2-governance.yaml` (loader verified
`src/governance/datahub_model.py:62`). Phase 1 governance config untouched.

---

## 3. Feast repository plan

Two projects, per ADR-005 (`docs/phase2/adr/adr-005-feast-stores.md:22-28`) as
amended by ADR-010 (Redis in-cluster, PGVector in-cluster, local object storage).

### 3.1 `feature_repo/structured/feature_store.yaml`

```
project: fd_structured
provider: local
registry: s3://financial-distress-lake/phase2/feast/structured/registry.db
online_store:  type: redis, connection_string: <REDIS_HOST>:6379,db=0
offline_store: type: file
entity_key_serialization_version: 3
```
S3 endpoint override via `FEAST_S3_ENDPOINT_URL` / `AWS_*` env pointing at MinIO
— the same env the Phase 1 MinIO clients already consume (`src/io/paths.py:10`,
`DEFAULT_BUCKET = "financial-distress-lake"`). **No new S3 client is written.**

### 3.2 Entity and feature views (in `src/ml/feast/feature_definitions.py`)

Entity: `ticker` (`ValueType.STRING`, join key `ticker`).

Table below is the original design intent. **As implemented (slice 4C,
2026-08-08), field names are the real Gold column names** — verified against
`src/transforms/gold/*.py`, which retain every Silver column via
`dict(row)`/`**row` plus surrogate keys rather than projecting to a fixed
renamed subset. There is no `risk_bucket` column anywhere in the real Gold
schema (dropped); `current_ratio`/`debt_to_asset`/`roa`/`z_score` live on
`obt_company_quarter_risk`, not `fact_financial_statement`, so they moved to
`company_risk_features`. `close`/`volatility_30d` are real column names
`close_price`/`volatility_signal` (a boolean flag, not a rolling stdev — see
`src/drift/generator.py`'s comment on the same real-schema-vs-plan gap for
drift). See `feature_definitions.py`'s `GOLD_DATASETS`/`FEATURE_VIEW_RATIONALE`
for the authoritative field lists.

| Feature view | Source | Fields | TTL | One-line business-freshness rationale |
|---|---|---|---:|---|
| `company_financial_features` | `FileSource` → MinIO `gold/fact_financial_statement/` | total_assets, total_liabilities, equity, current_assets, current_liabilities, ebit, net_income | **100 days** | A quarterly filing stays the authoritative view of the company until the next filing lands; 100 d ≈ one quarter plus filing lag, so nothing expires while it is still the newest truth. |
| `company_risk_features` | `FileSource` → MinIO `gold/obt_company_quarter_risk/` | current_ratio, debt_to_asset, roa, z_score, distress_label, distress_reason, training_eligible | **100 days** | Derived from the same quarterly filing, so it must not expire before its parent fact does. |
| `market_price_features` | `FileSource` → MinIO `gold/fact_market_price/` | close_price, volume, daily_return, volatility_signal | **2 days** | A daily bar is superseded by the next trading session; 2 d survives a weekend/holiday gap without ever serving a week-old price as current. |
| `stream_market_features` | `PushSource` (batch fallback = the file source above) | last_price, event_count_1h, price_change_pct_1h | **1 hour** | Intraday aggregates describe the current trading hour only; a longer TTL would let the online API answer "live" with a stale tick. |

`event_timestamp_column` is set on every source even though only the online
store is read this week — phase-04.md:110 makes this non-negotiable.

Label table is **not** a FeatureView. It is offline parquet + a Postgres table,
consumed by phase-05's `TrainingDataService.join_labels`
(`src/ml/contracts.py:30`). Registering it as a feature view would invite a
future leakage bug.

### 3.3 `feature_repo/rag/feature_store.yaml`

```
project: fd_rag
provider: local
registry: s3://financial-distress-lake/phase2/feast/rag/registry.db
online_store: type: postgres  (host = phase-2 pgvector service, db = ml)
offline_store: type: file
```

Entity: `chunk_id` (STRING). Feature view `document_chunk_vectors`, TTL
**365 days** — "tied to document version": a chunk is valid until its parent
document hash changes, at which point ingestion supersedes it explicitly rather
than letting it expire. TTL is a backstop, not the invalidation mechanism.

### 3.4 Feast repo files re-export, they do not duplicate

`feature_repo/structured/definitions.py` is three lines:
`from src.ml.feast.feature_definitions import *  # noqa: F401,F403`.
Feast's repo parser imports the module and inspects module attributes, so
re-exported objects register. **This must be proven by the step-4 smoke test
before the rest of the Feast work is written** — if Feast 0.65 rejects
star-re-export, fall back to putting definitions physically in
`feature_repo/*/definitions.py` and making `src/ml/feast/feature_definitions.py`
import *from* it (the pinned path still has to be a real file that names every
TTL, because that is the row-77 artifact).

---

## 4. RAG pipeline plan

### 4.1 Method mapping (signatures locked — `src/llm/contracts.py:19-39`, do not change)

| Abstract method | Concrete behaviour in `src/llm/rag_pipeline.py` |
|---|---|
| `fetch_documents(source, window)` | Read `configs/rag-sources.yaml` entry `source`. Cache-first: if `phase2/rag/raw/{source}/{doc_hash}` exists locally or on MinIO, return it without a network call. Otherwise fetch under the source's `rate_limit_rps` token bucket + `tenacity` retry, then write to cache. Returns `list[RawDocument]` (frozen dataclass: `source_uri`, `company`, `report_date`, `raw_bytes`, `content_type`, `license`, `access_class`, `fetched_ts`). |
| `parse_and_chunk(documents)` | Dispatch by content type (`text/plain`, `text/html`, `application/pdf`). Recursive character chunking, target 800 chars / 120 overlap, never splitting mid-sentence when a boundary exists within 20% of the target. Emits `Chunk` with all nine metadata fields (§4.3). `parser_version` is a module constant bumped by hand when chunking behaviour changes. |
| `deduplicate_chunks(chunks)` | Two-level. **Document level:** if `document_hash` already exists in `ml.rag_document`, short-circuit — reuse the stored chunk rows, emit zero new vectors. **Chunk level:** drop chunks whose `content_hash` already exists for the *same* `(document_hash, embedding_version)`. Returns only chunks needing embedding. This is what makes success criterion 1 (phase-04.md:97) true. |
| `enforce_licensing_and_metadata(chunks)` | Delegates to `src.llm.data_governance`. Raises `GovernanceViolation` on: missing/denied license, `access_class` not in the allowed set, PII detected in chunk text, any of the nine metadata fields empty. Violating chunks are routed to the quarantine table, not silently dropped. |
| `write_vectors(chunks, embedding_version)` | Embed via the configured `EmbeddingBackend`, then `INSERT ... ON CONFLICT (content_hash, embedding_version) DO NOTHING` into PGVector. Returns `ingestion_version` = `f"{utc_date}-{sha256(sorted content_hashes)[:12]}"` — stable across reruns of identical input, which is how idempotency is *observed* in the evidence run. |

### 4.2 Content-hash strategy

- `document_hash = sha256(raw_bytes)` — identity of the fetched artifact.
- `content_hash = sha256(normalized_chunk_text + parser_version)` — normalized =
  NFKC, collapsed whitespace, stripped. Including `parser_version` means a
  chunker change correctly produces new hashes instead of silently reusing
  chunks that no longer correspond to the stored text.
- Uniqueness in PGVector: `UNIQUE (content_hash, embedding_version)`. Re-running
  with a new embedding model produces new rows (correct — different vector
  space); re-running unchanged produces zero rows.

### 4.3 PGVector table shape (`sql/init_ml_metadata.sql`)

```
CREATE SCHEMA ml;
CREATE EXTENSION IF NOT EXISTS vector;

ml.rag_document(
  document_hash text primary key, source_uri text not null, source_name text not null,
  company text, report_date date, license text not null, access_class text not null,
  fetched_ts timestamptz not null, first_ingested_ts timestamptz not null)

ml.rag_chunk(
  chunk_id text primary key,             -- sha256(content_hash|embedding_version)[:32]
  document_hash text references ml.rag_document,
  content_hash text not null, chunk_index int not null, chunk_text text not null,
  source_uri text not null, company text, report_date date,
  parser_version text not null,
  embedding_model text not null, embedding_version text not null,
  embedding vector(384) not null,
  access_class text not null, created_ts timestamptz not null default now(),
  ingestion_version text not null,
  UNIQUE (content_hash, embedding_version))
CREATE INDEX ON ml.rag_chunk USING hnsw (embedding vector_cosine_ops);

ml.rag_quarantine(... same metadata + violation_reason, quarantined_ts)
ml.rag_ingestion_run(ingestion_version pk, run_id, started_ts, finished_ts,
  documents_fetched, chunks_new, chunks_reused, chunks_quarantined, source_sha)
ml.label_table(...)                 -- §5
ml.feast_registry_revision(...)     -- registry digest per apply
ml.stream_feature_checkpoint(job_name pk, last_offset, last_event_ts, updated_ts)
```

Every one of the nine metadata fields required by phase-04.md:38-41 and success
criterion 5 (phase-04.md:101) is a NOT-NULL column on `rag_chunk`, except
`company`/`report_date` which are nullable for genuinely company-agnostic
sources — governance records `access_class='public_market_commentary'` for those
rather than faking a ticker.

### 4.4 `src/llm/data_governance.py` (the governance row, phase-04.md:78-79)

Public surface, all pure functions or small classes with injected clients:
- `check_licensing(chunk) -> None | GovernanceViolation` — license must be in the
  allowlist from `configs/rag-sources.yaml`; unknown license = violation.
- `detect_pii(text) -> list[PiiFinding]` — Vietnamese national ID, phone, email,
  bank account regexes. Findings block ingestion; the finding *type* (never the
  matched value) is what gets logged.
- `redact(text, findings) -> str` — used only for the quarantine record.
- `RateLimiter(rps)` — token bucket, used by `fetch_documents`.
- `retry_policy()` — `tenacity` config (already in `.venv-phase2`); exponential
  backoff, capped attempts, retry only on transport/5xx.
- `Checkpoint` read/write against `ml.rag_ingestion_run`.
- `quarantine(chunk, reason, conn)` — dead-letter write.
- `assert_metadata_complete(chunk) -> None` — the nine-field contract, one place.

`AGENTS.md` DQ rule mapping: governance violations are **critical** (halt the
ingestion task); PII findings are **warning-level** → row goes to quarantine and
the run continues. Both write a row to
`ops.data_quality_result`? **No** — `AGENTS.md` forbids
cross-writing. Phase 2 results go to `ml.data_quality_result` in the
phase-2 Postgres, same column shape, so the reviewer sees a familiar table.

---

## 5. Label table plan (`src/ml/label_pipeline.py`)

Schema exactly as phase-04.md:42-44 requires:

| column | type | note |
|---|---|---|
| `ticker` | text | join key, matches the Feast entity |
| `event_timestamp` | timestamptz | point-in-time boundary for phase-05 PIT joins |
| `label` | int | 0/1 distress proxy |
| `label_version` | text | e.g. `altman-z-v1`; bumped when the rule changes |
| `created_ts` | timestamptz | write time, for dedupe-by-latest |
| `training_eligible` | bool | false for financial-sector rows and rows with null z-score |

Plus one non-negotiable extra: a `PROXY_LABEL_NOTICE` module constant and a
`label_source='proxy_not_ground_truth'` column, because phase-04.md:44 requires
proxy labels be explicitly marked non-ground-truth. The rubric text asks for
"2 cột id và label" — we satisfy that superset; the evidence markdown shows the
`ticker`+`label` projection joined to a feature table, which is literally the
screenshot the rubric asks for.

Reuses `src.transforms.compute_distress_labels.compute_labels`
(`src/transforms/compute_distress_labels.py:279`) — **read-only import, no
edit.** `training_eligible=false` follows the existing null-label path
(`compute_distress_labels.py:221`, financial-sector exclusion).

Written to two places, idempotently:
1. Parquet, MinIO `phase2/offline/labels/label_version={v}/` — overwrite the
   affected partition only (AGENTS.md Silver/Gold rule).
2. `ml.label_table`, `INSERT ... ON CONFLICT (ticker, event_timestamp,
   label_version) DO UPDATE` keeping the latest `created_ts`.

---

## 6. Drift scenario plan (`src/drift/`)

### `src/drift/generator_config.py`
Frozen dataclasses mirroring `src/generator/config.py`'s style (validate() on
each, strict unknown-key rejection via a local `_typed`, `load_drift_config(path,
scenario)`); **do not import from `src/generator/config.py`'s private helpers** —
copying ~20 lines of `_typed`/`_validate_rate` is cheaper than coupling Phase 2
to a Phase 1 private API. (Judgment call against DRY; noted deliberately.)

```
DriftScenario: name, seed, start_quarter, affected_fraction,
               feature_shifts: dict[str, ShiftSpec], expected_direction, threshold
ShiftSpec:     mode ('multiplicative'|'additive'|'variance'), magnitude, ramp
DriftConfig:   schema_version, scenarios: dict[str, DriftScenario]
```

### Two scenarios in `configs/drift-config.yaml` (as implemented, slice 4A)
1. **`financial_deterioration`** — from `start_quarter` onward, on
   `affected_fraction` of tickers: `total_liabilities` ×1.60,
   `retained_earnings` ×0.70, `ebit` ×0.70, `net_income` additive shift down.
   `expected_direction: increase` on `debt_to_asset` (population mean),
   threshold 0.10.
2. **`market_stress`** — `close_price` ×1.60, `volume` ×1.40, on the affected
   subgroup only. **Deviation from the original design above**: the generator's
   offline output is a single snapshot per ticker with no intraday/rolling
   time series, so there is no `volatility_30d` to shift or observe. The
   implemented proxy is the **cross-sectional stdev of `close_price` across
   all tickers** — widening the gap between the affected and unaffected
   subgroups raises this stdev. `expected_direction: increase` on that stdev,
   threshold 0.25. See `configs/drift-config.yaml`'s header comment.

### `src/drift/generator.py`
- `apply_drift(rows, scenario) -> DriftedData` — pure; `random.Random(scenario.seed)`
  only, no global RNG, so two runs are byte-identical.
- `build_drift_report(before, after, scenario) -> dict` — per-feature
  before/after mean, std, p50, p95, PSI, observed direction, configured
  direction, threshold, `passed: bool`.
- `render_drift_report_markdown(report) -> str` — mirrors the style of
  `src/generator/profile.py:104` (`render_profile_html`).
- Writes `outputs/phase2/drift/{scenario}/{run_id}/{report.json, report.md}`.

Validation (phase-04.md:91): "compare generated drift against the configured
direction and threshold" = assert `report['passed']` and
`report['observed_direction'] == scenario.expected_direction`.

---

## 7. dags/phase2/ wrapper plan

Five DAG files. Every one obeys these rules, each of which is a test in §9:

- Module top level contains **only** imports of `airflow`, `datetime`, `os`, and
  a single `from src...import` of the *callable*, plus the `DAG(...)` object and
  operator wiring. No client construction, no config load, no filesystem or
  network access at import time.
- Business logic is a one-line lambda-free call: `PythonOperator(python_callable=
  src.llm.rag_pipeline.run_ingestion, op_kwargs={...})`.
- Connection strings come from Airflow Variables/env read *inside* the callable.

| file | dag_id | tasks |
|---|---|---|
| `phase2_rag_ingest.py` | `phase2_rag_ingest` | fetch → parse_chunk → dedupe → govern → embed_write → emit_lineage |
| `phase2_feature_materialize.py` | `phase2_feature_materialize` | feast_apply → materialize_incremental → record_registry_revision |
| `phase2_stream_feature_offline.py` | `phase2_stream_feature_offline` | consume → transform → push_offline → checkpoint |
| `phase2_stream_feature_online.py` | `phase2_stream_feature_online` | consume → transform → push_online → checkpoint |
| `phase2_label_drift_build.py` | `phase2_label_drift_build` | generate → apply_drift → drift_report → build_labels → publish |

New dag_ids all carry the `phase2_` prefix; no existing dag_id or task_id in
`dags/*.py` is renamed or removed (verified: 15 Phase 1 DAG files present, none
named `phase2_*`).

`dags/phase2/phase2_drift_monitoring.py` is pinned by ML row 91 but belongs to
phase-06 — **out of scope here**, listed only so nobody creates it twice.

---

## 8. docker-compose.yml plan (append only)

Three new services appended after `flink-taskmanager`, before the top-level
`volumes:` key (docker-compose.yml:214). No existing block edited.

```
  phase2-redis:                    # Feast online store, mirrors in-cluster Redis
    image: redis:7-alpine
    command: redis-server --save "" --appendonly no
    ports: ["${PHASE2_REDIS_HOST_PORT:-6380}:6379"]
    healthcheck: redis-cli ping | grep PONG, 5s/5/10s
    profiles: ["phase2"]

  phase2-postgres:                 # PGVector + ml; NOT the Phase 1 postgres
    image: pgvector/pgvector:pg16
    environment: POSTGRES_DB=ml, POSTGRES_USER/PASSWORD from ${PHASE2_PG_*}
    ports: ["${PHASE2_PG_HOST_PORT:-5433}:5432"]
    volumes:
      - ./sql/init_ml_metadata.sql:/docker-entrypoint-initdb.d/01_init_ml_metadata.sql:ro
      - phase2-pgdata:/var/lib/postgresql/data
    healthcheck: pg_isready -U $USER -d ml, 5s/10/10s
    profiles: ["phase2"]

volumes:
  phase2-pgdata:                   # added under the existing volumes: key
```

Port choices avoid the Phase 1 `postgres` host port (5432, docker-compose.yml:9)
and any existing binding. `profiles: ["phase2"]` means plain `docker compose up`
behaviour is byte-identical to today — same guard the Flink profile already uses
(AGENTS.md). `docker compose config` must still pass (AGENTS.md verify command).

Optional third service — **defer unless needed**: a `phase2-feast-ui` container.
YAGNI; the registry file is the evidence.

---

## 9. Dependency additions (`.venv-phase2` only, never `.venv`)

Verified present in `.venv-phase2`: `feast==0.65.0`, `SQLAlchemy 2.0.51`,
`pandas`, `pyarrow`, `tenacity 8.5.0`, `pydantic 2.13.4`, `numpy`.

Verified missing, to install:

| package | why |
|---|---|
| `redis>=5` | Feast redis online store driver |
| `psycopg[binary]>=3.2` | PGVector writes; same major as `.venv` (pyproject.toml:29) so code is portable between venvs |
| `pgvector>=0.3` | psycopg3 vector type adapter |
| `minio>=7.2` | matches Phase 1's client (`src/io/minio_publish.py:11`); reuse, do not add boto3 |
| `boto3` | **only if** Feast's file/s3 registry path demands it — check first, do not install speculatively |
| `sentence-transformers` + CPU torch | only if D5/Q1 is confirmed; ~2 GB, install last, image-only if local disk is tight |

Not needed: any DataHub SDK. `src/governance/datahub_graphql.py:5-7` uses
stdlib `urllib` against the GraphQL endpoint — reuse that.

Install command shape:
`.venv-phase2/bin/pip install "redis>=5" "psycopg[binary]>=3.2" "pgvector>=0.3" "minio>=7.2"`
Record resolved versions into the evidence `versions:` field.

---

## 10. Test plan (tests written FIRST, per phase-04.md:59)

New directory `tests/phase2/pipelines/` (distinct from
`tests/phase2/requirements/`, which is generated). Files, and what each pins:

| test file | pins | fast loop? |
|---|---|---|
| `test_drift_config.py` | drift config loads, rejects unknown keys, rejects out-of-range magnitudes, both scenarios present | yes |
| `test_drift_generator.py` | same seed → identical output twice (byte hash); observed direction matches configured; PSI crosses threshold; unaffected fraction unchanged | yes |
| `test_label_pipeline.py` | exact 7-column schema; financial-sector rows `training_eligible=false`; label_version stamped; running build twice yields identical rows (idempotency) | yes |
| `test_rag_chunking.py` | chunk size/overlap bounds; sentence-boundary preference; `content_hash` stable under whitespace normalization; changes when `parser_version` changes | yes |
| `test_rag_dedup.py` | reprocessing an unchanged doc yields zero new chunks; changed doc yields only changed chunks; new embedding_version yields a full new set | yes |
| `test_rag_metadata_contract.py` | every emitted chunk carries all nine fields non-empty; `assert_metadata_complete` raises on each field individually (parametrized) | yes |
| `test_data_governance.py` | license allowlist; PII regexes (positive + negative per type); rate limiter spacing; retry policy retries 5xx and not 4xx; quarantine record shape | yes |
| `test_feast_definitions_ttl.py` | every FeatureView has non-null TTL; TTL values equal the documented table in §3.2; every source declares `event_timestamp_column`; each view has a rationale docstring | yes — **must not import feast** |
| `test_phase2_dags_import.py` | each `dags/phase2/*.py` imports with no side effects (monkeypatched socket/`open` guard, mirroring `tests/test_dags_05_smoke.py`); dag_id prefix; no Phase 1 dag_id collision | yes |
| `test_workflows_phase2.py` | the four workflow files exist, parse as YAML, `phase2-ci.yaml` is `workflow_call`, three callers reference it, `ci.yml` unchanged (content hash pinned) | yes |
| `tests/phase2/pipelines/test_pgvector_store.py` | real `psycopg` against the ephemeral cluster; upsert idempotency; unique constraint; quarantine write. Marked `postgres` + `slow`, reusing the `pytest_collection_modifyitems` marker pattern verified at `tests/phase2/product/conftest.py:29` | no (postgres marker) |
| `tests/phase2/pipelines/test_feast_smoke.py` | `feast plan/apply/materialize` against a disposable local registry + fake redis. Marked `slow` and **skipped unless `feast` importable** — it cannot run in `.venv` | no |

`test_feast_definitions_ttl.py` is the trickiest and the most valuable: it must
assert TTLs without importing feast in `.venv`. Approach: keep the TTL table as
a plain module-level `dict[str, timedelta]` constant `FEATURE_VIEW_TTL` in
`src/ml/feast/feature_definitions.py` *above* any feast import (which is lazy per
D4), and have the FeatureView construction read from that dict. The test imports
only the constant. This is the pattern that makes D4 workable everywhere.

Order of work per AGENTS.md "narrowest useful test first": write the file, run
`.venv/bin/python -m pytest tests/phase2/pipelines/test_X.py -k <case>`, then
broaden to `pytest tests/phase2/pipelines`, then the full
`scripts/run_stage1_quality_gates.py` before declaring a slice done.

Register no new pytest markers — `postgres` and `slow` already exist
(pyproject.toml:52-56), and `--strict-markers` is on.

---

## 11. Evidence markdown plan

Create `docs/phase2/evidence/llm/` and write one file per rubric_id at the
matrix's exact `evidence_path`. Contract verified at
`tests/phase2/requirements/conftest.py:26-36` and
`scripts/audit_phase2_evidence.py:_audit_executed` — nine keys, all non-empty,
`rubric_id` mentioned in the body, `artifact_path` must be a real file.

Required frontmatter keys (parsed as `key: value` lines anywhere in the file,
conftest.py:52): `rubric_id`, `execution_timestamp` (ISO-8601),
`source_sha` (40-hex), `gitops_sha` (40-hex), `versions`, `command`,
`expected_result`, `actual_result`, `redaction_status`.

Files to create:

| evidence_path | proves | `command` to record |
|---|---|---|
| `docs/phase2/evidence/llm/LLM-rag-rag-data-pipeline.md` | RAG DAG ran; chunks in PGVector; DataHub lineage | `airflow dags test phase2_rag_ingest <ds>` + row-count SQL |
| `docs/phase2/evidence/llm/LLM-rag-m-b-o-data-governance-cho-pipe.md` | licensing/PII/DLQ/rate-limit/retry all exercised | `.venv/bin/python -m pytest tests/phase2/pipelines/test_data_governance.py -q` + a quarantine-row SQL dump |
| `docs/phase2/evidence/llm/LLM-improve-the-data-generato-simulate-data-drift.md` | two scenarios, deterministic seed, before/after report | `.venv/bin/python scripts/run_phase2_drift_report.py --scenario financial_deterioration` (twice, same digest) |
| `docs/phase2/evidence/llm/LLM-improve-the-data-generato-using-generator-configuration.md` | config-driven generation | same script with `--scenario market_stress` + config dump |
| `docs/phase2/evidence/llm/LLM-improve-the-data-generato-t-o-b-ng-label-c-2-c-t-id-v-la.md` | label table + join-to-feature screenshot | label build command + the `ticker,label` ⋈ feature SQL |
| `docs/phase2/evidence/llm/LLM-ci-cd-job-1.md` | offline stream-feature workflow run | `gh run list --workflow phase2-stream-feature-offline.yaml` + run URL |
| `docs/phase2/evidence/llm/LLM-ci-cd-job-2.md` | online stream-feature workflow run | same for `phase2-stream-feature-online.yaml` |

Optional (ML rows, free because the artifacts exist): the four
`docs/phase2/evidence/ml/ML-feature-store-*.md` files. Write them only if time
remains — LLM-only scope does not score them.

`evidence_type` stays `design_only` in the CSV until phase-08 flips it to
`executed`; that flip is phase-08's job, not this phase's. Do **not** edit
`source_digest` columns.

`source_sha` = the commit that produced the run (`git rev-parse HEAD`),
`gitops_sha` = the same in `../financial-distress-gitops` (checkout verified
present, currently `7631f720`).

---

## 12. GitHub Actions plan (no YAML yet)

### `.github/workflows/phase2-ci.yaml` — reusable template
- `on: workflow_call` with inputs `pipeline_name`, `image_context`,
  `dockerfile`, `test_selector`; secrets `GHCR_TOKEN`, `GITOPS_PAT`.
- Jobs, in order:
  1. `lint` — `ruff check` + `black --check` on the pipeline's paths only.
  2. `test` — `pytest ${{ inputs.test_selector }}` in `.venv`-equivalent
     (fast loop, `-m "not slow"`; no Docker services in CI).
  3. `build` — Buildx build + push to GHCR, `outputs.digest` from
     `docker/build-push-action`.
  4. `gitops-pr` — checkout `financial-distress-gitops` with `GITOPS_PAT`,
     rewrite the pinned digest for `pipeline_name`, open a PR, output PR URL.
     Runs only on `main`/`dev` push, never on PR.
- Concurrency group per `pipeline_name` so two pushes cannot race the same
  digest file.

### Three callers
| file | `paths:` trigger | `pipeline_name` | `test_selector` |
|---|---|---|---|
| `phase2-rag-pipeline.yaml` | `src/llm/**`, `configs/rag-sources.yaml`, `dags/phase2/phase2_rag_ingest.py` | `rag-pipeline` | `tests/phase2/pipelines -k "rag or governance"` |
| `phase2-stream-feature-offline.yaml` | `src/ml/feast/offline_job.py`, `src/ml/feast/feature_definitions.py`, `dags/phase2/phase2_stream_feature_offline.py` | `stream-feature-offline` | `tests/phase2/pipelines -k "feast or ttl"` |
| `phase2-stream-feature-online.yaml` | `src/ml/feast/online_job.py`, `src/ml/feast/feature_definitions.py`, `dags/phase2/phase2_stream_feature_online.py` | `stream-feature-online` | same |

`ci.yml` is not modified and its `paths` are not narrowed — Phase 1 keeps
running on every push.

---

## 13. Recommended slicing (the one-pass scope, four review gates)

The user's confirmed scope is all 9 steps. That scope is correct, but **it will
not survive one uninterrupted coding burst** — it spans ~30 new files, two new
containers, a new Python env, and four CI files. Recommend four sequential
slices, each independently green against
`.venv/bin/python scripts/run_stage1_quality_gates.py`, each its own commit and
review gate. Same total scope, four safe stopping points.

| Slice | Steps | Files owned (no overlap with any other slice) | Blocked by |
|---:|---|---|---|
| **4A — infra + data** | 1(part), 2 | `docker-compose.yml` (append), `sql/init_ml_metadata.sql`, `configs/drift-config.yaml`, `src/drift/**`, `src/ml/label_pipeline.py`, `tests/phase2/pipelines/test_drift_*.py`, `test_label_pipeline.py`, `scripts/run_phase2_drift_report.py` | nothing |
| **4B — RAG** | 1(part), 3, 7 | `configs/rag-sources.yaml`, `src/llm/**`, `tests/phase2/pipelines/test_rag_*.py`, `test_data_governance.py`, `test_pgvector_store.py` | 4A (needs `phase2-postgres` + `ml`) |
| **4C — Feast + jobs + DAGs** | 1(part), 4, 5, 6 | `src/ml/feast/**`, `feature_repo/**`, `dags/phase2/**`, `tests/phase2/pipelines/test_feast_*.py`, `test_phase2_dags_import.py` | 4A (redis), 4B (rag feature view refs) |
| **4D — CI + lineage + evidence** | 8, 9 | `.github/workflows/phase2-*.yaml`, `src/governance/phase2_lineage.py`, `configs/phase2-governance.yaml`, `docs/phase2/evidence/llm/*.md`, `tests/phase2/pipelines/test_workflows_phase2.py` | 4A–4C (evidence needs real runs) |

**Parallelization note:** 4A and 4B touch disjoint files *except* that 4B needs
4A's `sql/init_ml_metadata.sql`. If the orchestrator wants parallelism, split
`init_ml_metadata.sql` out as a zero-th slice owned by neither, then 4A and 4B
can run concurrently. 4C and 4D are strictly sequential after them.

**Do the Feast star-re-export spike (§3.4) at the very start of 4C, timeboxed to
30 minutes.** It is the only unknown that can force a layout change, and finding
out late costs the whole slice.

---

## 14. Risk register (carried from phase-04.md:105-114, extended)

| Risk | L×I | Mitigation | Rollback |
|---|---|---|---|
| Module-level `feast`/`redis` import breaks the Phase 1 gate (D4) | **High × High** | Lazy imports enforced by `test_feast_definitions_ttl.py` running in `.venv`; run `scripts/run_stage1_quality_gates.py` at the end of every slice | Move the import inside the function; one-line fix, caught in minutes |
| Feast 0.65 rejects star-re-exported definitions (§3.4) | Med × Med | 30-min spike at the head of 4C before anything else in the slice | Physically relocate definitions into `feature_repo/`; pinned file imports from there |
| Feast dependency conflicts (phase-04.md:107) | Med × Med | `.venv-phase2` isolation; jobs run from a container image, not the host env | Pin the resolved set; rebuild the image from the recorded digest |
| RAG source unavailable / rate-limited (phase-04.md:111) | Med × High | Cache-first `fetch_documents`; committed fixture corpus so evidence runs need no network — mirrors the existing `vnstock_fixture_adapter` precedent | Run against fixtures only; note the substitution in the evidence `scenario:` line |
| pgvector image / `vector` extension unavailable locally | Low × High | `pgvector/pgvector:pg16` ships the extension; healthcheck + an init-SQL `CREATE EXTENSION` that fails loudly | Fall back to `float8[]` + brute-force cosine for local tests only; note the divergence in ADR-005 |
| New compose services change plain `docker compose up` behaviour | Low × High | `profiles: ["phase2"]` on both; `docker compose config` in the gate | Remove the two blocks; nothing else references them |
| Skipping the offline store definition (phase-04.md:108) | — | Not negotiable. Every FeatureView declares its offline source and `event_timestamp_column` in 4C | n/a |
| Embedding model bloats the repo/venv (D5) | Med × Med | Hash embedder in CI; real model only in the image and the evidence run | Ship the hash embedder and record it honestly in `embedding_model` — evidence would be weaker but not false |
| Evidence files written before the runs happen | Med × High | Write evidence **last** (4D), from real command output. `--require-executed` rejects placeholder values (`audit_phase2_evidence.py:695`) | Delete the file; the contract test reverts to skipping |
| GitOps PR job leaks a token or races | Low × High | `GITOPS_PAT` as a secret, never echoed; per-pipeline concurrency group; PR-only, never direct push | Revoke the PAT; close the PR |

Phase rollback (phase-04.md:113): disable the five `phase2_*` DAGs, restore the
previous Feast registry object from MinIO versioning, `docker compose down`
the `phase2` profile. Phase 1 datasets are never written by any of this.

---

## 15. Definition of done

- [ ] `.venv/bin/python scripts/run_stage1_quality_gates.py` passes (the AGENTS.md gate).
- [ ] `.venv/bin/python -m pytest tests/phase2/pipelines` green, and green again on a second run with identical output.
- [ ] `docker compose config` passes; plain `docker compose up` starts the same services as before.
- [ ] `feast apply` + `materialize_incremental` succeed twice against a disposable store with identical online values (success criterion 2, phase-04.md:98).
- [ ] Re-running `phase2_rag_ingest` on an unchanged corpus writes 0 new rows to `ml.rag_chunk` (criterion 1, phase-04.md:97).
- [ ] Both drift scenarios reproduce byte-identical reports across two runs and match their configured direction (criterion 4, phase-04.md:100).
- [ ] `SELECT * FROM ml.rag_chunk LIMIT 1` shows all nine metadata fields populated (criterion 5, phase-04.md:101).
- [ ] All four workflow files exist; the three callers each show one successful run.
- [ ] Seven LLM evidence files exist and `pytest tests/phase2/requirements -k "rag or data_generato or ci-cd"` no longer skips.
- [ ] `scripts/audit_phase2_evidence.py --matrix-only --strict` passes.

---

## Unresolved questions

**Q1 (blocking 4B).** Embedding backend — confirm D5: `all-MiniLM-L6-v2` (384-dim,
`sentence-transformers` + CPU torch ≈ 2 GB, installed in `.venv-phase2` and the
image) for real runs, with a deterministic 384-dim hash embedder for the `.venv`
fast loop and CI. Alternative: call an OpenAI-compatible embeddings endpoint on
the vLLM-CPU server phase-06 stands up — but that server does not exist yet, so
phase-04 would be blocked on phase-06. Recommend D5 as written.

**Q2 (non-blocking).** `phase-04.md:88` names Hypothesis property tests, but
`hypothesis` is not a repo dependency. Recommend seeded parametrized tests
instead (the generator is already seed-deterministic) and amending that line in
`phase-04.md`. Confirm, or approve adding `hypothesis` to the `dev` extra.

**Q3 (non-blocking).** ML-track evidence files (`ML-feature-store-*`,
`ML-ci-cd-job-*`, `ML-improve-the-data-generato-*`) become nearly free once the
artifacts exist, but the submission is LLM-only per ADR-010. Write them, or
leave them for a possible ML retrofit in phase-05?

**Q4 (non-blocking).** `docs/phase2/architecture.md` never enumerates the RAG
"trusted sources" (only `src/llm/contracts.py:21` says "Vnstock news + PDFs").
`configs/rag-sources.yaml` needs concrete entries. Proposal: 2–3 Vnstock company
news feeds + a small committed corpus of Vietnamese annual-report PDF extracts
under `tests/phase2/fixtures/rag_corpus/`, each with an explicit license and
access class. Confirm the source list before 4B.

**Q5 (non-blocking).** `phase-04.md` still carries the pre-GKE prose that Session
3's action-item list flagged for sweep (plan.md:307). This supplement supersedes
it on the points above, but someone should do that sweep so the two files do not
disagree in the reviewer's hands.
