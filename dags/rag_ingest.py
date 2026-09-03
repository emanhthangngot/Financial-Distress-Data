"""platform: RAG ingestion (fetch -> chunk -> dedupe -> govern -> embed_write),
all five RagIngestionService steps run in one task — see
src.llm.rag_pipeline.RagIngestionPipeline's class docstring for why."""

from __future__ import annotations

from datetime import timedelta

from dags.utils.dag_utils import DEFAULT_ARGS, airflow_imports
from src.llm.rag_pipeline import run_ingestion_task

DAG, PythonOperator = airflow_imports()
DAG_ID = "rag_ingest"

if DAG is not None:
    with DAG(
        dag_id=DAG_ID,
        default_args={
            **DEFAULT_ARGS,
            "retries": 2,
            "retry_delay": timedelta(seconds=30),
            "retry_exponential_backoff": True,
        },
        schedule=None,
        catchup=False,
        dagrun_timeout=timedelta(hours=1),
        tags=["financial-distress", "platform", "llm", "rag"],
    ) as dag:
        PythonOperator(
            task_id="run_ingestion",
            python_callable=run_ingestion_task,
        )
