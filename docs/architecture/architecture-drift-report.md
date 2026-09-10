# Architecture Drift Report

Captured 2026-09-10 against the merged Phase 5/LangGraph cutover commits on `dev`.

## Purpose

List files and runtime surfaces that still describe or implement a contract different from the active v2 architecture. This is an inventory, not a silent compatibility layer. Each item names the owning phase and the required correction.

## Active drift

| Surface | Observed drift | Owner | Required correction |
|---|---|---:|---|
| `sql/schema_evidence.sql` | Active DDL still uses `TIMESTAMP` in several tables while v2 requires `TIMESTAMPTZ` with explicit UTC migration. | P2/P4 | Apply `AT TIME ZONE 'UTC'` migration and regenerate schema evidence. |
| `src/transforms/gold/fact_financial_statement.py` | Resolved: statement variants are a closed four-value enum; unknown/missing values fail closed through `failed_records`. | P2 | Keep the enum and negative-case coverage. |
| `src/transforms/gold/fact_market_price.py` | Resolved: Python and Spark previous-close selection are knowledge-time aware; Spark row identity is stable across branch recomputation. | P4 | Keep parity regression coverage. |
| `src/transforms/features/pit.py` | Resolved: feature families compute as-of windows, completeness metadata, and preserve news grain; market windows select 30 observations. | P4/P5 | Keep window regression coverage and verify live materialization when a zero-spend runtime window exists. |
| `src/ml/feast/feature_definitions.py` | Resolved locally: FileSources bind `known_from_ts` and `created_timestamp` to partitioned `feat_*` prefixes; live Postgres-to-Redis materialization remains unverified. | P5 | Run live AC-P5-3/5/7/8 only inside an approved no-spend window. |
| `src/agents/langgraph_runtime.py` / `src/agents/runtime.py` | Resolved locally: coordinator uses LangChain RunnableLambda plus bounded LangGraph fan-out, hop short-circuit, timeout, and typed failures; live multi-replica deployment remains unverified. | P8/P9 | Execute parity/evaluation and live serving evidence when provider and cluster gates pass. |
| `docs/architecture/data-model.md` | Historical v1 sections remain in the document. | P3 | Keep historical sections explicitly marked; new callers must use the v2 header and Phase 2 contract. |
| `scripts/verify_target_architecture.py` | Legacy image component list remains for historical/live-cluster inspection. | P3/P6+ | Selected inventory is now the default gate; legacy image probe remains diagnostic only. |
| `.github/workflows/*` | Workflow token references are deferred to P10 and are not part of P1 naming cutover. | P10 | Reconcile deployment labels only with the release workflow owner. |
| `/home/pearspringmind/Studying/FSDS/financial-distress-gitops` | Sibling GitOps checkout contains user changes and was not modified. | P10 | Review and reconcile in that repository explicitly; do not overwrite user work. |

## Historical reference only

The following are not active architecture requirements by themselves:

- ADR-016's original image-fidelity requirement; superseded by ADR-022.
- Legacy `company_key` references inside historical documentation.
- Applied migration filenames under `supabase/migrations/`.
- Existing evidence artifacts retained for provenance.

## Verification status

- Rubric coverage verifier: pass, 161 rows / 300 points.
- Selected architecture inventory verifier: pass.
- Full repository quality gate: pass, 376 passed / 2 xfailed; naming, rubric, architecture, and evidence gates pass.
- Feast/streaming platform contract suite in isolated `.venv-platform`: pass, 25 tests.
- Platform-only workflow suite: 33 failures in the isolated environment because its expected `platform-*.yaml` filenames are absent; this is a repository workflow-rename defect, not a cloud blocker, and is not included in the fast gate.
