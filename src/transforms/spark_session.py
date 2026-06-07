from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def _bool_string(value: Any) -> str:
    return "true" if bool(value) else "false"


def configure_spark_builder(builder: Any, config: dict[str, Any]) -> Any:
    minio = config.get("minio", {})
    app_name = config.get("app_name", "financial-distress-stage-1")
    master = config.get("master", "local[*]")
    access_key = minio.get("access_key") or os.getenv(
        minio.get("access_key_env", "MINIO_ROOT_USER"), "minioadmin"
    )
    secret_key = minio.get("secret_key") or os.getenv(
        minio.get("secret_key_env", "MINIO_ROOT_PASSWORD"), "minioadmin"
    )
    path_style_access = _bool_string(minio.get("path_style_access", True))
    ssl_enabled = _bool_string(minio.get("ssl_enabled", False))

    return (
        builder.appName(app_name)
        .master(master)
        .config("spark.hadoop.fs.s3a.endpoint", minio.get("endpoint", "http://minio:9000"))
        .config("spark.hadoop.fs.s3a.access.key", access_key)
        .config("spark.hadoop.fs.s3a.secret.key", secret_key)
        .config("spark.hadoop.fs.s3a.path.style.access", path_style_access)
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", ssl_enabled)
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
    )


def load_spark_config(path: str | Path = "configs/spark_config.yaml") -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def build_spark_session(config_path: str | Path = "configs/spark_config.yaml") -> Any:
    try:
        from pyspark.sql import SparkSession
    except ImportError as exc:
        raise RuntimeError(
            "PySpark is required for local MinIO Parquet jobs. "
            "Install the runtime dependencies before running Stage 1 evidence jobs."
        ) from exc

    builder = configure_spark_builder(SparkSession.builder, load_spark_config(config_path))
    return builder.getOrCreate()
