from __future__ import annotations

from dags._stage1_dag_utils import DEFAULT_ARGS, airflow_imports
from src.collectors.financial_statement_collector import collect_financial_statements

DAG, PythonOperator = airflow_imports()


def _collect() -> list[dict]:
    return collect_financial_statements(["AAA", "BBB"], 2024, 2025)


if DAG is not None:
    with DAG(
        dag_id="02_collect_financial_statement_api",
        default_args=DEFAULT_ARGS,
        schedule=None,
        catchup=False,
        tags=["financial-distress", "stage-1"],
    ) as dag:
        PythonOperator(task_id="call_financial_statement_api", python_callable=_collect)
