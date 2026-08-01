# UI Screenshot Capture Runbook

The rubric rows under "Data Pipeline Orchestration" and "Data Governance" ask
for screenshots captured on the live Airflow, DataHub, Spark, and Flink UIs.
The checked-in `reviewer_screenshots/` pack was generated from evidence HTML
views. This runbook captures **genuine UI screenshots** from the running local
stack so a strict reviewer sees real service screens, not rendered HTML.

## What the script produces

`scripts/capture_ui_screenshots.py` drives a headless Chromium (Playwright)
against the local Docker stack and writes into `docs/evidence/screenshots/`:

| File | Source UI | Rubric row |
|---|---|---|
| `airflow-dp1.png` | Airflow DAG graph for `dp1_bronze_ingest` | DP1 ingest + validate stages |
| `airflow-dp2.png` | Airflow DAG graph for `build_silver_gold` | DP2 ingest + validate stages |
| `airflow-dp3.png` | Airflow DAG graph for `build_offline_features` | DP3 ingest + validate stages |
| `datahub-dp1-lineage.png` | DataHub dataset page for `bronze.companies` | DP1 lineage + contract |
| `datahub-dp2-lineage.png` | DataHub dataset page for `gold.fact_financial_statement` | DP2 lineage + contract |
| `datahub-dp3-lineage.png` | DataHub dataset page for `gold.feat_company_unified` | DP3 lineage + contract |
| `flink-ui-overview.png` | Flink UI overview | Flink runtime |
| `flink-ui-job.png` | Flink UI job list | Flink job graph |

## Prerequisites

```bash
uv sync --all-extras   # installs playwright (dev extra)
.venv/bin/python -m playwright install chromium
```

Start the stack with Flink enabled and load the DAGs:

```bash
POSTGRES_HOST_PORT=55432 docker compose up -d \
  postgres minio minio-init kafka kafka-init \
  airflow-init airflow-webserver airflow-scheduler

docker compose exec kafka bash /opt/financial-distress-init/kafka_init_topics.sh

ENABLE_FLINK=1 docker compose --profile flink up -d flink-jobmanager flink-taskmanager
```

Each of the three DAGs must have at least one successful run so the Airflow
grid and DataHub lineage pages have content:

```bash
docker compose run --rm --no-deps airflow-scheduler airflow dags test \
  ingest_source_to_bronze 2026-07-30T12:02:00+00:00
docker compose run --rm --no-deps airflow-scheduler airflow dags test \
  build_silver_gold 2026-07-30T12:02:00+00:00
docker compose run --rm --no-deps airflow-scheduler airflow dags test \
  build_offline_features 2026-07-30T12:02:00+00:00
```

For DataHub, start the quickstart and sync governance metadata so dataset
pages, lineage, assertions, and contracts are populated:

```bash
uvx --python 3.12 --from acryl-datahub==1.6.0 datahub docker quickstart --version v1.6.0
uv run --python 3.12 --with acryl-datahub==1.6.0 \
  python scripts/sync_datahub_governance.py --emit --server http://localhost:8080 \
  --run-id <run-id> --output docs/evidence/datahub/phase7-runtime.json
```

## Capture

```bash
.venv/bin/python scripts/capture_ui_screenshots.py \
  --airflow-url http://localhost:8080 --airflow-user airflow --airflow-password airflow \
  --datahub-url http://localhost:9002 --datahub-user datahub --datahub-password datahub \
  --flink-url http://localhost:8081 \
  --output docs/evidence/screenshots
```

To capture only a subset of services, pass `--skip-airflow`, `--skip-datahub`,
or `--skip-flink`. Missing services produce a `WARN` line and are skipped, so a
partial run is still safe.

## After capture

1. Review the new PNGs and replace the HTML-rendered pack if the genuine
   captures are materially better:
   `docs/evidence/reviewer_screenshots/*.png`.
2. Update `docs/evidence/final/coursework-final-*/screenshots/*.png` if you
   regenerate the final evidence bundle.
3. Re-run the evidence audit to confirm the files are still discoverable:
   `python scripts/audit_stage1_evidence.py docs/evidence --check`.

## Why this matters

The rubric asks for UI captures on Airflow, DataHub, Spark UI, and Flink UI.
Genuine screenshots from a running service are the strongest possible proof and
remove the only real point-loss risk in the submission.
