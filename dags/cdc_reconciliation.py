"""Phase 2: reconcile generator and Flink CDC Bronze paths.

The module is a thin Airflow wrapper.  All connector/network work remains in
the task callable so importing the DAG in tests or scheduler discovery has no
filesystem, socket, database, or Flink side effects.
"""

from __future__ import annotations

from datetime import timedelta

from dags.utils.dag_utils import DEFAULT_ARGS, airflow_imports
from src.cdc.reconcile import run_reconciliation_task

DAG, PythonOperator = airflow_imports()
DAG_ID = "cdc_reconciliation"

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
        tags=["financial-distress", "phase2", "cdc", "reconciliation"],
    ) as dag:
        PythonOperator(
            task_id="reconcile_generator_and_cdc",
            python_callable=run_reconciliation_task,
        )
