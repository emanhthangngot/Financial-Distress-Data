"""Phase 2: drift-scenario report + label table build
(generate -> apply_drift -> drift_report -> build_labels -> publish), run as
one task via src.ml.label_pipeline.run_label_drift_build_task."""

from __future__ import annotations

from datetime import timedelta

from dags.utils.dag_utils import DEFAULT_ARGS, airflow_imports
from src.ml.label_pipeline import run_label_drift_build_task

DAG, PythonOperator = airflow_imports()
DAG_ID = "label_drift_build"

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
        tags=["financial-distress", "phase2", "ml", "llm", "drift", "labels"],
    ) as dag:
        PythonOperator(
            task_id="build_drift_report_and_labels",
            python_callable=run_label_drift_build_task,
        )
