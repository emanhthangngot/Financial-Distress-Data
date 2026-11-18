---
title: "README Business Domain"
date: 2026-08-14
status: active
---

# README Business Domain: the row itself, plus the deployable-unit diagram

This doc proves the README requirement: a business-domain introduction and a
high-level system deployment diagram where every major component is a real
deployable unit. It does not repeat the full README — it explains what that
section covers and why the diagram is drawn the way it is.

## Part I — Business domain

The platform is a **local-first financial-distress data lakehouse** for
Vietnamese listed companies: it collects quarterly financial statements,
daily market prices, and reference data, then produces curated
Bronze/Silver/Gold tables, distress labels (Altman Z''-Score inspired), and
audit-ready evidence. Three primary users:

- **Data engineer** — owns Airflow DAGs, Kafka topics, PySpark transforms,
  MinIO layout, PostgreSQL metadata.
- **ML engineer** — consumes Gold features and `obt_company_quarter_risk`
  for the platform training/scoring/monitoring.
- **Analyst / reviewer** — opens DBeaver or DuckDB against the local
  lakehouse to validate row counts, SCD2 history, lineage, and contracts.

Full text: `README.md` §Business Domain.

## Part II — Deployable-unit diagram

The the platform lakehouse subsystem diagram (Phase 3 of this plan) draws only
real deployable units — Kafka, Airflow, Spark, MinIO, PostgreSQL, DuckDB —
never a library or SDK as a node:

```mermaid
flowchart LR
    classDef edge fill:#2b6cb0,stroke:#1a365d,color:#fff
    classDef service fill:#38a169,stroke:#22543d,color:#fff
    classDef store fill:#805ad5,stroke:#44337a,color:#fff
    classDef model fill:#d69e2e,stroke:#744210,color:#fff
    classDef result fill:#dd6b20,stroke:#7b341e,color:#fff

    GEN["Generator / Collectors<br/>src/collectors, src/generator"]:::edge
    KAFKA["Kafka KRaft<br/>docker-compose kafka"]:::store
    AIRFLOW["Airflow<br/>dags/*.py"]:::service
    SPARK["PySpark local mode<br/>src/transforms/*"]:::service
    FLINK["Flink (opt-in)<br/>flink/*, ENABLE_FLINK=1"]:::service
    MINIO["MinIO Lakehouse<br/>s3a://financial-distress-lake/"]:::store
    POSTGRES["PostgreSQL ops"]:::store
    DUCKDB["DuckDB / DBeaver<br/>sql/*.sql"]:::result

    GEN -->|"batch rows"| MINIO
    GEN -->|"event JSON"| KAFKA
    AIRFLOW -->|"DP1 ingest"| GEN
    KAFKA -->|"ordered stream"| FLINK
    FLINK -->|"windows + late/dup metrics"| MINIO
    AIRFLOW -->|"DP2 Spark submit"| SPARK
    MINIO -->|"Bronze Parquet"| SPARK
    SPARK -->|"Silver/Gold/feature Parquet"| MINIO
    AIRFLOW -->|"run state + DQ"| POSTGRES
    MINIO -->|"Parquet inspection"| DUCKDB
```

Every arrow follows data-flow direction (A→B when data moves from A to B) and
carries a label describing what moves along it — the same convention this
plan's style contract fixes for all seven subsystem diagrams. Feast SDK,
DuckDB `httpfs` extension, and similar libraries are deliberately *not*
drawn as nodes — they are not independently deployable.

## Limitations

This doc indexes the diagram and domain summary; the full README carries the
canonical, most-current version of both — read `README.md` directly for the
authoritative text.

## References

- Mermaid flowchart syntax: https://mermaid.js.org/syntax/flowchart.html
