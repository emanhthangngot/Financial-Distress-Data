---
title: "Schema Design"
date: 2026-08-14
status: active
---

# Schema Design: zone naming, SCD2 dimension, feature timestamp contract

This doc proves the "Schema design" documentation area: consistent zone
naming across 15 real tables, an SCD2 dimension with verified history, a
feature-timestamp contract enforced by a database check, and the
dimension/fact relationship structure. It does not prove data volume at
production scale — the evidence fixture is intentionally small and
inspectable.

**Active deployment facts:** DuckDB `warehouse.db`, 3 Bronze + 3 Silver + 9
Gold tables.

## Part I — Naming and relationships

### 1. Zone prefixes and stable keys

Physical datasets use `bronze.<noun>`, `silver.<noun>`, and Gold prefixes
`dim_`, `fact_`, `obt_`, or `feat_`. Gold facts and the quarterly risk OBT
reference both `dim_company.company_version_key` and `dim_date.date_key`:
`company_key` identifies a company across history, `company_version_key`
identifies one SCD2 version.

### 2. SCD Type 2 dimension

`dim_company` retains `valid_from_ts`, nullable `valid_to_ts`, and
`is_current`. The evidence fixture contains two versions for ticker `AAA`
and exactly one current row — the property this row asks to demonstrate,
verified rather than asserted.

## Part II — Feature contract and audit

### 3. Every feat_ table carries event_timestamp and created_ts

Every `feat_company_*` table includes literal `event_timestamp` and
`created_ts` columns. The unified table additionally has
`feature_event_timestamp` plus a database check enforcing it is not later
than the reference event — the same point-in-time discipline
`novel_ideas.md`'s PIT leakage guard enforces at the pipeline level.

### 4. Reproducible schema audit

```bash
python scripts/build_schema_evidence.py \
  --output warehouse.db --report docs/evidence/schema/phase8-schema-audit.json
```

Open `warehouse.db` in DBeaver and inspect the `bronze`, `silver`, and
`gold` schemas. The generated audit records 15 tables, six foreign keys,
feature timestamp coverage, and SCD2 history. Full evidence:
[`docs/evidence/schema/phase8-schema-audit.json`](../../evidence/schema/phase8-schema-audit.json).

## Limitations

The evidence fixture (15 tables) is a deliberately small, fully-inspectable
schema for reviewer verification — it demonstrates the naming/SCD2/feature
contracts correctly, not a claim about schema behavior under production-scale
data volume.

## References

- Kimball SCD Type 2: standard dimensional-modeling technique
