"""
DAG 01 - Collect company master data.

Pulls the universe of tickers (HOSE, HNX, UPCOM) from the company-list collector and
lands the result in the Bronze zone. The DAG runs on demand and is the first step of
the platform evidence pipeline.
"""

from __future__ import annotations

from dags.utils.dag_utils import DEFAULT_ARGS, airflow_imports
from src.collectors.company_list_collector import collect_companies

DAG, PythonOperator = airflow_imports()

if DAG is not None:
    with DAG(
        dag_id="01_collect_company_master_data",
        default_args=DEFAULT_ARGS,
        schedule=None,
        catchup=False,
        tags=["financial-distress", "stage-1"],
    ) as dag:
        PythonOperator(
            task_id="fetch_company_list_from_primary_source",
            python_callable=collect_companies,
        )
