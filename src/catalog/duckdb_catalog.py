from __future__ import annotations


def duckdb_httpfs_setup_sql(
    endpoint: str = "localhost:9000",
    access_key: str = "minioadmin",
    secret_key: str = "minioadmin",
) -> str:
    return f"""INSTALL httpfs;
LOAD httpfs;
SET s3_endpoint='{endpoint}';
SET s3_access_key_id='{access_key}';
SET s3_secret_access_key='{secret_key}';
SET s3_use_ssl=false;
SET s3_url_style='path';"""


def create_view_sql(view_name: str, parquet_path: str) -> str:
    return f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_parquet('{parquet_path}');"
