from __future__ import annotations

from typing import Any


def bronze_to_silver_spark(
    dataframe: Any,
    required: list[str],
    nullable: list[str],
    dedup_keys: list[str],
    *,
    field_types: dict[str, str] | None = None,
    enum_values: dict[str, list[Any]] | None = None,
    blank_as_null: bool = True,
    preserve_vintages: bool = False,
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
        normalized = normalized.withColumn(field, F.lit(None).cast("string"))

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

    raw_payload = F.to_json(F.struct(*[F.col(column) for column in normalized.columns]))
    if blank_as_null:
        for field in [*required, *nullable]:
            if field in normalized.columns:
                normalized = normalized.withColumn(
                    field,
                    F.when(F.trim(F.col(field).cast("string")) == "", F.lit(None)).otherwise(
                        F.col(field)
                    ),
                )

    spark_types = {
        "string": "string",
        "integer": "long",
        "float": "double",
        "boolean": "boolean",
        "date": "date",
        "timestamp": "timestamp",
    }
    invalid_expr = F.lit(False)
    for field, field_type in (field_types or {}).items():
        if field not in normalized.columns:
            continue
        original = F.col(field)
        casted = original.cast(spark_types[field_type])
        invalid_expr = invalid_expr | (original.isNotNull() & casted.isNull())
        normalized = normalized.withColumn(field, casted)
    for field, allowed in (enum_values or {}).items():
        if field in normalized.columns:
            invalid_expr = invalid_expr | (
                F.col(field).isNotNull() & ~F.col(field).isin(list(allowed))
            )

    if preserve_vintages:
        knowledge_candidates = [
            F.col(field).cast("timestamp")
            for field in (
                "known_from_ts",
                "report_release_date",
                "event_timestamp",
                "created_ts",
            )
            if field in normalized.columns
        ]
        if not knowledge_candidates:
            raise ValueError(
                "known_from_ts or a source timestamp column is required to preserve vintages"
            )
        if "known_from_ts" in normalized.columns:
            explicit_known = F.col("known_from_ts")
            invalid_expr = invalid_expr | (
                explicit_known.isNotNull() & explicit_known.cast("timestamp").isNull()
            )
        normalized = normalized.withColumn("known_from_ts", F.coalesce(*knowledge_candidates))
        if "known_from_ts" not in all_fields:
            all_fields.append("known_from_ts")
    missing_required_expr = None
    for field in required:
        condition = F.col(field).isNull()
        missing_required_expr = (
            condition if missing_required_expr is None else missing_required_expr | condition
        )
    if preserve_vintages:
        missing_required_expr = missing_required_expr | F.col("known_from_ts").isNull()

    failed = (
        normalized.filter(missing_required_expr | invalid_expr)
        .withColumn(
            "failure_reason",
            F.when(missing_required_expr, F.lit("missing required fields")).otherwise(
                F.lit("invalid typed fields")
            ),
        )
        .withColumn("raw_payload", raw_payload)
    )
    valid = normalized.filter(~missing_required_expr & ~invalid_expr).select(*all_fields)
    if preserve_vintages:
        vintage_window = Window.partitionBy(*dedup_keys, "known_from_ts").orderBy(
            F.col("created_ts").desc_nulls_last()
        )
        latest_window = Window.partitionBy(*dedup_keys).orderBy(
            F.col("known_from_ts").desc(), F.col("created_ts").desc_nulls_last()
        )
        silver = (
            valid.withColumn("_vintage_row_number", F.row_number().over(vintage_window))
            .filter(F.col("_vintage_row_number") == 1)
            .drop("_vintage_row_number")
            .withColumn("_latest_row_number", F.row_number().over(latest_window))
            .withColumn("is_latest_vintage", F.col("_latest_row_number") == 1)
            .drop("_latest_row_number")
        )
    else:
        window = Window.partitionBy(*dedup_keys).orderBy(F.col("created_ts").desc_nulls_last())
        silver = (
            valid.withColumn("_row_number", F.row_number().over(window))
            .filter(F.col("_row_number") == 1)
            .drop("_row_number")
        )
    return silver, failed
