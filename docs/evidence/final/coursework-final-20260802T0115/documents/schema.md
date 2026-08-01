# Schema Design

## Zones And Naming

Physical datasets use `bronze.<noun>`, `silver.<noun>`, and Gold prefixes
`dim_`, `fact_`, `obt_`, or `feat_`. The generated reviewer database contains
three Bronze, three Silver, and nine Gold tables.

## Relationships

Gold facts and the quarterly risk OBT reference both
`dim_company.company_version_key` and `dim_date.date_key`. Stable
`company_key` identifies a company across history; `company_version_key`
identifies one SCD2 version.

## SCD Type 2

`dim_company` retains `valid_from_ts`, nullable `valid_to_ts`, and
`is_current`. The evidence fixture contains two versions for `AAA` and exactly
one current row.

## Feature Contract

Every `feat_company_*` table includes literal `event_timestamp` and
`created_ts` columns. The unified table also has `feature_event_timestamp` and a
database check enforcing it is not later than the reference event.

## Reproduction

```bash
python scripts/build_schema_evidence.py \
  --output warehouse.db \
  --report docs/evidence/schema/phase8-schema-audit.json
```

Open `warehouse.db` in DBeaver and inspect the `bronze`, `silver`, and `gold`
schemas. The generated audit records 15 tables, six foreign keys, feature
timestamp coverage, and SCD2 history.
