"""DP3: compute offline features and enforce point-in-time correctness."""

from __future__ import annotations

from datetime import timedelta

from dags._stage1_dag_utils import DEFAULT_ARGS, airflow_imports
from src.orchestration import airflow_tasks

DAG, PythonOperator = airflow_imports()
DAG_ID = "build_offline_features"


def task_chain() -> list[str]:
    return [
        "resolve_run",
        "compute_offline_features",
        "validate_point_in_time_features",
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
        dagrun_timeout=timedelta(hours=1),
        tags=["financial-distress", "rubric", "dp3", "features"],
    ) as dag:
        tasks = {
            "resolve_run": PythonOperator(
                task_id="resolve_run",
                python_callable=airflow_tasks.resolve_run,
                op_kwargs={"dag_id": DAG_ID},
            ),
            "compute_offline_features": PythonOperator(
                task_id="compute_offline_features",
                python_callable=airflow_tasks.compute_offline_features,
            ),
            "validate_point_in_time_features": PythonOperator(
                task_id="validate_point_in_time_features",
                python_callable=airflow_tasks.validate_point_in_time_features,
            ),
            "publish_manifest": PythonOperator(
                task_id="publish_manifest",
                python_callable=airflow_tasks.publish_manifest,
                op_kwargs={"pipeline_id": DAG_ID},
            ),
        }
        for left, right in zip(task_chain()[:-1], task_chain()[1:], strict=True):
            tasks[left] >> tasks[right]
