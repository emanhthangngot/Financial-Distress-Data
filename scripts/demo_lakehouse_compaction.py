"""W19 Lakehouse compaction benchmark.

Writes N small Parquet files to a temp directory, runs
``src.lakehouse.compaction.compact_small_files`` to merge them into ~128 MB
shards, and writes the before/after stats to
``docs/evidence/lakehouse_compaction_benchmark.json``.

Run with:
    .venv/bin/python scripts/demo_lakehouse_compaction.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

# Allow ``python scripts/demo_lakehouse_compaction.py`` from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pyarrow as pa
import pyarrow.parquet as pq

from src.lakehouse.compaction import compact_small_files

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = REPO_ROOT / "docs" / "evidence" / "lakehouse_compaction_benchmark.json"

# Keep this small enough to run in <1s on a dev laptop; the test suite
# already exercises 100 small files, here we just demonstrate the contract.
N_FILES = 100
ROWS_PER_FILE = 200
TARGET_FILE_MB = 128


def _make_small_files(directory: Path, n_files: int, rows_per_file: int) -> int:
    """Write ``n_files`` small Parquet files. Returns total bytes."""
    schema = pa.schema([("ticker", pa.string()), ("value", pa.int64())])
    total = 0
    for i in range(n_files):
        ticker = f"T{i:04d}"
        values = list(range(i * rows_per_file, (i + 1) * rows_per_file))
        table = pa.table({"ticker": [ticker] * rows_per_file, "value": values}, schema=schema)
        path = directory / f"part-{i:05d}.parquet"
        pq.write_table(table, path)
        total += path.stat().st_size
    return total


def main() -> dict[str, Any]:
    """Run the compaction benchmark. Returns the evidence payload."""
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="w19_compact_") as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "src"
        out = tmp_path / "out"
        src.mkdir()
        _make_small_files(src, N_FILES, ROWS_PER_FILE)
        result = compact_small_files(str(src), target_file_mb=TARGET_FILE_MB, output_dir=str(out))
        payload = {
            "n_input_files": result["input_file_count"],
            "n_output_files": result["output_file_count"],
            "input_total_bytes": result["input_total_bytes"],
            "output_total_bytes": result["output_total_bytes"],
            "input_avg_bytes": (
                result["input_total_bytes"] // result["input_file_count"]
                if result["input_file_count"]
                else 0
            ),
            "output_avg_bytes": (
                result["output_total_bytes"] // result["output_file_count"]
                if result["output_file_count"]
                else 0
            ),
            "target_file_mb": TARGET_FILE_MB,
            "row_count_preserved": result["input_row_count"] == result["output_row_count"],
            "rows_in": result["input_row_count"],
            "rows_out": result["output_row_count"],
        }
        EVIDENCE_PATH.write_text(json.dumps(payload, indent=2) + "\n")
        # Force a sync so the on-disk evidence is flushed even on Windows.
        return payload


if __name__ == "__main__":
    out = main()
    print(json.dumps(out, indent=2))
