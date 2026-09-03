"""
Command-line runner for the DuckDB catalog.

Applies the catalog DDL against a local DuckDB instance, used by DAG 08 and by the lakehouse evidence
script. Idempotent: re-running drops and recreates the views.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


def _endpoint_from_env() -> str | None:
    endpoint = os.getenv("MINIO_ENDPOINT")
    if not endpoint:
        return None
    return endpoint.removeprefix("http://").removeprefix("https://")


def _read_dotenv_value(name: str, env_path: str | Path = ".env") -> str | None:
    path = Path(env_path)
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == name:
            return value.strip().strip('"').strip("'") or None
    return None


def create_views_sql(sql_path: str | Path = "sql/duckdb_create_views.sql") -> str:
    """Render the DuckDB view-creation SQL with runtime substitutions.

    The endpoint placeholder is injected from the ``MINIO_ENDPOINT`` env
    var when set; credentials are intentionally NOT injected here --
    ``sql/duckdb_create_views.sql`` no longer carries demo strings, and
    DuckDB resolves ``MINIO_ROOT_USER`` / ``MINIO_ROOT_PASSWORD`` from
    its own env chain. This contract is enforced by
    ``tests/test_secrets_no_defaults.py``.
    """
    sql = Path(sql_path).read_text(encoding="utf-8")
    endpoint = _endpoint_from_env()
    if endpoint is not None:
        sql = re.sub(r"SET s3_endpoint='[^']+';", f"SET s3_endpoint='{endpoint}';", sql)

    access_key = os.getenv("MINIO_ROOT_USER") or _read_dotenv_value("MINIO_ROOT_USER")
    secret_key = os.getenv("MINIO_ROOT_PASSWORD") or _read_dotenv_value("MINIO_ROOT_PASSWORD")
    if access_key and secret_key:
        credential_sql = (
            f"SET s3_access_key_id='{access_key}';\nSET s3_secret_access_key='{secret_key}';"
        )
        sql = sql.replace(
            "-- env chain (process env, .env, ~/.aws/credentials).",
            "-- env chain (process env, .env, ~/.aws/credentials).\n" + credential_sql,
        )
    return sql


def validation_statements(sql_path: str | Path = "sql/duckdb_validation_queries.sql") -> list[str]:
    sql = Path(sql_path).read_text(encoding="utf-8")
    return [statement.strip() for statement in sql.split(";") if statement.strip()]


def run_duckdb_validation(
    evidence_dir: str | Path,
    create_views_sql_path: str | Path = "sql/duckdb_create_views.sql",
    validation_sql_path: str | Path = "sql/duckdb_validation_queries.sql",
) -> list[dict[str, Any]]:
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError(
            "DuckDB validation requires runtime dependencies: "
            ".venv/bin/python -m pip install -e '.[runtime]'."
        ) from exc

    connection = duckdb.connect(":memory:")
    try:
        connection.execute(create_views_sql(create_views_sql_path))
        outputs = []
        for statement in validation_statements(validation_sql_path):
            result = connection.execute(statement)
            outputs.append(
                {
                    "query": statement,
                    "columns": [column[0] for column in result.description or []],
                    "rows": result.fetchall(),
                }
            )
    finally:
        connection.close()

    output_dir = Path(evidence_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "lakehouse_duckdb_validation.json"
    output_path.write_text(json.dumps(outputs, indent=2, default=str), encoding="utf-8")
    return outputs
