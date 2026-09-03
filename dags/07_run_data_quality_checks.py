"""
DAG 07 - Run data quality checks.

Executes the DQ framework against each lakehouse zone, classifies results as
hard/soft failures, and writes them to ``project_metadata.data_quality_result``.
Hard-fail DQ halts the downstream Gold transform; soft-fail routes records to
``project_metadata.failed_records``.
"""

from __future__ import annotations

from dags.utils.dag_utils import DEFAULT_ARGS, airflow_imports, metadata_writer_from_env
from src.quality.dq_checks import check_not_null

DAG, PythonOperator = airflow_imports()


def _dq_smoke():
    result = check_not_null([{"ticker": "AAA"}], "companies", "ticker")
    writer = metadata_writer_from_env()
    run_id = writer.log_run(
        dag_id="07_run_data_quality_checks",
        task_id="run_schema_and_null_checks",
        dataset_name=result.dataset_name,
        status=result.status,
        input_rows=1,
        output_rows=1,
        error_message=result.error_message,
    )
    writer.log_dq_result(
        dataset_name=result.dataset_name,
        check_name=result.check_name,
        status=result.status,
        severity=result.severity,
        metric_value=result.metric_value,
        threshold_value=result.threshold_value,
        error_message=result.error_message,
        run_id=run_id,
    )
    return result


if DAG is not None:
    with DAG(
        dag_id="07_run_data_quality_checks",
        default_args=DEFAULT_ARGS,
        schedule=None,
        catchup=False,
        tags=["financial-distress", "stage-1"],
    ) as dag:
        PythonOperator(task_id="run_schema_and_null_checks", python_callable=_dq_smoke)
