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
| `src/transforms/features/pit.py` | Python feature builders compute as-of windows and preserve news grain; Spark materialization parity and live window output remain unverified. | P4/P5 | Keep Python regression coverage, add Spark aggregation parity, and verify live materialization in a zero-spend runtime. |
| `src/ml/feast/feature_definitions.py` | Partially resolved locally: FileSources bind `known_from_ts` and partitioned `feat_*` prefixes, but risk/unified `created_timestamp` columns and the market `volume` field require schema reconciliation before `feast apply`. | P5 | Reconcile emitted columns, run `feast apply`, and execute live materialization only inside an approved no-spend window. |
| `src/agents/langgraph_runtime.py` / `src/agents/runtime.py` | Resolved locally: coordinator uses LangChain RunnableLambda plus bounded LangGraph fan-out, hop short-circuit, timeout, and typed failures; live multi-replica deployment remains unverified. | P8/P9 | Execute parity/evaluation and live serving evidence when provider and cluster gates pass. |
| `docs/architecture/data-model.md` | Historical v1 sections remain in the document. | P3 | Keep historical sections explicitly marked; new callers must use the v2 header and Phase 2 contract. |
| `scripts/verify_target_architecture.py` | Exhaustive inventory now enumerates all 83 image components with selected/omitted status and one-line rationale; legacy image probe remains diagnostic behind `--cluster`. | P3/P6+ | Keep inventory coverage tests and add live cluster evidence when available. |
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
- Platform workflow contract suite in isolated `.venv-platform`: pass, 34 tests after aligning the verifier with the repository's phase2 workflow names.
- Exhaustive target-component coverage tests: pass, 11 tests; missing-file, invalid-owner, missing-evidence, omission-reason, and missing-component failure paths exercised.
- Phase 11 coverage/mutation thresholds: blocked; full platform collection lacks `mcp`, `psycopg`, `hypothesis`, and the asyncio marker plugin in `.venv-platform`.
