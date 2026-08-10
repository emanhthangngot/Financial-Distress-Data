"""Phase 2: stream `financial.price_events` -> offline parquet append +
checkpoint, via src.ml.feast.offline_job.run_offline_job."""

from __future__ import annotations

from datetime import timedelta

from dags._stage1_dag_utils import DEFAULT_ARGS, airflow_imports
from src.ml.feast.offline_job import run_offline_job

DAG, PythonOperator = airflow_imports()
DAG_ID = "phase2_stream_feature_offline"

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
        tags=["financial-distress", "phase2", "ml", "feast", "streaming"],
    ) as dag:
        PythonOperator(
            task_id="consume_transform_push_offline",
            python_callable=run_offline_job,
        )
