"""platform: Feast structured feature materialization with validation."""

from __future__ import annotations

from datetime import timedelta

from dags.utils.dag_utils import DEFAULT_ARGS, airflow_imports
from src.ml.feast.materialization import run_materialize_task, validate_materialization_task

DAG, PythonOperator = airflow_imports()
DAG_ID = "feature_materialize"

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
        tags=["financial-distress", "platform", "ml", "feast"],
    ) as dag:
        ingest_features = PythonOperator(
            task_id="ingest_features",
            python_callable=run_materialize_task,
        )
        validate_features = PythonOperator(
            task_id="validate_features",
            python_callable=validate_materialization_task,
        )
        ingest_features >> validate_features
