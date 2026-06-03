# Evidence Collection Checklist

Runtime evidence is intentionally stored here after running the local Docker stack.

Minimum Phase 1 submission artifacts:

- `pytest` output showing the local unit suite passes.
- `docker compose config` output.
- PostgreSQL query export or screenshot for `project_metadata.pipeline_run_log`.
- PostgreSQL query export or screenshot for `project_metadata.data_quality_result`.
- PostgreSQL query export or screenshot for `project_metadata.dataset_freshness`.
- MinIO screenshot showing Bronze, Silver, or Gold object paths.
- DuckDB query output against Gold views.
- DBeaver screenshots for PostgreSQL metadata and DuckDB views.

Suggested local commands:

```bash
docker compose up -d postgres minio kafka
docker compose exec kafka bash /opt/financial-distress-init/kafka_init_topics.sh
.venv/bin/python -m pytest
```

Only add artifacts that were produced by an actual local run.

## Stage 1 Automated Evidence Run

Install runtime dependencies before materializing MinIO/PostgreSQL evidence:

```bash
.venv/bin/python -m pip install -e ".[dev,runtime]"
```

Start the complete local stack. The compose file initializes Airflow metadata,
creates the MinIO bucket `financial-distress-lake`, and creates the Kafka topics.

```bash
cp .env.example .env
docker compose up -d
docker compose ps
```

Run the Stage 1 evidence materializer:

```bash
.venv/bin/python scripts/run_stage1_evidence.py
```

For a no-service payload check:

```bash
.venv/bin/python scripts/run_stage1_evidence.py --dry-run --evidence-dir /tmp/stage1-evidence
```

Expected generated evidence files:

- `stage1_row_counts.json`
- `stage1_minio_objects.txt`
- `stage1_stream_batches.json`
- `stage1_duckdb_validation.json` after a non-dry-run execution

## Manual Inspection Targets

MinIO:

- URL: `http://localhost:9001`
- Login: `minioadmin` / `minioadmin`
- Bucket: `financial-distress-lake`
- Check prefixes under `bronze/`, `silver/`, and `gold/`.

Airflow:

- URL: `http://localhost:8080`
- Login: `airflow` / `airflow`
- Trigger the eight Stage 1 smoke DAGs and capture successful task evidence.

DBeaver PostgreSQL connection:

- Host: `localhost`
- Port: `55432` when using `.env.example`, otherwise the value of `POSTGRES_HOST_PORT`
- Database: `financial_distress`
- User/password: `airflow` / `airflow`
- Evidence queries:

```sql
SELECT * FROM project_metadata.pipeline_run_log ORDER BY created_at DESC LIMIT 20;
SELECT * FROM project_metadata.data_quality_result ORDER BY checked_at DESC LIMIT 20;
SELECT * FROM project_metadata.dataset_freshness ORDER BY checked_at DESC LIMIT 20;
SELECT dataset_name, schema_version, schema_json
FROM project_metadata.schema_version_registry
ORDER BY dataset_name;
```

DBeaver DuckDB connection:

1. Open a DuckDB connection.
2. Run `sql/duckdb_create_views.sql`.
3. Run `sql/duckdb_validation_queries.sql`.
4. Capture row counts, duplicate-check output, distress-label distribution, and
   `gold_feat_company_unified` sample rows.
