"""
DAG 05 - Transform Bronze to Silver (PySpark).

Runs the PySpark Bronze-to-Silver job that normalises raw collector output, applies
schema validation against the in-memory registry, and writes idempotent, partitioned
Parquet to the Silver zone. Used by the platform evidence pipeline.

W9 fail-fast: the smoke helper ``_transform_smoke_run`` captures the ``failed`` list
returned by ``bronze_to_silver`` and raises ``AirflowFailException`` (or a clear
``RuntimeError`` when Airflow is not installed) when any row lands in ``failed``.
This prevents a single invalid bronze row from silently passing the smoke gate.
"""

from __future__ import annotations

from dags.utils.dag_utils import DEFAULT_ARGS, airflow_imports
from src.metadata.schema_registry import InMemorySchemaRegistry
from src.transforms.bronze_to_silver import bronze_to_silver

DAG, PythonOperator = airflow_imports()


def _airflow_fail(message: str) -> None:
    """Raise AirflowFailException when Airflow is present, else RuntimeError.

    The DAG file must remain importable without Airflow (so ``python -c "import dags.X"``
    works in CI without the airflow package). The fail-fast primitive degrades to a
    plain ``RuntimeError`` in that case, but the operator itself always raises.
    """
    try:
        from airflow.exceptions import AirflowFailException

        raise AirflowFailException(message)
    except ImportError:
        raise RuntimeError(f"[dag05] smoke helper failed: {message}") from None


def _transform_smoke_run(rows, required, nullable) -> tuple[list[dict], list[dict]]:
    """Smoke helper. Calls ``bronze_to_silver`` and fails fast on any failed row.

    Returns the (valid, failed) tuple so callers can inspect the result; but the
    helper itself raises before returning whenever ``failed`` is non-empty.
    """
    valid, failed = bronze_to_silver(rows, required, nullable, ["ticker"])
    if failed:
        _airflow_fail(
            f"{len(failed)} bronze row(s) failed schema validation; aborting DAG 05 smoke"
        )
    return valid, failed


def _transform_smoke() -> tuple[list[dict], list[dict]]:
    contract = InMemorySchemaRegistry().get_current("companies")
    return _transform_smoke_run(
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
