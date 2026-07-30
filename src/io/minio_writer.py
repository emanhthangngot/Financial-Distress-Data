"""
MinIO/S3 writer for the financial-distress lakehouse.

Thin wrapper around the S3A filesystem with helpers to write partitioned Parquet, append to Bronze,
and overwrite Silver/Gold partitions idempotently. All paths go through ``src.io.paths`` so bucket
and zone conventions stay consistent.
"""

from __future__ import annotations

import io
from typing import Any


def _field_names(rows: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    return names


def _arrow_type(values: list[Any]) -> Any:
    import pyarrow as pa

    non_null = [value for value in values if value is not None]
    if not non_null:
        return pa.string()
    if all(isinstance(value, bool) for value in non_null):
        return pa.bool_()
    if all(isinstance(value, int) and not isinstance(value, bool) for value in non_null):
        return pa.int64()
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in non_null):
        return pa.float64()
    return pa.string()


def rows_to_parquet_bytes(rows: list[dict[str, Any]]) -> bytes:
    import pyarrow as pa
    import pyarrow.parquet as pq

    fields = _field_names(rows)
    arrays = []
    for field in fields:
        values = [row.get(field) for row in rows]
        arrow_type = _arrow_type(values)
        if pa.types.is_string(arrow_type):
            values = [None if value is None else str(value) for value in values]
        arrays.append(pa.array(values, type=arrow_type))

    table = pa.Table.from_arrays(arrays, names=fields)
    output = io.BytesIO()
    pq.write_table(table, output)
    return output.getvalue()


def write_minio_dataset(
    client: Any,
    bucket: str,
    bucket_and_key: str,
    rows: list[dict[str, Any]],
) -> None:
    object_key = bucket_and_key.removeprefix(f"{bucket}/")
    data = rows_to_parquet_bytes(rows)
    client.put_object(
        bucket,
        object_key,
        io.BytesIO(data),
        len(data),
        content_type="application/octet-stream",
    )


def write_minio_bytes(
    client: Any,
    bucket: str,
    object_key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> None:
    client.put_object(
        bucket,
        object_key,
        io.BytesIO(data),
        len(data),
        content_type=content_type,
    )


def write_minio_text(
    client: Any,
    bucket: str,
    object_key: str,
    text: str,
    content_type: str = "text/plain",
) -> None:
    write_minio_bytes(
        client,
        bucket,
        object_key,
        text.encode("utf-8"),
        content_type=content_type,
    )


def clear_minio_prefix(client: Any, bucket: str, prefix: str) -> int:
    from minio.deleteobjects import DeleteObject

    objects = [DeleteObject(item.object_name) for item in client.list_objects(bucket, prefix, True)]
    if not objects:
        return 0
    errors = list(client.remove_objects(bucket, objects))
    if errors:
        first = errors[0]
        raise RuntimeError(f"failed to clear MinIO prefix {prefix}: {first}")
    return len(objects)
