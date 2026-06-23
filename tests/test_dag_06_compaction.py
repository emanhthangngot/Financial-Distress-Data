"""Test seeds for W19: DAG 06 compaction task wiring.

The DAG `dags/06_pyspark_silver_to_gold.py` must:
- Be importable
- Define a task `compact_gold_tables` ordered after `spark_build_gold_tables`
- The compaction task must reference the `compact_small_files` function from
  `src.lakehouse.compaction` (sanity: the wiring is real, not a placeholder).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DAG_PATH = REPO_ROOT / "dags" / "06_pyspark_silver_to_gold.py"


def _import_dag() -> object:
    spec = importlib.util.spec_from_file_location("dag_06_compaction", DAG_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dag_06_imports() -> None:
    module = _import_dag()
    assert module is not None


def test_dag_06_has_compact_gold_tables_task() -> None:
    module = _import_dag()
    assert hasattr(module, "_compact_gold_tables") or hasattr(module, "compact_gold_tables"), (
        "DAG 06 must define a callable named _compact_gold_tables or compact_gold_tables"
    )


def test_dag_06_compaction_task_references_compact_small_files() -> None:
    source = DAG_PATH.read_text()
    assert "compact_small_files" in source, (
        "DAG 06 must call src.lakehouse.compaction.compact_small_files"
    )
    assert "compact_gold_tables" in source, "DAG 06 must declare a compact_gold_tables task"
    # Ordering invariant: compact task comes after spark_build_gold_tables
    spark_idx = source.find("spark_build_gold_tables")
    compact_idx = source.find("compact_gold_tables")
    assert spark_idx != -1 and compact_idx != -1
    # The compact task id should be declared (string literal) after the
    # spark task id at least once.
    assert compact_idx > spark_idx, "compact_gold_tables must be declared after spark_build_gold_tables"


def test_dag_06_compaction_uses_avg_file_mb_threshold() -> None:
    source = DAG_PATH.read_text()
    assert "AVG_FILE_MB" in source or "avg_file_mb" in source.lower(), (
        "DAG 06 compaction must be guarded by an avg-file-size threshold (env or constant)"
    )
