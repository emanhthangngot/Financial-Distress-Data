from __future__ import annotations


def create_view_sql(view_name: str, parquet_path: str) -> str:
    return f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_parquet('{parquet_path}');"
