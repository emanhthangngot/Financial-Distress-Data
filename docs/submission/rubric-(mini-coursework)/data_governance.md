---
title: "Data Governance"
date: 2026-08-14
status: active
---

# Data Governance: DataHub lineage, validation, and data contracts for all three DP pipelines

This doc proves "Data Governance": all three Airflow pipelines (DP1, DP2,
DP3) are cataloged in DataHub with schema, lineage, and a Data Contract, and
publication is blocked when governance is incomplete. It does not prove a
persistent hosted DataHub instance — this evidence uses the official local
quickstart, which competes for port 9092 with the coursework's own Kafka and
must be run in a dedicated window.

**Active deployment facts:** DataHub 1.6.0, model
`configs/datahub/governance.yaml` — 15 datasets, 3 Airflow
DataFlow/DataJob pairs, 21 lineage edges, one schema assertion + volume
assertion + Data Contract per pipeline.

## Part I — Governance model and local runtime

### 1. One representative contract output per pipeline

| Pipeline | Inputs | Representative contract output |
|---|---|---|
| `ingest_source_to_bronze` (DP1) | generator + Kafka source | `bronze.companies` |
| `build_silver_gold` (DP2) | three Bronze datasets | `gold.fact_financial_statement` |
| `build_offline_features` (DP3) | Gold dimension + facts | `gold.feat_company_unified` |

```bash
uvx --python 3.12 --from acryl-datahub==1.6.0 datahub docker quickstart --version v1.6.0
docker stop financial-distress-data-kafka-1   # coursework Kafka also uses 9092
uv run --python 3.12 --with acryl-datahub==1.6.0 python scripts/sync_datahub_governance.py \
  --emit --server http://localhost:8080 \
  --run-id coursework-20260730T120200-bf92b2cdf0 \
  --output docs/evidence/datahub/phase7-runtime.json
```

Runtime URNs and counts are recorded in
[`docs/evidence/datahub/phase7-runtime.json`](../../evidence/datahub/phase7-runtime.json).

## Part II — Failure semantics (governance is enforced, not decorative)

```text
- Unknown dataset references fail before connecting to GMS.
- A contract dataset outside pipeline outputs is rejected.
- Unsupported assertion field types fail instead of silently coercing.
- HTTP or GraphQL errors block evidence publication.
- Missing schema, assertions, contract, or lineage blocks a passing report.
```

The sync command itself fails unless every representative output has a
schema, upstream lineage, both assertions, and a queryable Data Contract —
governance is a hard gate on the evidence, not a documentation-only claim.
Assertions use OSS metadata aspects (not the Cloud-only `AssertionsClient`),
each receiving a successful `AssertionRunEvent` carrying the governance
`run_id`.

## Limitations

The DataHub quickstart binds ports `8080`, `9002`, `9092`, `9200`, `3306` —
`9092` collides with the coursework's own Kafka broker, requiring the core
stack's Kafka to be stopped for the governance evidence window and restarted
afterward (`datahub docker quickstart --stop`, then
`docker start financial-distress-data-kafka-1`). This is a real local-port
constraint, not hidden from this doc.

## References

- DataHub: https://datahubproject.io/docs/
</content>
