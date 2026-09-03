"""DP2: build and validate Silver and Gold datasets with Spark."""

from __future__ import annotations

from datetime import timedelta

from dags.utils.dag_utils import DEFAULT_ARGS, airflow_imports
from src.orchestration import airflow_tasks

DAG, PythonOperator = airflow_imports()
DAG_ID = "build_silver_gold"


def task_chain() -> list[str]:
    return [
        "resolve_run",
        "spark_build_silver_gold",
        "validate_silver_gold",
        "publish_manifest",
    ]


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
        dagrun_timeout=timedelta(hours=2),
        tags=["financial-distress", "rubric", "dp2", "spark"],
    ) as dag:
        tasks = {
            "resolve_run": PythonOperator(
                task_id="resolve_run",
                python_callable=airflow_tasks.resolve_run,
                op_kwargs={"dag_id": DAG_ID},
            ),
            "spark_build_silver_gold": PythonOperator(
                task_id="spark_build_silver_gold",
                python_callable=airflow_tasks.spark_build_silver_gold,
            ),
            "validate_silver_gold": PythonOperator(
                task_id="validate_silver_gold",
                python_callable=airflow_tasks.validate_silver_gold,
            ),
            "publish_manifest": PythonOperator(
                task_id="publish_manifest",
                python_callable=airflow_tasks.publish_manifest,
                op_kwargs={"pipeline_id": DAG_ID},
            ),
        }
        for left, right in zip(task_chain()[:-1], task_chain()[1:], strict=True):
            tasks[left] >> tasks[right]
