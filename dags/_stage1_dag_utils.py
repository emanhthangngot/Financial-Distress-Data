from __future__ import annotations

from datetime import datetime


def airflow_imports():
    try:
        from airflow import DAG
        from airflow.operators.python import PythonOperator
    except Exception:
        return None, None
    return DAG, PythonOperator


DEFAULT_ARGS = {"owner": "financial-distress", "start_date": datetime(2026, 1, 1)}
