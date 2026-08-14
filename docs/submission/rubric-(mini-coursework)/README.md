---
title: "Mini-Coursework Submission Index"
date: 2026-08-14
status: active
scope: "docs/submission/rubric-(mini-coursework)/**"
---

# Mini-Coursework (Phase 1) — Reviewer Index

Nine narrative docs cover the Phase 1 local-first lakehouse rubric, sourced
from `docs/mini_coursework.md` (spec authority) and the rubric points sheet
`docs/Coursework Tracking (Public) - rubic (mini-coursework).csv` (200 raw
line-item points; the sheet's own footer records the reconciled total as
100). Every doc cites real `docs/evidence/**` generated artifacts and never
edits them — regenerate via the producing script instead.

## Area index

| Area | Doc | Rubric section |
|---|---|---|
| Business domain + system diagram | [`readme_business_domain.md`](./readme_business_domain.md) | README requirement |
| Engineering fundamentals | [`engineering_fundamentals.md`](./engineering_fundamentals.md) | Docker & Docker Compose |
| Data generator | [`data_generator.md`](./data_generator.md) | Implement Data Generator |
| Processing jobs | [`processing_jobs.md`](./processing_jobs.md) | Processing Jobs (Spark + Flink) |
| Data storage | [`data_storage.md`](./data_storage.md) | Data Storage |
| Data pipeline orchestration | [`data_pipeline_orchestration.md`](./data_pipeline_orchestration.md) | Data Pipeline Orchestration |
| Data governance | [`data_governance.md`](./data_governance.md) | Data Governance |
| Schema design | [`schema_design.md`](./schema_design.md) | Documentation → Schema design |
| Novel ideas | [`novel_ideas.md`](./novel_ideas.md) | Novel ideas |

## Reading order

1. `readme_business_domain.md` — orientation
2. `engineering_fundamentals.md` — Docker baseline
3. `data_generator.md` — source of all downstream data
4. `processing_jobs.md` — Spark (offline) + Flink (streaming)
5. `data_storage.md` — lakehouse/warehouse optimization
6. `data_pipeline_orchestration.md` — Airflow DP1/DP2/DP3
7. `data_governance.md` — DataHub lineage/contracts
8. `schema_design.md` — zone schemas, SCD2, naming
9. `novel_ideas.md` — PIT leakage guard + ingestion manifest

## Related

- [Docs style contract](../../docs-style-contract.md)
- LLM-track submission index: `docs/submission/rubric-final-coursework-(final-llm)/README.md` (not linked — directory name contains parentheses that break the doc-gate's link regex)
- [ML-track deferred index](../ml-track-deferred.md)
- [Mini-coursework spec (authority)](../../mini_coursework.md)
- Rubric points sheet: `docs/Coursework Tracking (Public) - rubic (mini-coursework).csv` (not linked — filename contains parentheses/spaces that break the doc-gate's link regex)
</content>
