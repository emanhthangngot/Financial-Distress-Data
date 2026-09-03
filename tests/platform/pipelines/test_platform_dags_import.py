"""Pins the flattened platform DAG modules: zero import-time side effects,
filename-aligned DAG IDs, and no collisions with other DAGs. Airflow is not
installed in ``.venv`` (only in the Airflow container image), so
``airflow_imports()`` returns ``(None, None)`` here and the DAG object is
never built — this test instead proves the module *imports cleanly* under
that fallback, which is exactly the path a socket/filesystem guard would
also need to survive."""

from __future__ import annotations

import builtins
import importlib.util
import re
import socket
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DAGS_DIR = REPO_ROOT / "dags"
PLATFORM_DAG_STEMS = {
    "rag_ingest",
    "feature_materialize",
    "stream_feature_offline",
    "stream_feature_online",
    "label_drift_build",
    "cdc_reconciliation",
    "drift_monitoring",
}
PLATFORM_DAG_FILES = sorted(DAGS_DIR / f"{stem}.py" for stem in PLATFORM_DAG_STEMS)


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load module at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _guarded_import(path: Path, name: str, monkeypatch: pytest.MonkeyPatch):
    """Blocks real socket connections and disk writes during import — a
    module that tries either at import time (rather than inside a function,
    per D4/the DAG zero-side-effect rule) fails loudly here instead of
    silently working in this sandbox and breaking in a stricter one."""
    real_open = builtins.open

    def _no_socket(*args, **kwargs):
        raise AssertionError(f"{path.name} opened a socket at import time")

    def _no_write_open(file, mode="r", *args, **kwargs):
        if "w" in mode or "a" in mode or "x" in mode:
            raise AssertionError(f"{path.name} opened {file!r} for writing at import time")
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(socket, "socket", _no_socket)
    monkeypatch.setattr(builtins, "open", _no_write_open)
    return _load_module(path, name)


@pytest.mark.parametrize("path", PLATFORM_DAG_FILES, ids=lambda p: p.stem)
def test_dag_module_imports_without_side_effects(
    path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _guarded_import(path, f"_platform_dag_{path.stem}", monkeypatch)
    assert hasattr(module, "DAG_ID")
    assert hasattr(module, "DAG")


@pytest.mark.parametrize("path", PLATFORM_DAG_FILES, ids=lambda p: p.stem)
def test_dag_id_matches_filename(path: Path) -> None:
    module = _load_module(path, f"_platform_dagid_{path.stem}")
    assert module.DAG_ID == path.stem


@pytest.mark.parametrize("path", PLATFORM_DAG_FILES, ids=lambda p: p.stem)
def test_dag_object_is_none_without_airflow_installed(path: Path) -> None:
    # Documents the actual state of this venv (no airflow) rather than
    # assuming it — if airflow becomes a `.venv` dependency later this
    # assertion is the signal to also assert real DAG/task wiring.
    import importlib.util as _ilu

    module = _load_module(path, f"_platform_dagnone_{path.stem}")
    if _ilu.find_spec("airflow") is None:
        assert module.DAG is None


_PLATFORM_DAG_IDS = {
    _load_module(path, f"_platform_collect_{path.stem}").DAG_ID
    for path in PLATFORM_DAG_FILES
}


def test_platform_dag_ids_do_not_collide_with_other_dag_ids() -> None:
    other_dag_ids: set[str] = set()
    for path in DAGS_DIR.glob("*.py"):
        if path in PLATFORM_DAG_FILES or path.name.startswith("_"):
            continue
        match = re.search(r'^DAG_ID\s*=\s*"([^"]+)"', path.read_text(encoding="utf-8"), re.M)
        if match:
            other_dag_ids.add(match.group(1))
    assert other_dag_ids, "sanity check: expected to find at least one other DAG_ID"
    assert _PLATFORM_DAG_IDS.isdisjoint(other_dag_ids)


def test_every_platform_dag_id_is_unique() -> None:
    ids = [_load_module(p, f"_platform_uniq_{p.stem}").DAG_ID for p in PLATFORM_DAG_FILES]
    assert len(ids) == len(set(ids))


def test_expected_platform_dag_files_present() -> None:
    assert all(path.is_file() for path in PLATFORM_DAG_FILES)
