"""Regression tests for the PR #1 review follow-up cleanup."""

from __future__ import annotations

import importlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_reviewer_flagged_module_names_are_removed() -> None:
    """Reviewer-flagged helper filenames should not remain in source/test paths."""
    removed_paths = [
        REPO_ROOT / "dags" / "_stage1_dag_utils.py",
        REPO_ROOT / "src" / "transforms" / "features" / "pit.py",
        REPO_ROOT / "src" / "transforms" / "silver" / "spark.py",
        REPO_ROOT / "tests" / "test_airflow_stage1_dag.py",
    ]

    assert all(not path.exists() for path in removed_paths)


def test_renamed_public_imports_resolve() -> None:
    """The clearer replacement modules should be importable through their new paths."""
    dag_utils = importlib.import_module("dags.utils.stage1_dag_utils")
    features = importlib.import_module("src.transforms.features.point_in_time")
    silver_spark = importlib.import_module("src.transforms.silver.bronze_to_silver_spark")

    assert callable(dag_utils.metadata_writer_from_env)
    assert callable(features.pit_join_features)
    assert callable(silver_spark.bronze_to_silver_spark)


def test_duckdb_guardrail_is_visible_to_reviewers() -> None:
    """README and SQL must state that DuckDB is local inspection, not horizontal scale."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8").lower()
    sql = (REPO_ROOT / "sql" / "duckdb_create_views.sql").read_text(encoding="utf-8").lower()

    assert "single-node sql inspection" in readme
    assert "not a horizontally scalable serving layer" in readme
    assert "single-node inspection engine" in sql
    assert "not used as a horizontally scalable serving layer" in sql
