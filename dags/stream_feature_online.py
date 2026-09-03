"""platform: stream `financial.price_events` -> Feast online store (Redis
push) + checkpoint, via src.ml.feast.online_job.run_online_job."""

from __future__ import annotations

from datetime import timedelta

from dags.utils.dag_utils import DEFAULT_ARGS, airflow_imports
from src.ml.feast.online_job import run_online_job

DAG, PythonOperator = airflow_imports()
DAG_ID = "stream_feature_online"

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
        tags=["financial-distress", "platform", "ml", "feast", "streaming"],
    ) as dag:
        PythonOperator(
            task_id="consume_transform_push_online",
            python_callable=run_online_job,
        )
