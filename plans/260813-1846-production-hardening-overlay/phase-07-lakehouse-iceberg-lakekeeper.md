---
phase: 7
title: "Lakehouse: Iceberg + Lakekeeper catalog"
status: cancelled
priority: P2
effort: "2d"
dependencies: [4]
---

> **CANCELLED 2026-08-14 (user decision, ML track dropped).** Zero LLM rubric rows reference Iceberg or Lakekeeper (measured 2026-08-14). Closed only ML rows (~2 pts).
> Body below is kept as the historical record of what was planned/built; nothing further is executed against it. See `plan.md` Overview.

# Phase 7: Lakehouse — Iceberg tables + Lakekeeper REST catalog

## Overview

Give the platform data plane real table semantics — ACID commits, snapshot
isolation, time travel, schema evolution — behind an Iceberg REST catalog, and use
snapshots as the mechanism for incremental training-data versioning.

Additive: Phase 1's Parquet-on-MinIO layout is untouched and keeps serving the
already-captured platform .vidence.

## Requirements

- Functional: platform .ables are Iceberg tables registered in a REST catalog;
  a training read resolves a specific snapshot ID and can be replayed exactly;
  schema evolution is demonstrated without rewriting data.
- Non-functional: the catalog runs in under ~1.5 vCPU including its metadata
  database.

## Architecture

Iceberg has settled the table-format question; the live decision in 2026 is the
**catalog**, which is where governance, auditability and lock-in actually sit.
Three options were considered:

| Catalog | Verdict |
|---|---|
| Apache Polaris | Apache TLP since Feb 2026, aimed at multi-engine multi-cloud governance. More platform than this project needs, heavier footprint. |
| Nessie | The only real option for Git-style data branching. Genuine capability, but this plan has no branch-per-environment data workflow to justify it. |
| **Lakekeeper** | Rust, dependency-light, Kubernetes-native, strong authorization. Chosen: cleanest fit at this vCPU budget. |

Because engines talk the Iceberg **REST protocol**, the catalog choice is
reversible — pointing Spark/DuckDB/Flink at a different REST endpoint is a config
change, not a migration. That reversibility is what makes picking the lean option
low-risk, and it belongs in the ADR.

**Versioning mechanism.** The ML rubric asks for incremental data versioning on
every training pull. Iceberg snapshots provide it natively: a training run records
the snapshot ID it read, and re-running against that ID reproduces the exact
input. This is strictly better than the reference repo's Hudi-based approach for
our purpose because it needs no extra engine — the snapshot ID drops straight into
the existing reproducibility manifest alongside `source_sha` and image digest.

## Related Code Files

GitOps repo:

- Create: `platform/data/lakekeeper.yaml`, `platform/data/lakekeeper-postgres.yaml`
- Create: `argocd/applications/platform-lakehouse.yaml`
- Modify: `platform/data/network-policies.yaml`

Source repo:

- Create: `src/iceberg/__init__.py`, `catalog.py`, `tables.py`, `snapshots.py`
- Create: `tests/platform/pipelines/test_lakehouse_catalog.py`
- Create: `docs/platform/adr/adr-012-iceberg-catalog-choice.md`
- Modify: `requirements-phase2.txt` — `pyiceberg`
- Modify: `src/ml/reproducibility_manifest.py` — record snapshot ID (new file, see phase 10)

Do **not** modify `src/transforms/`, `src/catalog/` or `src/collectors/` — those
are protected platform .aths. The new `src/iceberg/` package is the Phase 2
namespace.

**Do not put this code in `src/lakehouse/`.** That package already exists and is
Phase 1: `compaction.py` is the W19 lakehouse-compaction spine called by
`dags/06_pyspark_silver_to_gold.py` and `dags/dp1_bronze_ingest.py`, and it
produces the R25/R26 evidence in `docs/evidence/lakehouse_compaction_benchmark.json`.
It sits outside `PHASE1_PROTECTED` only because the protection list has a gap —
see `plans/reports/scout-260813-2117-repo-layout-audit.md` finding H0, which
phase 1 closes by adding it to the list. platform .ceberg work stays in its own
package.

## Implementation Steps

1. Deploy Lakekeeper plus its metadata Postgres via Argo CD, with MinIO/GCS as the
   warehouse backend. Pin the chart version.
2. Create `src/iceberg/catalog.py` wrapping `pyiceberg`'s REST catalog client
   with the project's connection contract; keep credentials sourced from the
   ESO-materialized secret from phase 6.
3. Define the platform .ceberg tables — feature tables, the label table, and the
   drift-reference table — with explicit partitioning and the event/creation
   timestamp columns the schema rubric already requires.
4. Write `src/iceberg/snapshots.py`: resolve current snapshot ID, read as-of a
   snapshot, and diff two snapshots for row-delta reporting.
5. Demonstrate and capture three properties: an ACID concurrent-write test, a
   time-travel read reproducing an earlier result, and an additive schema
   evolution (add a column) with old readers unaffected.
6. Wire the snapshot ID into the reproducibility manifest contract so phase 10's
   training runs record it automatically.
7. Write ADR-012 covering the catalog comparison and the REST-protocol
   reversibility argument.

## Verification

```bash
.venv/bin/python -m pytest tests/platform/pipelines -k lakehouse
.venv/bin/python -c "from src.lakehouse.catalog import load_catalog; print(load_catalog().list_tables('phase2'))"
kubectl get pods -l app.kubernetes.io/name=lakekeeper
scripts/validate-gitops.sh   # in the gitops repo
```

## Success Criteria

- [ ] Lakekeeper -> queried over the Iceberg REST protocol -> lists the registered platform .ables
- [ ] Two concurrent writers -> commit to one table -> both succeed or one retries cleanly; no torn state
- [ ] Time-travel read -> given a recorded snapshot ID -> returns byte-identical results to the original read
- [ ] Schema evolution -> column added -> existing readers continue without error, no data rewrite
- [ ] Snapshot ID -> appears in the reproducibility manifest contract
- [ ] Strict `--track LLM` gate -> unchanged PASS 100/100

## ML rubric rows closed

- Versioning — "Mỗi lần kéo dữ liệu từ Feast về để training, cần version lại DATA
  theo cơ chế incremental" (2 pts)

Also the substrate for phase 10's training reproducibility and phase 8's CDC sink.

## Risk Assessment

- **Lakekeeper is younger than Polaris and Nessie.** Mitigated structurally: the
  REST protocol is the contract, so replacing the catalog is a config change. Say
  this explicitly in ADR-012 rather than pretending the maturity gap is absent.
- **Adding an Iceberg path alongside Parquet risks two sources of truth.** Scope
  the boundary explicitly in the ADR: platform .arquet is frozen evidence; Iceberg
  is platform data.
- **`pyiceberg` version drift against the catalog's REST implementation.** Pin
  both and assert compatibility in the test suite.
