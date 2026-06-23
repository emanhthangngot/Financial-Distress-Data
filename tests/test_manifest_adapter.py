"""W24 Idea 2 - Airbyte-style declarative ingestion manifest (RED seeds).

The W24 plan calls for a YAML manifest of ingestion sources (TCBS, CafeF)
that can be dispatched by a single adapter without rewriting per-source
collector code. The adapter is read-only and offline-safe: all sources
ship with ``enabled: false`` by default and ``fetch()`` returns a
synthetic record sourced from a per-source fixture handler.

These tests assert the manifest shape, the dispatch behaviour, and the
smoke-runner evidence. They start RED in W24 commit 3 and turn GREEN
once the adapter and CLI are implemented in commit 4.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_YAML = REPO_ROOT / "configs" / "ingestion_manifest.yaml"
ADAPTER_MODULE = "src.collectors.manifest_adapter"
SMOKE_MODULE = "src.collectors.run_manifest_smoke"
EVIDENCE_JSON = REPO_ROOT / "docs" / "evidence" / "airbyte_manifest_run.json"

REQUIRED_SOURCE_FIELDS = {
    "source_id",
    "enabled",
    "endpoint",
    "field_map",
    "rate_limit_per_min",
    "incremental_key",
}


def test_manifest_yaml_exists() -> None:
    assert MANIFEST_YAML.exists(), f"missing manifest at {MANIFEST_YAML}"


def test_manifest_loads_with_two_sources() -> None:
    mod = importlib.import_module(ADAPTER_MODULE)
    adapter = mod.ManifestAdapter(MANIFEST_YAML)
    sources = adapter.sources()
    assert len(sources) >= 2, (
        "manifest must list at least TCBS and CafeF"
    )
    ids = {s["source_id"] for s in sources}
    assert {"tcbs", "cafef"}.issubset(ids)


def test_manifest_sources_have_required_fields() -> None:
    mod = importlib.import_module(ADAPTER_MODULE)
    adapter = mod.ManifestAdapter(MANIFEST_YAML)
    for src in adapter.sources():
        missing = REQUIRED_SOURCE_FIELDS - set(src.keys())
        assert not missing, f"source {src.get('source_id')} missing: {missing}"


def test_manifest_adapter_fetch_uses_field_map() -> None:
    mod = importlib.import_module(ADAPTER_MODULE)
    adapter = mod.ManifestAdapter(MANIFEST_YAML)
    record = adapter.fetch("VCB", "tcbs")
    assert isinstance(record, dict)
    field_map = next(
        s["field_map"] for s in adapter.sources() if s["source_id"] == "tcbs"
    )
    # Every field in the manifest's field_map must appear as a key in
    # the record returned by fetch().
    for manifest_field in field_map:
        assert manifest_field in record, (
            f"fetch() result missing manifest field {manifest_field}"
        )


def test_manifest_adapter_disabled_source_returns_none() -> None:
    mod = importlib.import_module(ADAPTER_MODULE)
    adapter = mod.ManifestAdapter(MANIFEST_YAML)
    # All sources are disabled by default in the shipped manifest. The
    # adapter must not call the handler and must return None so the
    # caller can skip the source cleanly.
    result = adapter.fetch("VCB", "tcbs")
    assert result is None


def test_manifest_adapter_enabled_source_returns_dict(
    tmp_path: Path,
) -> None:
    mod = importlib.import_module(ADAPTER_MODULE)
    # Build an inline manifest with a single enabled source pointing at
    # the bundled fixture handler.
    manifest = tmp_path / "m.yaml"
    manifest.write_text(
        "sources:\n"
        "  - source_id: tcbs\n"
        "    enabled: true\n"
        "    endpoint: fixture\n"
        "    field_map:\n"
        "      symbol: symbol\n"
        "      price: close_price\n"
        "    rate_limit_per_min: 60\n"
        "    incremental_key: ts\n",
        encoding="utf-8",
    )
    adapter = mod.ManifestAdapter(manifest)
    record = adapter.fetch("VCB", "tcbs")
    assert record is not None
    assert record["symbol"] == "VCB"
    assert "price" in record


def test_run_manifest_smoke_writes_evidence_json() -> None:
    # Use the shipped manifest (all sources disabled) - smoke still
    # writes a JSON with the required keys, even if records is empty.
    result = subprocess.run(
        [sys.executable, "-m", "src.collectors.run_manifest_smoke"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert EVIDENCE_JSON.exists(), (
        f"smoke runner must write evidence to {EVIDENCE_JSON}"
    )
    payload = json.loads(EVIDENCE_JSON.read_text(encoding="utf-8"))
    assert "sources" in payload
    assert "records" in payload
    assert "per_source_counts" in payload
