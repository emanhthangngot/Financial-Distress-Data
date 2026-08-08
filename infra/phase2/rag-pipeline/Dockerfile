# syntax=docker/dockerfile:1.7
# Runs dags/phase2/phase2_rag_ingest.py's callable
# (src.llm.rag_pipeline.run_ingestion_task) as a standalone deployable —
# same code the Airflow PythonOperator calls, packaged separately per
# phase-04-implementation-notes.md section 2's "two processes, two images"
# note for the stream jobs, extended here for consistency across all three
# CI-built pipelines.
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN pip install --no-cache-dir \
    pyyaml>=6.0 \
    "psycopg[binary]>=3.2" \
    requests>=2.31 \
    tenacity>=8.0 \
    numpy>=1.26

COPY src ./src
COPY configs ./configs
COPY sql ./sql

ENV PYTHONPATH=/app

CMD ["python", "-c", "from src.llm.rag_pipeline import run_ingestion_task; print(run_ingestion_task())"]
