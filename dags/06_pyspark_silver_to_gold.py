"""
DAG 06 - PySpark Silver to Gold.

Runs the PySpark Silver-to-Gold job that builds dimension tables, fact tables, and
the unified company-quarter risk OBT. Output lands in the Gold zone and is
registered as DuckDB views for analyst queries.
"""

from __future__ import annotations

import os

from dags.utils.stage1_dag_utils import DEFAULT_ARGS, airflow_imports
from src.collectors.source_adapters.vnstock_fixture_adapter import VnstockFixtureAdapter
from src.lakehouse.compaction import compact_small_files
from src.transforms.compute_distress_labels import compute_labels
from src.transforms.silver_to_gold import build_fact_financial_statement

DAG, PythonOperator = airflow_imports()


def _gold_smoke() -> list[dict]:
    adapter = VnstockFixtureAdapter()
    statements = adapter.fetch_financial_statements("AAA", 2025, 2025)
    facts = build_fact_financial_statement(statements)
    return compute_labels(facts)


def _compact_gold_tables() -> dict:
    """Run lakehouse compaction on the Gold zone.

    Guarded by the AVG_FILE_MB env var (default 64 MB). Only directories whose
    average Parquet file size is below the threshold get compacted; the rest
    are considered healthy and skipped.
    """
    threshold_mb = float(os.environ.get("AVG_FILE_MB", "64"))
    threshold_bytes = int(threshold_mb * 1024 * 1024)
    # The DAG runs inside the Airflow container; the Gold root is /opt/airflow
    # by default. We probe both the in-container and the host paths so the
    # task is resilient to local ``airflow tasks test`` runs.
    candidates = [os.environ.get("GOLD_ROOT", "/opt/airflow/data/gold")]
    summary: dict = {"scanned": [], "compacted": [], "skipped": []}
    for root in candidates:
        if not os.path.isdir(root):
            continue
        summary["scanned"].append(root)
        for dirpath, _dirnames, filenames in os.walk(root):
            parquet_files = [f for f in filenames if f.endswith(".parquet")]
            if not parquet_files:
                continue
            total_bytes = sum(os.path.getsize(os.path.join(dirpath, f)) for f in parquet_files)
            avg_bytes = total_bytes / len(parquet_files)
            if avg_bytes >= threshold_bytes:
                summary["skipped"].append({"path": dirpath, "avg_bytes": int(avg_bytes)})
                continue
            result = compact_small_files(
                dirpath,
                target_file_mb=128,
                output_dir=os.path.join(dirpath, "_compacted"),
            )
            summary["compacted"].append({"path": dirpath, "result": result})
    return summary


if DAG is not None:
    with DAG(
        dag_id="06_pyspark_silver_to_gold",
        default_args=DEFAULT_ARGS,
        schedule=None,
        catchup=False,
        tags=["financial-distress", "stage-1"],
    ) as dag:
        spark_build_gold_tables = PythonOperator(
            task_id="spark_build_gold_tables", python_callable=_gold_smoke
        )
        compact_gold_tables = PythonOperator(
            task_id="compact_gold_tables", python_callable=_compact_gold_tables
        )
        spark_build_gold_tables >> compact_gold_tables
