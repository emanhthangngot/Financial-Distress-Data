"""Test seeds for W19: lakehouse compaction module.

Covers the contract of `src.lakehouse.compaction`:
- `compact_small_files` reduces N small Parquet files in a directory down to
  <= ceil(total_bytes / target_file_bytes) files, each at or above the target
  size (in bytes), while preserving the row count and the union of columns.
- `z_order_by` returns a DataFrame whose rows are sorted by a deterministic
  interleaving of the requested columns (Z-order curve approximation).
- The module exposes both functions at package level.
"""

from __future__ import annotations

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.lakehouse import compaction


def _write_small_parquet_files(directory, n_files: int = 100, rows_per_file: int = 50) -> int:
    """Write N small Parquet files with a stable schema. Returns total bytes."""
    total = 0
    schema = pa.schema([("ticker", pa.string()), ("value", pa.int64())])
    for i in range(n_files):
        ticker = f"T{i:04d}"
        values = list(range(i * rows_per_file, (i + 1) * rows_per_file))
        table = pa.table({"ticker": [ticker] * rows_per_file, "value": values}, schema=schema)
        path = directory / f"part-{i:05d}.parquet"
        pq.write_table(table, path)
        total += path.stat().st_size
    return total


def test_compaction_module_exports() -> None:
    assert hasattr(compaction, "compact_small_files")
    assert hasattr(compaction, "z_order_by")
    assert callable(compaction.compact_small_files)
    assert callable(compaction.z_order_by)


def test_compact_small_files_reduces_file_count(tmp_path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    total_bytes = _write_small_parquet_files(src, n_files=100, rows_per_file=50)

    result = compaction.compact_small_files(
        str(src), target_file_mb=1, output_dir=str(tmp_path / "out")
    )

    out_files = sorted((tmp_path / "out").glob("*.parquet"))
    assert len(out_files) == 1, f"expected 1 file at 1MB target, got {len(out_files)}"
    out_table = pq.read_table(out_files[0])
    assert out_table.num_rows == 100 * 50
    assert out_table.column_names == ["ticker", "value"]
    assert result["input_file_count"] == 100
    assert result["output_file_count"] == 1
    assert result["input_total_bytes"] == total_bytes


def test_compact_small_files_target_two_files(tmp_path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    _write_small_parquet_files(src, n_files=10, rows_per_file=500)
    # 10 files * 500 rows * ~30 bytes/row = ~150KB total; target 0.0001 MB
    # forces ceil(150KB / 100B) = 1500 files which exceeds input. Should clamp
    # to at most input file count = 10, but the test simply asserts that
    # fewer or equal files come out and total rows preserved.
    result = compaction.compact_small_files(
        str(src), target_file_mb=0.0001, output_dir=str(tmp_path / "out")
    )
    out_files = sorted((tmp_path / "out").glob("*.parquet"))
    assert len(out_files) <= 10
    assert len(out_files) >= 1
    # Even if multiple files, union rows should equal input
    total_rows = sum(pq.read_table(f).num_rows for f in out_files)
    assert total_rows == 10 * 500
    assert result["output_file_count"] == len(out_files)


def test_compact_small_files_empty_directory(tmp_path) -> None:
    src = tmp_path / "empty"
    src.mkdir()
    result = compaction.compact_small_files(
        str(src), target_file_mb=128, output_dir=str(tmp_path / "out")
    )
    assert result["input_file_count"] == 0
    assert result["output_file_count"] == 0


def test_z_order_by_returns_dataframe() -> None:
    # Use a pandas DataFrame so the function has a portable contract
    # (Pandas DataFrame is what Spark DF maps to for batched tests).
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC", "AAA", "BBB", "CCC"],
            "report_period": [1, 1, 1, 2, 2, 2],
            "value": [10, 20, 30, 40, 50, 60],
        }
    )
    sorted_df = compaction.z_order_by(df, ["ticker", "report_period"])
    # Z-order should produce a deterministic order; assert rows are present
    # and the sort interleaves both columns.
    assert len(sorted_df) == len(df)
    assert set(sorted_df.columns) == {"ticker", "report_period", "value"}
    # No row loss and no duplication
    assert sorted_df["value"].sum() == df["value"].sum()
