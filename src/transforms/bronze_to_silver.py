from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def normalize_columns(row: dict[str, Any]) -> dict[str, Any]:
    return {str(key).strip().lower(): value for key, value in row.items()}


def align_to_schema(
    row: dict[str, Any], required: list[str], nullable: list[str]
) -> dict[str, Any]:
    normalized = normalize_columns(row)
    missing_required = [field for field in required if normalized.get(field) is None]
    if missing_required:
        raise ValueError(f"missing required fields: {', '.join(missing_required)}")
    return {field: normalized.get(field) for field in [*required, *nullable]}


def deduplicate_latest(rows: Iterable[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    latest: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        business_key = tuple(row.get(key) for key in keys)
        current = latest.get(business_key)
        if current is None or str(row.get("created_ts", "")) >= str(current.get("created_ts", "")):
            latest[business_key] = row
    return list(latest.values())


def bronze_to_silver(
    rows: Iterable[dict[str, Any]],
    required: list[str],
    nullable: list[str],
    dedup_keys: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    valid: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for row in rows:
        try:
            valid.append(align_to_schema(row, required, nullable))
        except ValueError as exc:
            failed.append({"failure_reason": str(exc), "raw_payload": row})
    return deduplicate_latest(valid, dedup_keys), failed


def bronze_to_silver_spark(
    dataframe: Any,
    required: list[str],
    nullable: list[str],
    dedup_keys: list[str],
) -> tuple[Any, Any]:
    try:
        from pyspark.sql import functions as F
        from pyspark.sql.window import Window
    except ImportError as exc:
        raise RuntimeError("PySpark is required for Spark Bronze-to-Silver transforms.") from exc

    normalized = dataframe
    for column_name in dataframe.columns:
        normalized_name = str(column_name).strip().lower()
        if normalized_name != column_name:
            normalized = normalized.withColumnRenamed(column_name, normalized_name)

    missing_nullable = [field for field in nullable if field not in normalized.columns]
    for field in missing_nullable:
        normalized = normalized.withColumn(field, F.lit(None))

    all_fields = [*required, *nullable]
    missing_required_columns = [field for field in required if field not in normalized.columns]
    if missing_required_columns:
        raw_payload = F.to_json(F.struct(*[F.col(column) for column in normalized.columns]))
        failed = normalized.withColumn(
            "failure_reason",
            F.lit(f"missing required columns: {', '.join(missing_required_columns)}"),
        ).withColumn("raw_payload", raw_payload)
        empty_silver = normalized.limit(0).select(
            *[field for field in all_fields if field in normalized.columns]
        )
        return empty_silver, failed

    missing_required_expr = None
    for field in required:
        condition = F.col(field).isNull()
        missing_required_expr = (
            condition if missing_required_expr is None else missing_required_expr | condition
        )

    raw_payload = F.to_json(F.struct(*[F.col(column) for column in normalized.columns]))
    failed = (
        normalized.filter(missing_required_expr)
        .withColumn("failure_reason", F.lit("missing required fields"))
        .withColumn("raw_payload", raw_payload)
    )
    valid = normalized.filter(~missing_required_expr).select(*all_fields)
    window = Window.partitionBy(*dedup_keys).orderBy(F.col("created_ts").desc_nulls_last())
    silver = (
        valid.withColumn("_row_number", F.row_number().over(window))
        .filter(F.col("_row_number") == 1)
        .drop("_row_number")
    )
    return silver, failed
