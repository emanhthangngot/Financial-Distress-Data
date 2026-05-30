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
