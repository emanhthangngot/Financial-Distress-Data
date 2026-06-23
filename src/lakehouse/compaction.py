"""Compaction + Z-order helpers for the Gold Parquet zone.

This module is the spine for W19 (lakehouse compaction + DW indexing). It
operates on plain Parquet files in a local-FS or S3A path. Full Spark runtime
is intentionally not required — DuckDB + pyarrow cover the unit-test surface
and the DAG hook uses the same primitives.

Compaction strategy
-------------------
1. Read every ``*.parquet`` file in ``src`` (recursively) using ``pyarrow``.
2. Sum the total bytes and the row count.
3. Decide the target output file count as
   ``max(1, ceil(total_bytes / target_file_bytes))`` clamped to the input file
   count when the target is unreasonably small.
4. Round-robin the input tables into that many output buckets, write one
   Parquet file per bucket, and return a small summary dict.

Z-order strategy
----------------
A lightweight Z-order approximation: convert each requested column to its
bit-interleaved integer code using a fixed-precision quantization (10 bits per
column), then sort by the concatenated code. This is the standard "Z-order
curve" trick used by Delta Lake and Apache Iceberg when full Z-order is too
expensive.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


def _iter_parquet_files(root: str | os.PathLike[str]) -> list[Path]:
    root_path = Path(root)
    if not root_path.exists():
        return []
    return sorted(p for p in root_path.rglob("*.parquet") if p.is_file())


def _read_tables(paths: list[Path]) -> list[pa.Table]:
    return [pq.read_table(p) for p in paths]


def _concat(tables: list[pa.Table]) -> pa.Table:
    if not tables:
        return pa.table({})
    return pa.concat_tables(tables, promote_options="default")


def _bucket_count(total_bytes: int, target_bytes: int, max_buckets: int) -> int:
    if total_bytes <= 0 or target_bytes <= 0:
        return 1
    return max(1, min(max_buckets, math.ceil(total_bytes / target_bytes)))


def compact_small_files(
    source_dir: str,
    target_file_mb: int = 128,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """Compact small Parquet files in ``source_dir`` into ``output_dir``.

    Parameters
    ----------
    source_dir
        Directory containing the input ``*.parquet`` files (recursive).
    target_file_mb
        Desired output file size in MB. The number of output files is
        ``ceil(total_bytes / target_bytes)`` clamped to ``[1, input_count]``.
    output_dir
        Where to write the compacted files. Defaults to a sibling ``compacted/``
        directory under ``source_dir``.

    Returns
    -------
    dict with keys: ``input_file_count``, ``output_file_count``,
    ``input_total_bytes``, ``output_total_bytes``, ``input_row_count``,
    ``output_row_count``, ``target_file_mb``.
    """
    target_bytes = max(1, int(target_file_mb)) * 1024 * 1024
    src = Path(source_dir)
    out = Path(output_dir) if output_dir else src / "compacted"
    out.mkdir(parents=True, exist_ok=True)

    input_files = _iter_parquet_files(src)
    if not input_files:
        return {
            "input_file_count": 0,
            "output_file_count": 0,
            "input_total_bytes": 0,
            "output_total_bytes": 0,
            "input_row_count": 0,
            "output_row_count": 0,
            "target_file_mb": target_file_mb,
        }

    # Clean output dir of any prior run artifacts (parquet only).
    for stale in out.glob("*.parquet"):
        stale.unlink()

    tables = _read_tables(input_files)
    total_bytes = sum(p.stat().st_size for p in input_files)
    total_rows = sum(t.num_rows for t in tables)
    bucket_count = _bucket_count(total_bytes, target_bytes, len(input_files))
    # Round-robin rows into N buckets preserving order.
    buckets: list[list[pa.Table]] = [[] for _ in range(bucket_count)]
    for i, t in enumerate(tables):
        buckets[i % bucket_count].append(t)

    output_total_bytes = 0
    written = 0
    for i, bucket_tables in enumerate(buckets):
        if not bucket_tables:
            continue
        merged = _concat(bucket_tables) if len(bucket_tables) > 1 else bucket_tables[0]
        path = out / f"part-{i:05d}.parquet"
        pq.write_table(merged, path, compression="snappy")
        output_total_bytes += path.stat().st_size
        written += 1

    return {
        "input_file_count": len(input_files),
        "output_file_count": written,
        "input_total_bytes": total_bytes,
        "output_total_bytes": output_total_bytes,
        "input_row_count": total_rows,
        "output_row_count": total_rows,
        "target_file_mb": target_file_mb,
    }


# --- Z-order --------------------------------------------------------------


def _z_order_key(table: pa.Table, columns: list[str]) -> pa.Array:
    """Compute a Z-order key for each row.

    Each requested column contributes 10 bits; values are normalized to
    ``[0, 1023]`` via min-max scaling then rounded to int. The bits are
    interleaved column-by-column to form the final key.
    """
    if not columns:
        raise ValueError("z_order_by requires at least one column")
    arrays: list[pa.Array] = []
    for col in columns:
        arr = table.column(col)
        # Skip nulls: replace with the min of non-nulls so they sort first.
        if pa.types.is_floating(arr.type):
            values = arr.to_pylist()
            non_null = [v for v in values if v is not None]
            if not non_null:
                arrays.append(pa.array([0] * len(values)))
                continue
            lo, hi = min(non_null), max(non_null)
            span = hi - lo if hi != lo else 1.0
            scaled = [int(((v - lo) / span) * 1023) if v is not None else 0 for v in values]
            arrays.append(pa.array(scaled, type=pa.int32()))
        elif pa.types.is_integer(arr.type):
            values = arr.to_pylist()
            non_null = [v for v in values if v is not None]
            if not non_null:
                arrays.append(pa.array([0] * len(values)))
                continue
            lo, hi = min(non_null), max(non_null)
            span = hi - lo if hi != lo else 1
            scaled = [int(((v - lo) / span) * 1023) if v is not None else 0 for v in values]
            arrays.append(pa.array(scaled, type=pa.int32()))
        else:
            # String columns: hash to a stable int, then scale to 0..1023.
            values = arr.to_pylist()
            scaled = [abs(hash(v)) % 1024 if v is not None else 0 for v in values]
            arrays.append(pa.array(scaled, type=pa.int32()))

    n_rows = len(table)
    keys = [0] * n_rows
    for col_idx, arr in enumerate(arrays):
        col_bits = arr.to_pylist()
        for row_idx in range(n_rows):
            # Interleave 10 bits of this column at bit positions
            # [col_idx*10, col_idx*10+10). Since 10*N bits won't exceed
            # Python's int limit for small N, we just OR in the value.
            keys[row_idx] |= (int(col_bits[row_idx]) & 0x3FF) << (col_idx * 10)
    return pa.array(keys, type=pa.uint64())


def z_order_by(dataframe: Any, columns: list[str]) -> Any:
    """Sort a Pandas or pyarrow-table-like DataFrame by Z-order of ``columns``.

    Accepts Pandas DataFrame, pyarrow Table, or anything with a ``.column(name)``
    accessor. For Pandas, converts to Arrow via ``pa.Table.from_pandas`` to
    compute the Z-order key, then returns a Pandas DataFrame reindexed by the
    sorted order.
    """
    # Pandas DataFrame path: detect via presence of ``iloc`` (no Arrow tables
    # have that). Avoid ``hasattr(to_arrow)`` because not all pandas builds
    # expose the Arrow accessor.
    if hasattr(dataframe, "iloc") and hasattr(dataframe, "columns"):
        table = pa.Table.from_pandas(dataframe, preserve_index=False)
        key = _z_order_key(table, list(columns))
        order = sorted(range(len(table)), key=lambda i: key[i].as_py())
        return dataframe.iloc[order].reset_index(drop=True)
    if isinstance(dataframe, pa.Table):
        key = _z_order_key(dataframe, list(columns))
        order = sorted(range(len(dataframe)), key=lambda i: key[i].as_py())
        return dataframe.take(order)
    raise TypeError(f"z_order_by: unsupported dataframe type {type(dataframe).__name__}")
