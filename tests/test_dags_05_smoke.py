"""W9 — DAG 05 smoke helper must fail-fast on a bad bronze row.

The DAG 05 smoke helper currently calls ``bronze_to_silver`` and ignores
its ``failed`` list, so a single invalid bronze row silently passes
through. W9 AC: capture ``failed`` and raise ``AirflowFailException``
when non-empty.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

from src.metadata.schema_registry import InMemorySchemaRegistry


def _load_dag_module(stem: str):
    """DAG files start with digits, so we cannot `import dags.05_...`.

    Load the module by file path instead.
    """
    repo_root = Path(__file__).resolve().parent.parent
    path = repo_root / "dags" / f"{stem}.py"
    spec = importlib.util.spec_from_file_location(f"_w9_{stem}", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Cannot load DAG module at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_dag05 = _load_dag_module("05_transform_bronze_to_silver")


def test_dag05_smoke_helper_raises_on_invalid_bronze_row():
    """An invalid bronze row must propagate as AirflowFailException."""
    contract = InMemorySchemaRegistry().get_current("companies")
    # Missing 'company_name' (required) — must land in failed[].
    bad_row = {
        "ticker": "AAA",
        # 'company_name' deliberately omitted
        "exchange": "HOSE",
        "created_ts": "2026-01-01T00:00:00+00:00",
    }
    with pytest.raises(Exception) as exc_info:
        _dag05._transform_smoke_run(
            [bad_row],
            contract.required,
            contract.nullable,
        )
    # The exception should originate from Airflow's fail-fast primitive,
    # or — when Airflow is not installed — a clear RuntimeError with the
    # failed-row count.
    msg = str(exc_info.value)
    assert "failed" in msg.lower() or "airflow" in msg.lower()


def test_dag05_smoke_helper_passes_on_valid_bronze_row():
    """A valid bronze row set must not raise."""
    contract = InMemorySchemaRegistry().get_current("companies")
    rows = [
        {
            "ticker": "AAA",
            "company_name": "AAA Corp",
            "exchange": "HOSE",
            "created_ts": "2026-01-01T00:00:00+00:00",
        }
    ]
    result = _dag05._transform_smoke_run(
        rows,
        contract.required,
        contract.nullable,
    )
    assert result is not None
