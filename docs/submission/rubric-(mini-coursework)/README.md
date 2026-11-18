---
title: "Mini-Coursework Submission Index"
date: 2026-08-14
status: active
scope: "docs/submission/rubric-(mini-coursework)/**"
---

# Mini-Coursework (the platform) — Reviewer Index

Nine narrative docs cover the the platform local-first lakehouse rubric, sourced
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

## Absorbed source docs

Each narrative doc above absorbs one or more of these older the platform docs —
listed here so they stay reachable by link (the root README's old giant
"Documentation" link list was replaced by this index in Phase 6; these
survive as retire candidates per `docs/project-file-map.md`, not deleted):

| Absorbed into | Source docs |
|---|---|
| `data_generator.md` | [`01_data_generator.md`](../../01_data_generator.md), [`data-generator.md`](../../data-generator.md) |
| `schema_design.md` | [`architecture/data-model.md`](../../architecture/data-model.md), [`architecture/data-model.md`](../../architecture/data-model.md) |
| `processing_jobs.md` / `data_storage.md` | [`05_storage_optimization.md`](../../05_storage_optimization.md), [`spark-and-storage-optimization.md`](../../spark-and-storage-optimization.md), [`flink-stream-processing.md`](../../flink-stream-processing.md) |
| `data_governance.md` | [`07_data_contracts.md`](../../07_data_contracts.md), [`data-governance.md`](../../data-governance.md) |
| `engineering_fundamentals.md` | [`08_docker_optimization.md`](../../08_docker_optimization.md), [`docker-optimization.md`](../../docker-optimization.md) |
| `novel_ideas.md` | [`09_novel_idea_1.md`](../../09_novel_idea_1.md), [`10_novel_idea_2.md`](../../10_novel_idea_2.md), [`novel-idea-pit-leakage-guard.md`](../../novel-idea-pit-leakage-guard.md), [`novel-idea-evidence-manifest.md`](../../novel-idea-evidence-manifest.md) |
| `data_pipeline_orchestration.md` | [`data-pipeline-orchestration.md`](../../data-pipeline-orchestration.md) |
| `readme_business_domain.md` | [`architecture/lakehouse.md`](../../architecture/lakehouse.md) |

Also still reachable, not absorbed by a narrative doc: [`docs/idea.md`](../../idea.md) (Phase 0 problem discovery), [`docs/coursework_proposal.md`](../../coursework_proposal.md), [`docs/11_rubric_completion_spec.md`](../../11_rubric_completion_spec.md), [`docs/evidence-index.md`](../../evidence-index.md), and [`docs/ui-screenshot-runbook.md`](../../ui-screenshot-runbook.md).

## Related

- [Docs style contract](../../docs-style-contract.md)
- [LLM-track submission index](<../rubric-final-coursework-(final-llm)/README.md>)
- [ML-track deferred index](../ml-track-deferred.md)
- [Mini-coursework spec (authority)](../../mini_coursework.md)
- [Rubric points sheet](<../../Coursework Tracking (Public) - rubic (mini-coursework).csv>)
