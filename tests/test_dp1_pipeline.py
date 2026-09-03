"""
DP1 pipeline invariant tests.

Regression locks for the platform DP1 Bronze ingest DAG. These tests parse the DAG
source statically and import it defensively, so they run on a machine without
Airflow installed (matches the test environment in ``pyproject.toml``).
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DAG_FILE = REPO_ROOT / "dags" / "dp1_bronze_ingest.py"


def _read_source() -> str:
    assert DAG_FILE.exists(), f"DP1 DAG file is missing at {DAG_FILE}; expected scaffold in W20"
    return DAG_FILE.read_text(encoding="utf-8")


def test_dp1_dag_file_exists_at_dags_root():
    assert DAG_FILE.exists(), f"expected DP1 DAG at {DAG_FILE}"


def test_dp1_dag_imports_cleanly():
    module = importlib.import_module("dags.dp1_bronze_ingest")
    assert module is not None
    # Module must expose a module-level ``dag`` reference for the registered DAG.
    assert hasattr(module, "dag"), "DP1 module must expose a module-level `dag`"


def test_dp1_dag_id_is_dp1_bronze_ingest():
    source = _read_source()
    assert re.search(r'dag_id\s*=\s*"dp1_bronze_ingest"', source), (
        "DP1 DAG must register with dag_id='dp1_bronze_ingest' for the rubric "
        "UI screenshot to be stable"
    )


def test_dp1_dag_has_ingest_and_validate_stages():
    source = _read_source()
    assert re.search(
        r'task_id\s*=\s*"ingest_bronze"', source
    ), "DP1 DAG must define an `ingest_bronze` task (rubric: Ingest stage, 2 pts)"
    assert re.search(
        r'task_id\s*=\s*"validate_bronze"', source
    ), "DP1 DAG must define a `validate_bronze` task (rubric: Validate stage, 2 pts)"


def test_dp1_validate_stage_depends_on_ingest():
    source = _read_source()
    # Either explicit `validate_bronze.set_upstream(ingest_bronze)` or the
    # bitshift operator `<<` chaining are acceptable DAG wiring idioms.
    upstream_anchor = re.search(
        r"(validate_bronze\s*<<\s*ingest_bronze|"
        r"ingest_bronze\s*>>\s*validate_bronze|"
        r"validate_bronze\.set_upstream\(\s*ingest_bronze\s*\))",
        source,
    )
    assert upstream_anchor is not None, (
        "DP1 DAG must wire validate_bronze downstream of ingest_bronze; "
        "the rubric screenshot depends on a visible task ordering"
    )


def test_dp1_dag_uses_airflow_variable_for_bucket():
    source = _read_source()
    # Bucket is an Airflow Variable in the running cluster; the DAG code must
    # read it through ``Variable.get`` (rubric bonus: variables in Airflow).
    assert (
        "Variable.get" in source
    ), "DP1 DAG must read at least one value from Airflow Variable (rubric bonus)"
    assert (
        "financial_distress_bucket" in source or "FINANCIAL_DISTRESS_BUCKET" in source
    ), "DP1 DAG must reference the lakehouse bucket name (Variable or env fallback)"


def test_dp1_ingest_stage_includes_all_three_collectors():
    source = _read_source()
    # Ingest stage fans out to the three batch collectors; the rubric calls
    # out Bronze ingest of raw data and these are the three source families.
    expected_callables = [
        "collect_companies",
        "collect_financial_statements",
        "collect_market_prices",
    ]
    for callable_name in expected_callables:
        assert (
            callable_name in source
        ), f"DP1 ingest stage must orchestrate the `{callable_name}` collector"


def test_dp1_module_has_docstring():
    source = _read_source()
    # First non-blank line must be a docstring (rubric row 5: module docstrings).
    first_meaningful = next((line.strip() for line in source.splitlines() if line.strip()), "")
    assert first_meaningful.startswith('"""') or first_meaningful.startswith(
        "'''"
    ), "DP1 DAG module must start with a module-level docstring"
