"""Target-plan mutation tests using aliases loaded from mutmut's tree."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

MUTANT_ROOT = Path(__file__).resolve().parents[3]


def load_alias(alias: str, relative_path: str) -> ModuleType:
    key = "src." + alias
    existing = sys.modules.get(key)
    if existing is not None:
        return existing
    path = MUTANT_ROOT / relative_path
    assert path.is_relative_to(MUTANT_ROOT)
    assert path.exists()
    spec = importlib.util.spec_from_file_location(alias, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


def test_reproducibility_manifest_alias_contract() -> None:
    module = load_alias("ml.reproducibility_manifest", "src/ml/reproducibility_manifest.py")
    manifest = module.build_manifest(
        "snapshot-42",
        source_sha="abc",
        image_digest="sha256:def",
        environment={"lock": "ghi"},
        data_version="v1",
        compute_source="local",
        compute_seconds=2,
        accelerator="cpu",
        marginal_cost_usd=0,
    )
    expected = module.build_manifest(
        "snapshot-42",
        source_sha="abc",
        image_digest="sha256:def",
        environment={"lock": "ghi"},
        data_version="v1",
        compute_source="local",
        compute_seconds=2,
        accelerator="cpu",
        marginal_cost_usd=0,
    )
    assert manifest.snapshot_id == "snapshot-42"
    assert manifest.digest() == expected.digest()
    assert manifest.to_json() == expected.to_json()


def test_current_source_sha_success_and_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_alias("ml.reproducibility_manifest", "src/ml/reproducibility_manifest.py")
    recorded: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def successful_run(*args: object, **kwargs: object) -> SimpleNamespace:
        recorded.append((args, kwargs))
        return SimpleNamespace(stdout="abc123\n")

    monkeypatch.setattr(module.subprocess, "run", successful_run)
    assert module.current_source_sha(cwd="/x") == "abc123"
    assert recorded == [
        (
            (["git", "rev-parse", "HEAD"],),
            {"cwd": "/x", "check": True, "capture_output": True, "text": True},
        )
    ]

    def raise_called_process_error(*args: object, **kwargs: object) -> None:
        raise subprocess.CalledProcessError(1, "git")

    monkeypatch.setattr(module.subprocess, "run", raise_called_process_error)
    assert module.current_source_sha() == "unknown"

    def raise_os_error(*args: object, **kwargs: object) -> None:
        raise OSError("git missing")

    monkeypatch.setattr(module.subprocess, "run", raise_os_error)
    assert module.current_source_sha() == "unknown"


@pytest.mark.parametrize(
    "overrides",
    [
        {"snapshot_id": ""},
        {"compute_source": "remote"},
        {"compute_seconds": -1},
        {"accelerator": ""},
        {"marginal_cost_usd": -1},
    ],
)
def test_build_manifest_rejects_invalid_inputs(overrides: dict[str, object]) -> None:
    module = load_alias("ml.reproducibility_manifest", "src/ml/reproducibility_manifest.py")
    overrides = dict(overrides)
    kwargs: dict[str, object] = {
        "source_sha": "abc",
        "image_digest": "sha256:def",
        "environment": {"lock": "ghi"},
        "compute_source": "local",
        "compute_seconds": 2,
        "accelerator": "cpu",
        "marginal_cost_usd": 0,
    }
    snapshot_id = str(overrides.pop("snapshot_id", "snapshot-42"))
    kwargs.update(overrides)
    with pytest.raises(ValueError):
        module.build_manifest(snapshot_id, **kwargs)
