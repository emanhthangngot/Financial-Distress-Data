"""
Local catalog: DuckDB views over MinIO Parquet.

Hosts the DuckDB-backed catalog that registers Silver and Gold Parquet partitions as SQL views for
analyst queries. Reads via the ``httpfs`` extension so the same views work in DBeaver and CLI.
"""
