"""platform: Feast structured feature materialization
(feast_apply -> materialize_incremental -> record_registry_revision), run as
one task via src.ml.feast.materialization.run_materialize_task."""

from __future__ import annotations

from datetime import timedelta

from dags.utils.dag_utils import DEFAULT_ARGS, airflow_imports
from src.ml.feast.materialization import run_materialize_task

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
        PythonOperator(
            task_id="materialize",
            python_callable=run_materialize_task,
        )
