"""Target-plan mutation tests using aliases loaded from mutmut's tree."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

MUTANT_ROOT = Path(__file__).resolve().parents[3]


def load_alias(alias: str, relative_path: str) -> ModuleType:
    path = MUTANT_ROOT / relative_path
    assert MUTANT_ROOT.name == "mutants"
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
