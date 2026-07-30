"""Rollback-capable promotion of staged MinIO dataset prefixes."""

from __future__ import annotations

from typing import Any

from src.io.minio_writer import clear_minio_prefix


def _copy_prefix(client: Any, bucket: str, source_prefix: str, target_prefix: str) -> int:
    from minio.commonconfig import CopySource

    count = 0
    for item in client.list_objects(bucket, source_prefix, recursive=True):
        relative = item.object_name.removeprefix(source_prefix)
        client.copy_object(
            bucket,
            f"{target_prefix}{relative}",
            CopySource(bucket, item.object_name),
        )
        count += 1
    return count


def promote_staged_prefixes(
    client: Any,
    bucket: str,
    run_id: str,
    dataset_prefixes: list[str],
) -> None:
    """Promote all staged prefixes and restore the previous snapshot on failure."""
    staging_root = f"_staging/{run_id}/"
    rollback_root = f"_rollback/{run_id}/"
    for prefix in dataset_prefixes:
        if not list(client.list_objects(bucket, f"{staging_root}{prefix}", recursive=True)):
            raise RuntimeError(f"staged dataset is empty: {prefix}")

    try:
        for prefix in dataset_prefixes:
            _copy_prefix(client, bucket, prefix, f"{rollback_root}{prefix}")
        for prefix in dataset_prefixes:
            clear_minio_prefix(client, bucket, prefix)
            _copy_prefix(client, bucket, f"{staging_root}{prefix}", prefix)
    except Exception:
        for prefix in dataset_prefixes:
            clear_minio_prefix(client, bucket, prefix)
            _copy_prefix(client, bucket, f"{rollback_root}{prefix}", prefix)
        raise
    finally:
        clear_minio_prefix(client, bucket, staging_root)
        clear_minio_prefix(client, bucket, rollback_root)
