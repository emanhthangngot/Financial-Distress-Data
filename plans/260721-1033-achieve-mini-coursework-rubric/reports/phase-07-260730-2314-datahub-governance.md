# Phase 7 DataHub Governance Report

Status: completed

## Implemented

- Pinned and ran official DataHub OSS `v1.6.0` quickstart.
- Added a validated 15-dataset/three-pipeline governance model.
- Emitted dataset schemas, ownership, Airflow DataFlow/DataJob entities, and
  input/output lineage.
- Emitted OSS schema and volume assertion aspects with successful run events.
- Created one real Data Contract for each pipeline's representative output.
- Added strict GraphQL verification for schema, assertions, contract, and
  upstream lineage.
- Added operator runbook and failure semantics.

## Runtime Evidence

Run ID: `coursework-20260730T120200-bf92b2cdf0`

Evidence: `docs/evidence/datahub/phase7-runtime.json`

Verified: 15 datasets, three contracts, six assertions, non-empty schemas, and
upstream lineage for all three representative outputs.

## Defects Found And Corrected

1. Experimental SDK assertions require a Cloud-only package. The implementation
   now emits OSS aspects.
2. Dataset SDK URNs include `platform_instance`, while the initial lineage helper
   omitted it. All entity references now use the same URN builder.
3. DataHub 1.6 uses `lineage(input: ...)`, not `upstreamLineage`.
4. DataHub Kafka conflicts with coursework Kafka on host port `9092`; the
   evidence runbook defines separate runtime windows.

## Quality Gates

- Focused tests: `7 passed`
- Ruff governance scope: passed
- DataHub GMS health: passed
- Live emit and GraphQL read-back: passed

## Unresolved Questions

- Reviewer-facing UI screenshots remain part of the correlated Phase 9 package.
