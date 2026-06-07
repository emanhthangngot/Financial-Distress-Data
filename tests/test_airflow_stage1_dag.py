import importlib


def test_primary_stage1_evidence_dag_imports_without_airflow():
    module = importlib.import_module("dags.stage1_local_evidence_pipeline")

    assert module.build_stage1_payload()["gold_fact_financial_statement"] == 16
    assert module.DAG is None
