---
phase: 7
title: "Integrate DataHub Governance And Lineage"
status: completed
priority: P1
effort: "1 week"
dependencies: [6]
---

# Phase 7: Integrate DataHub Governance And Lineage

## Overview

Implement DataHub proof for lineage, validation, and contracts across DP1/DP2/DP3.

## Requirements

- Local reproducible DataHub deployment/profile.
- Dataset and pipeline entities for every DP input/output.
- Column/schema contracts, DQ assertions, ownership, and lineage.

## Related Code Files

- Add DataHub services or an isolated Compose profile
- Create: `src/governance/`
- Create: `configs/datahub/`
- Modify DP DAGs to emit lineage/run metadata
- Create: `docs/data-governance.md`

## Implementation Steps

1. Pin a supported DataHub quickstart/deployment approach.
2. Emit dataset metadata for source, Bronze, Silver, Gold, and feature tables.
3. Emit DP1/DP2/DP3 pipeline entities and input/output lineage.
4. Publish schema contracts and DQ assertions with run results.
5. Add deterministic ingestion/bootstrap and a health check.
6. Validate lineage graph and screenshot targets automatically where possible.

## Metadata Model

| Pipeline | Required dataset lineage | Required governance proof |
|---|---|---|
| DP1 | generator source/Kafka -> Bronze tables | Bronze contracts + validation assertion |
| DP2 | Bronze -> Silver -> Gold dims/facts/OBT | Schema contract + DQ assertions |
| DP3 | Gold facts/dims -> feature tables | Feature timestamp contract + leakage assertion |

## Task Breakdown

| ID | Task | Validation | Rubric points |
|---|---|---|---:|
| P7-T1 | Add pinned DataHub governance profile and health checks | Fresh bootstrap test | - |
| P7-T2 | Emit dataset URNs/schemas/ownership | DataHub API lookup | Shared |
| P7-T3 | Emit DP1 pipeline + lineage | Graph assertion/UI | 2 lineage |
| P7-T4 | Publish DP1 validation and contract | Assertion/contract UI | 2 validation |
| P7-T5 | Emit DP2 pipeline + lineage | Graph assertion/UI | 2 lineage |
| P7-T6 | Publish DP2 validation and contract | Assertion/contract UI | 2 validation |
| P7-T7 | Emit DP3 pipeline + lineage | Graph assertion/UI | 2 lineage |
| P7-T8 | Publish DP3 validation and contract | Assertion/contract UI | 2 validation |
| P7-T9 | Correlate Airflow/DataHub runs with manifest | Run ID query | Evidence integrity |

## Validation

```bash
docker compose --profile governance up -d
python -m pytest -q tests/integration/test_datahub_metadata.py
python scripts/verify_datahub_lineage.py --run-id <run-id> --require dp1 dp2 dp3
```

## Evidence Outputs

- Three DataHub pipeline pages with visible upstream/downstream datasets.
- Contract/schema tab for representative datasets in each pipeline.
- Assertion/validation results tied to the final run.
- One end-to-end lineage overview with explanatory caption.

## Success Criteria

- [x] DataHub API shows DP1 linked to source/Bronze datasets.
- [x] DataHub API shows DP2 linked to Bronze/Silver/Gold datasets.
- [x] DataHub API shows DP3 linked to Gold facts/feature tables.
- [x] Each representative output exposes schema, assertions, contract, and lineage.

## Risks And Rollback

DataHub is resource-heavy. Use a profile and document minimum resources; do not make unit/CI gates require the full UI stack.

## As-Built Notes

- DataHub OSS `v1.6.0` was runtime-verified with the official quickstart.
- DataHub and coursework Kafka both default to host port `9092`; run them in
  separate evidence windows or remap one service.
- Runtime proof: `docs/evidence/datahub/phase7-runtime.json`.
- UI screenshots are curated during the Phase 9 submission capture.
