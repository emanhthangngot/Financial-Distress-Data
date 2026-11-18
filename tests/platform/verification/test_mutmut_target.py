"""Target-plan mutation tests using aliases loaded from mutmut's tree."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from datetime import datetime
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


def test_canonical_digest_uses_sorted_compact_json() -> None:
    module = load_alias("ml.reproducibility_manifest", "src/ml/reproducibility_manifest.py")

    assert (
        module._canonical_digest({"z": "đồng", "a": datetime(2026, 1, 1)})
        == "fab65381e5c091d55d8737c157024c6bb3e89a3af8c773f482b4f0c320d990cb"
    )


@pytest.mark.parametrize(
    ("source_key", "source_value"),
    [
        ("SOURCE_SHA", "source-123"),
        ("GIT_SHA", "git-456"),
    ],
)
def test_manifest_from_env_reads_values_and_defaults(
    monkeypatch: pytest.MonkeyPatch,
    source_key: str,
    source_value: str,
) -> None:
    module = load_alias("ml.reproducibility_manifest", "src/ml/reproducibility_manifest.py")
    for key in (
        "SOURCE_SHA",
        "GIT_SHA",
        "IMAGE_DIGEST",
        "REQUIREMENTS_LOCK_SHA",
        "DATA_VERSION",
        "COMPUTE_SOURCE",
        "COMPUTE_SECONDS",
        "ACCELERATOR",
        "MARGINAL_COST_USD",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(module.platform, "python_version", lambda: "3.11.0")
    monkeypatch.setattr(module.platform, "platform", lambda: "test-platform")
    monkeypatch.setenv(source_key, source_value)
    monkeypatch.setenv("IMAGE_DIGEST", "sha256:image")
    monkeypatch.setenv("REQUIREMENTS_LOCK_SHA", "lock-789")
    monkeypatch.setenv("DATA_VERSION", "data-v1")
    monkeypatch.setenv("COMPUTE_SOURCE", "local")
    monkeypatch.setenv("COMPUTE_SECONDS", "2.5")
    monkeypatch.setenv("ACCELERATOR", "cpu")
    monkeypatch.setenv("MARGINAL_COST_USD", "0.25")

    manifest = module.manifest_from_env("snapshot-env")

    assert manifest.snapshot_id == "snapshot-env"
    assert manifest.source_sha == source_value
    assert manifest.image_digest == "sha256:image"
    assert (
        manifest.environment_digest
        == "9a73ed4ebc32b14cccbe28e127cfbaa3b420c8170004a680278e5b6d7b283fd2"
    )
    assert manifest.data_version == "data-v1"
    assert manifest.compute_source == "local"
    assert manifest.compute_seconds == 2.5
    assert manifest.accelerator == "cpu"
    assert manifest.marginal_cost_usd == 0.25


def test_manifest_from_env_defaults_optional_values(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_alias("ml.reproducibility_manifest", "src/ml/reproducibility_manifest.py")
    for key in (
        "SOURCE_SHA",
        "GIT_SHA",
        "IMAGE_DIGEST",
        "REQUIREMENTS_LOCK_SHA",
        "DATA_VERSION",
        "COMPUTE_SOURCE",
        "COMPUTE_SECONDS",
        "ACCELERATOR",
        "MARGINAL_COST_USD",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(module.platform, "python_version", lambda: "3.11.0")
    monkeypatch.setattr(module.platform, "platform", lambda: "test-platform")
    monkeypatch.setenv("GIT_SHA", "fallback-git")
    monkeypatch.setenv("COMPUTE_SOURCE", "gke")
    monkeypatch.setenv("COMPUTE_SECONDS", "0")
    monkeypatch.setenv("ACCELERATOR", "gpu")
    monkeypatch.setenv("MARGINAL_COST_USD", "0")

    manifest = module.manifest_from_env("snapshot-defaults")

    assert manifest.source_sha == "fallback-git"
    assert manifest.image_digest == "unknown"
    assert (
        manifest.environment_digest
        == "229390a59be29bf43da92fefb171e0aedc1075951180ba89f44ae3d1db52120b"
    )
    assert manifest.data_version is None


def test_manifest_from_env_uses_runtime_source_when_sha_vars_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_alias("ml.reproducibility_manifest", "src/ml/reproducibility_manifest.py")
    monkeypatch.setattr(module, "current_source_sha", lambda: "runtime-sha")
    monkeypatch.setenv("COMPUTE_SOURCE", "local")
    monkeypatch.setenv("COMPUTE_SECONDS", "1")
    monkeypatch.setenv("ACCELERATOR", "cpu")
    monkeypatch.setenv("MARGINAL_COST_USD", "0")
    for key in ("SOURCE_SHA", "GIT_SHA"):
        monkeypatch.delenv(key, raising=False)

    manifest = module.manifest_from_env("snapshot-runtime")

    assert manifest.source_sha == "runtime-sha"


@pytest.mark.parametrize(
    "missing_key", ["COMPUTE_SOURCE", "COMPUTE_SECONDS", "ACCELERATOR", "MARGINAL_COST_USD"]
)
def test_manifest_from_env_rejects_missing_required_values(
    monkeypatch: pytest.MonkeyPatch, missing_key: str
) -> None:
    module = load_alias("ml.reproducibility_manifest", "src/ml/reproducibility_manifest.py")
    values = {
        "SOURCE_SHA": "source-123",
        "COMPUTE_SOURCE": "local",
        "COMPUTE_SECONDS": "2",
        "ACCELERATOR": "cpu",
        "MARGINAL_COST_USD": "0",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv(missing_key, raising=False)

    with pytest.raises(ValueError):
        module.manifest_from_env("snapshot-invalid")


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


def test_dq_checks_alias_contracts() -> None:
    module = load_alias("quality.dq_checks", "src/quality/dq_checks.py")

    assert module.check_not_null([{"ticker": "AAA"}], "companies", "ticker").status == "pass"
    assert module.check_not_null([{"ticker": None}], "companies", "ticker").status == "fail"
    assert (
        module.check_unique(
            [{"ticker": "AAA"}, {"ticker": "AAA"}], "companies", ["ticker"]
        ).metric_value
        == 1.0
    )
    assert (
        module.check_latest_vintage_unique(
            [{"ticker": "AAA", "is_latest_vintage": True}], "companies", ["ticker"]
        ).status
        == "pass"
    )
    assert (
        module.check_null_rate_ceiling(
            [{"key": None}, {"key": "v1"}], "facts", "key", ceiling=0.5
        ).status
        == "pass"
    )
    assert (
        module.check_referential_integrity([{"key": "missing"}], {"known"}, "facts", "key").status
        == "fail"
    )
    assert module.check_retention(10, 9, "facts").status == "pass"
    assert (
        module.check_freshness(
            [{"event_timestamp": "2026-01-01T02:00:00Z"}],
            "prices",
            "2026-01-01T02:30:00Z",
            60,
        ).status
        == "pass"
    )


def test_silver_core_alias_contracts() -> None:
    module = load_alias("transforms.silver.core", "src/transforms/silver/core.py")

    assert module.normalize_columns({" Ticker ": "AAA"}) == {"ticker": "AAA"}
    assert module.align_to_schema({"ticker": "AAA"}, ["ticker"], ["name"]) == {
        "ticker": "AAA",
        "name": None,
    }
    with pytest.raises(ValueError, match="missing required fields"):
        module.align_to_schema({}, ["ticker"], [])

    rows = [
        {"ticker": "AAA", "created_ts": "2026-01-01T00:00:00Z", "value": 1},
        {"ticker": "AAA", "created_ts": "2026-01-02T00:00:00Z", "value": 2},
    ]
    assert module.deduplicate_latest(rows, ["ticker"]) == [rows[1]]
    vintages = [
        {
            "ticker": "AAA",
            "known_from_ts": "2025-01-01T00:00:00Z",
            "created_ts": "2026-01-01T00:00:00Z",
        },
        {
            "ticker": "AAA",
            "known_from_ts": "2026-02-01T00:00:00Z",
            "created_ts": "2026-01-01T00:00:00Z",
        },
    ]
    preserved = module.deduplicate_preserve_vintage(vintages, ["ticker"])
    assert [row["is_latest_vintage"] for row in preserved] == [False, True]
