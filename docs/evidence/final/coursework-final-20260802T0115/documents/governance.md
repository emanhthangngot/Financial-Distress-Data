# DataHub Governance

## Scope

DataHub 1.6.0 catalogs the source, Bronze, Silver, Gold, and offline feature
datasets produced by the three Airflow pipelines. The checked-in metadata model
is [`configs/datahub/governance.yaml`](../configs/datahub/governance.yaml).

The model contains 15 datasets with schemas and ownership, three Airflow
DataFlow/DataJob pairs, 21 input/output lineage edges, and one schema assertion,
volume assertion, and Data Contract per pipeline.

## Local Runtime

Use the official quickstart pinned to `v1.6.0` and Python 3.12:

```bash
uvx --python 3.12 --from acryl-datahub==1.6.0 \
  datahub docker quickstart --version v1.6.0
```

The quickstart binds `8080`, `9002`, `9092`, `9200`, and `3306`. The core
coursework Kafka normally owns `9092`, so stop it during the governance evidence
window:

```bash
docker stop financial-distress-data-kafka-1
curl -fsS http://localhost:8080/health
curl -fsS http://localhost:9002/
```

The DataHub UI is available at `http://localhost:9002`.

## Publish And Verify

```bash
uv run --python 3.12 --with acryl-datahub==1.6.0 \
  python scripts/sync_datahub_governance.py \
  --emit \
  --server http://localhost:8080 \
  --run-id coursework-20260730T120200-bf92b2cdf0 \
  --output docs/evidence/datahub/phase7-runtime.json
```

The command fails unless every representative output has a schema, upstream
lineage, both assertions, and a queryable Data Contract. Assertions use OSS
metadata aspects rather than the Cloud-only `AssertionsClient`; each assertion
also receives a successful `AssertionRunEvent` containing the governance
`run_id`.

| Pipeline | Inputs | Representative contract output |
|---|---|---|
| `ingest_source_to_bronze` | generator and Kafka source | `bronze.companies` |
| `build_silver_gold` | three Bronze datasets | `gold.fact_financial_statement` |
| `build_offline_features` | Gold dimension and facts | `gold.feat_company_unified` |

Runtime URNs and counts are recorded in
[`phase7-runtime.json`](evidence/datahub/phase7-runtime.json).

## Failure Semantics

- Unknown dataset references fail before connecting to GMS.
- A contract dataset outside pipeline outputs is rejected.
- Unsupported assertion field types fail instead of silently coercing.
- HTTP or GraphQL errors block evidence publication.
- Missing schema, assertions, contract, or lineage blocks a passing report.

## Restore Core Kafka

```bash
datahub docker quickstart --stop
docker start financial-distress-data-kafka-1
```
