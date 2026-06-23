"""Test seeds for W19: DuckDB index demo script.

The script `scripts/demo_duckdb_index.py` must:
- Exist at that exact path
- Be importable (no top-level side effects beyond defining `main` and helpers)
- Define a callable `main()` that runs the benchmark
- On success produce `docs/evidence/duckdb_index_benchmark.json` with the
  required keys: `query`, `before_ms`, `after_ms`, `speedup_factor`
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "demo_duckdb_index.py"
EVIDENCE_PATH = REPO_ROOT / "docs" / "evidence" / "duckdb_index_benchmark.json"
REQUIRED_KEYS = {"query", "before_ms", "after_ms", "speedup_factor"}


def test_script_exists() -> None:
    assert SCRIPT_PATH.is_file(), f"missing {SCRIPT_PATH}"


def test_script_has_main_callable() -> None:
    spec = importlib.util.spec_from_file_location("demo_duckdb_index", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(getattr(module, "main", None)), "demo_duckdb_index.main must be callable"


def test_evidence_json_shape() -> None:
    # The test does not execute the script (that needs a running Spark env or
    # seeded DuckDB) — it asserts the file's contract when produced.
    if not EVIDENCE_PATH.is_file():
        pytest_skip = True
        import pytest

        pytest.skip(f"{EVIDENCE_PATH} not yet produced; run scripts/demo_duckdb_index.py first")
    payload = json.loads(EVIDENCE_PATH.read_text())
    missing = REQUIRED_KEYS - payload.keys()
    assert not missing, f"duckdb_index_benchmark.json missing keys: {missing}"
    assert isinstance(payload["before_ms"], (int, float))
    assert isinstance(payload["after_ms"], (int, float))
    assert isinstance(payload["speedup_factor"], (int, float))
    assert payload["speedup_factor"] >= 1.0, "speedup_factor must be >= 1.0"
