# platform .ompletion Report

Date: 2026-07-22
Status: Completed

## Delivered

- Added versioned, typed YAML schema contracts with blank, enum, numeric, and UTC timestamp validation.
- Aligned Python and Spark Silver behavior, deterministic event IDs, and latest-event deduplication.
- Implemented persistent SCD2 company history with stable entity keys and version keys.
- Joined sector metadata before configurable distress-label exclusions.
- Persisted rejected records with `run_id` linkage and batched metadata writes.
- Replaced broad optional-input fallbacks with missing-only handling; corrupt inputs now fail.
- Added staging, DQ-before-promotion, atomic local publication, and rollback-capable MinIO promotion.
- Made DQ rules executable from YAML and fixed null referential integrity and future freshness behavior.
- Extracted publication/DQ responsibilities from the Spark runtime job and identified smoke DAGs explicitly.

## Defects Found During Real Runtime Validation

1. Spark unions failed when an optional `shares_outstanding` column was absent. Nullable columns are now aligned before union.
2. News facts retained replay duplicates in the Spark path. Latest-event deduplication now matches the Python contract.
3. The external DQ job used a stale fixed reference date, incorrectly classifying future data. It now resolves the current UTC time at task execution.

Each defect received a focused regression test before the runtime fix.

## Verification

| Gate | Result |
|---|---|
| Full unit/regression suite | 131 passed |
| Ruff | Passed |
| Python compileall | Passed |
| Docker Compose validation | Passed |
| Whitespace validation | Passed |
| Black | 94 files unchanged; formatter process has a known exit hang and was terminated after its successful result |
| Docker service checks | PostgreSQL, Kafka topics, MinIO bucket, and Airflow DAG imports passed |
| Real Airflow/Spark evidence DAG | Passed with run `phase2-debug3` |

The successful runtime produced 2 companies, 16 financial statements, 14 market prices, 2 SCD2 dimension rows, 16 financial facts, 14 market facts, 1 alert, 2 news facts, 16 labels, and 16 unified feature rows. It recorded zero rejected rows for the valid fixture.

All critical external DQ checks passed. Fixture freshness remains a warning because the deterministic January 2026 fixture is intentionally older than the July 2026 validation date.

## Coverage Notes

- Stateful unit tests prove SCD2 change, no-change, and null transitions. Repeated Docker execution proves the no-change path does not duplicate current company versions.
- Atomic failure tests prove the previous local snapshot remains published; MinIO promotion includes rollback behavior.
- Python and Spark consume the same schema and DQ configuration. The real Spark run validates the distributed path against the shared expected counts.
- A changed-company two-run Docker artifact is deferred to the configurable generator phase; the behavior itself is covered by the stateful regression tests.

## Runtime State

The Docker stack remains running. PostgreSQL is mapped to host port `55432` because the default `5432` port was already occupied.
