"""
DAG 08 - Register MinIO Parquet as DuckDB views.

Creates the DuckDB catalog that exposes Silver and Gold Parquet partitions as SQL
views. The DAG also runs a smoke query so the catalog is verified end-to-end
(``httpfs`` over MinIO + view materialisation) before downstream tasks read it.
"""

from __future__ import annotations

from dags.utils.stage1_dag_utils import DEFAULT_ARGS, airflow_imports
from src.catalog.duckdb_catalog import create_view_sql

DAG, PythonOperator = airflow_imports()


def _duckdb_smoke() -> str:
    return create_view_sql(
        "gold_fact_financial_statement",
        "s3://financial-distress-lake/gold/fact_financial_statement/**/*.parquet",
    )


if DAG is not None:
    with DAG(
        dag_id="08_minio_duckdb_register_tables",
        default_args=DEFAULT_ARGS,
        schedule=None,
        catchup=False,
        tags=["financial-distress", "stage-1"],
    ) as dag:
        PythonOperator(task_id="create_or_update_duckdb_views", python_callable=_duckdb_smoke)
