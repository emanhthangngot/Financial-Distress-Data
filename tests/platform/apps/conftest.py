from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

pytest.importorskip(
    "fastapi",
    reason="platform .pp tests require .venv-platform; the platform .venv stays dependency-clean",
)
pytest.importorskip(
    "httpx",
    reason="platform .pp tests require .venv-platform; the platform .venv stays dependency-clean",
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def load_app_module(app_name: str, module_name: str) -> ModuleType:
    package_path = REPO_ROOT / "apps" / app_name / "app"
    path = package_path / f"{module_name}.py"
    package_name = f"phase2_{app_name.replace('-', '_')}_app"
    if package_name not in sys.modules:
        package = ModuleType(package_name)
        package.__path__ = [str(package_path)]
        sys.modules[package_name] = package
    unique_name = f"{package_name}.{module_name}"
    spec = importlib.util.spec_from_file_location(unique_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = module
    spec.loader.exec_module(module)
    return module
