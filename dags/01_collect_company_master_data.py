from __future__ import annotations

from dags._stage1_dag_utils import DEFAULT_ARGS, airflow_imports
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
