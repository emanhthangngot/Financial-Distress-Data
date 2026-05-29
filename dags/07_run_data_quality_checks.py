from __future__ import annotations

from dags._stage1_dag_utils import DEFAULT_ARGS, airflow_imports
from src.quality.dq_checks import check_not_null

DAG, PythonOperator = airflow_imports()


def _dq_smoke():
    return check_not_null([{"ticker": "AAA"}], "companies", "ticker")


if DAG is not None:
    with DAG(
        dag_id="07_run_data_quality_checks",
        default_args=DEFAULT_ARGS,
        schedule=None,
        catchup=False,
        tags=["financial-distress", "stage-1"],
    ) as dag:
        PythonOperator(task_id="run_schema_and_null_checks", python_callable=_dq_smoke)
