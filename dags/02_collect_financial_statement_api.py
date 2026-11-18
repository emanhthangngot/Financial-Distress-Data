"""
DAG 02 - Collect financial statements (quarterly).

Fetches quarterly income-statement, balance-sheet, and cash-flow rows for the watchlist
from the financial-statement collector. Output goes to the Bronze zone; downstream
transforms build Silver facts and Gold distress labels from this raw source.
"""

from __future__ import annotations

from dags.utils.dag_utils import DEFAULT_ARGS, airflow_imports
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
