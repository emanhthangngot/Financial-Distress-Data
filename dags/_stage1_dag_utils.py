"""
Stage 1 DAG utilities.

Shared helpers for the Stage 1 evidence DAGs: ``DEFAULT_ARGS`` (Airflow default
arguments), ``airflow_imports()`` (defensive import of Airflow primitives so
``python -c "import dags.X"`` works without Airflow installed), and
``metadata_writer_from_env()`` (PostgreSQL writer factory wired to
``project_metadata``).
"""

from __future__ import annotations

import os
from datetime import datetime

from src.metadata.metadata_writer import (
    MetadataWriter,
    PostgresMetadataWriter,
    psycopg_connection_factory,
)


def airflow_imports():
    try:
        from airflow import DAG
        from airflow.operators.python import PythonOperator
    except Exception:
        return None, None
    return DAG, PythonOperator


DEFAULT_ARGS = {"owner": "financial-distress", "start_date": datetime(2026, 1, 1)}


def metadata_writer_from_env():
    dsn = os.getenv("PROJECT_METADATA_DSN")
    if dsn:
        return PostgresMetadataWriter(psycopg_connection_factory(dsn))
    return MetadataWriter()
