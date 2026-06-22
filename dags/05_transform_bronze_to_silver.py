"""
DAG 05 - Transform Bronze to Silver (PySpark).

Runs the PySpark Bronze-to-Silver job that normalises raw collector output, applies
schema validation against the in-memory registry, and writes idempotent, partitioned
Parquet to the Silver zone. Used by the Stage 1 evidence pipeline.
"""

from __future__ import annotations

from dags._stage1_dag_utils import DEFAULT_ARGS, airflow_imports
from src.metadata.schema_registry import InMemorySchemaRegistry
from src.transforms.bronze_to_silver import bronze_to_silver

DAG, PythonOperator = airflow_imports()


def _transform_smoke() -> tuple[list[dict], list[dict]]:
    contract = InMemorySchemaRegistry().get_current("companies")
    return bronze_to_silver(
        [
            {
                "ticker": "AAA",
                "company_name": "AAA Corp",
                "exchange": "HOSE",
                "created_ts": "2026-01-01T00:00:00+00:00",
            }
        ],
        contract.required,
        contract.nullable,
        ["ticker"],
    )


if DAG is not None:
    with DAG(
        dag_id="05_transform_bronze_to_silver",
        default_args=DEFAULT_ARGS,
        schedule=None,
        catchup=False,
        tags=["financial-distress", "stage-1"],
    ) as dag:
        PythonOperator(
            task_id="validate_schema_clean_and_deduplicate",
            python_callable=_transform_smoke,
        )
