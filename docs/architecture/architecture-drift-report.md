# Architecture Drift Report

Captured 2026-09-10 against `dev` at the Phase 3 contract reconciliation point.

## Purpose

List files and runtime surfaces that still describe or implement a contract different from the active v2 architecture. This is an inventory, not a silent compatibility layer. Each item names the owning phase and the required correction.

## Active drift

| Surface | Observed drift | Owner | Required correction |
|---|---|---:|---|
| `sql/schema_evidence.sql` | Active DDL still uses `TIMESTAMP` in several tables while v2 requires `TIMESTAMPTZ` with explicit UTC migration. | P2/P4 | Apply `AT TIME ZONE 'UTC'` migration and regenerate schema evidence. |
| `src/transforms/gold/fact_financial_statement.py` | Missing/unknown statement variant still has a consolidated fallback in one builder path. | P2 | Use an explicit closed enum and route unknown values to failed records. |
| `src/transforms/gold/fact_market_price.py` | Python return calculation is knowledge-time aware; Spark window parity still needs a vintage-aware implementation. | P4 | Make Spark and Python previous-close selection identical and add adversarial correction evidence. |
| `src/transforms/features/pit.py` | Feature builders currently project rows; full 4-quarter/30-day aggregate windows and completeness fields remain incomplete. | P4/P5 | Implement real as-of windows and preserve `event_timestamp`/`created_timestamp`. |
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
- Legacy image live-cluster probe: diagnostic only; not a release gate under ADR-022.
- Full repository quality gate: must be rerun after each subsequent phase changes the shared contracts.
