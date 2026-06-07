from __future__ import annotations

from dags._stage1_dag_utils import DEFAULT_ARGS, airflow_imports
from src.collectors.source_adapters.vnstock_fixture_adapter import VnstockFixtureAdapter
from src.transforms.silver_to_gold import build_distress_labels, build_fact_financial_statement

DAG, PythonOperator = airflow_imports()


def _gold_smoke() -> list[dict]:
    adapter = VnstockFixtureAdapter()
    statements = adapter.fetch_financial_statements("AAA", 2025, 2025)
    facts = build_fact_financial_statement(statements)
    return build_distress_labels(facts)


if DAG is not None:
    with DAG(
        dag_id="06_pyspark_silver_to_gold",
        default_args=DEFAULT_ARGS,
        schedule=None,
        catchup=False,
        tags=["financial-distress", "stage-1"],
    ) as dag:
        PythonOperator(task_id="spark_build_gold_tables", python_callable=_gold_smoke)
