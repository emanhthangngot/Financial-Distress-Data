---
phase: 5
title: "Mini-coursework narrative docs and ML deferred index"
status: done
priority: P1
effort: "1d"
dependencies: [1, 2, 3]
---

# Phase 5: Mini-coursework narrative docs and ML deferred index

## Overview

Phase 1 work is real and verified but is currently spread over ~28 loose
`docs/*.md` files with no reviewer path through them. Fold it into the same
narrative format under the mini-coursework rubric tab, and add the ML-deferred
index so a grader never meets an unexplained gap.

## Requirements

- Functional: 9 mini-coursework rubric areas, one narrative doc each, same
  skeleton as Phase 4.
- Functional: one ML-deferred index covering all 19 ML rubric areas, each with
  an explicit status (`deferred` / `design-only` / `covered by LLM track`) and a
  one-line reason.
- Functional: existing Phase 1 docs are absorbed or linked, not duplicated —
  DRY applies to docs too.
- Non-functional: no Phase 1 pipeline behavior changes; docs only.

## Architecture

```text
docs/submission/rubric-(mini-coursework)/
  README.md                        index: area -> doc -> proof -> point
  readme_business_domain.md        the README row itself
  engineering_fundamentals.md      Docker, Compose, multi-stage, image size
  data_generator.md                skew, cardinality, schema evolution, dupes,
                                   burst/late events, config, raw storage
  processing_jobs.md               PySpark offline, Flink streaming, windowing,
                                   optimization evidence (baseline vs optimized)
  data_storage.md                  lakehouse compaction/partitioning, DuckDB index
  data_pipeline_orchestration.md   Airflow DP1/DP2/DP3, connections, variables
  data_governance.md               lineage, validation, data contracts
  schema_design.md                 zone schemas, SCD2, timestamps, naming
  novel_ideas.md                   PIT leakage guard + the second novel idea

docs/submission/ml-track-deferred.md
  19 ML rubric areas x {status, reason, nearest LLM-track equivalent}
```

Source docs to absorb (each becomes either a narrative doc's body or a link
target, never both):

```text
01_data_generator.md / data-generator.md      -> data_generator.md
02_schema_design.md / schema-design.md        -> schema_design.md
05_storage_optimization.md,
  spark-and-storage-optimization.md           -> processing_jobs + data_storage
07_data_contracts.md, data-governance.md      -> data_governance.md
08_docker_optimization.md,
  docker-optimization.md                      -> engineering_fundamentals.md
09_novel_idea_1.md, 10_novel_idea_2.md,
  novel-idea-pit-leakage-guard.md             -> novel_ideas.md
data-pipeline-orchestration.md                -> data_pipeline_orchestration.md
flink-stream-processing.md                    -> processing_jobs.md
```

## Related Code Files

- Create: `docs/submission/rubric-(mini-coursework)/*.md` (10 files incl. README)
- Create: `docs/submission/ml-track-deferred.md`
- Modify: the absorbed `docs/*.md` — reduced to a pointer or marked for Phase 7
  retirement; the numbered/kebab duplicate pairs collapse to one survivor each
- Read only: `docs/mini_coursework.md` (Phase 1 spec — authority),
  `docs/Coursework Tracking (Public) - rubic (mini-coursework).csv`,
  `docs/Coursework Tracking (Public) - rubic final-coursework (final - ml).csv`,
  `docs/evidence/**` (generated artifacts to cite, never to edit)

## Implementation Steps

1. Map the 9 mini-coursework rubric rows to their existing evidence in
   `docs/evidence/**` and the surviving `docs/*.md` sources. Any row without
   evidence is flagged now, not discovered during the README rewrite.
2. Write `docs/submission/rubric-(mini-coursework)/README.md` index first, same
   discipline as Phase 4.
3. Write the 9 narrative docs. Phase 1 is local-first: quote the real local
   stack (Airflow, Kafka, MinIO, DuckDB, PySpark local mode, Flink opt-in) and
   never imply cloud equivalents — `AGENTS.md` forbids the AWS framing.
4. Embed the Phase 1 lakehouse subsystem diagram (Phase 3, diagram 1) in
   `readme_business_domain.md` and the orchestration doc.
5. Use the Phase 2 captures: Airflow DAG graphs and successful runs, Kafka
   offsets, MinIO paths, DuckDB views, Flink baseline vs optimized, Spark UI
   baseline vs optimized — each with its Image note.
6. Build the before/after tables from the real benchmark JSONs already in
   `docs/evidence/` (`duckdb_index_benchmark.json`,
   `lakehouse_compaction_benchmark.json`, the Flink/Spark benchmark outputs).
   Cite the JSON path next to the table.
7. Write `docs/submission/ml-track-deferred.md`: all 19 ML areas, each with
   status and a one-line reason, plus a top paragraph stating the accepted
   scope decision (LLM track, 60 rows / 100 points) so the deferral reads as a
   decision rather than a shortfall.
8. Mark absorbed source docs for Phase 7 retirement; do not delete yet.
9. Run `check_documentation.py`; commit as
   `docs(phase1): narrative mini-coursework submission docs`.

## Success Criteria

- [ ] All 9 mini-coursework areas have a narrative doc following the contract
- [ ] Every doc cites generated evidence by path and never edits it
- [ ] Baseline/optimized tables trace to a real JSON artifact in `docs/evidence/`
- [ ] `docs/submission/ml-track-deferred.md` covers all 19 ML areas with a
      status and reason each
- [ ] No Phase 1 doc content is duplicated across two surviving files
- [ ] No cloud-equivalent framing anywhere in the Phase 1 docs
- [ ] `.venv/bin/python scripts/check_documentation.py` exits 0

## Risk Assessment

- **Risk:** absorbing 28 loose docs silently drops a rubric-relevant claim.
  **Mitigation:** step 1's explicit row→source map; Phase 7 diffs the retired
  files' claims against the surviving set before deletion.
- **Risk:** the ML-deferred index reads as an excuse.
  **Mitigation:** frame it as the accepted scope decision it is, state it once
  at the top, and give each row a concrete reason — not a repeated boilerplate.
- **Risk:** re-litigating Phase 1 technical decisions while writing them up.
  **Mitigation:** this phase is documentation-only. A discovered defect is
  logged, not fixed here.
