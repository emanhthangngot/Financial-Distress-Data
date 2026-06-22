"""Tests for the generator characteristics evidence writer (W17.4)."""
from __future__ import annotations

import json
from pathlib import Path

from src.jobs.stage1_evidence_job import (
    build_generator_characteristics,
    write_generator_characteristics_evidence,
)


def test_build_generator_characteristics_returns_expected_sections() -> None:
    payload = build_generator_characteristics()

    assert "skew" in payload
    assert "cardinality" in payload
    assert "evolution" in payload
    assert "duplication" in payload
    assert "streaming" in payload
    assert "volume" in payload

    # Skew: top_share is between 0 and 1
    assert 0.0 <= payload["skew"]["top_share"] <= 1.0
    assert isinstance(payload["skew"]["ticker_counts"], dict)

    # Cardinality: counts are non-negative
    assert payload["cardinality"]["distinct_tickers"] >= 0
    assert payload["cardinality"]["distinct_industries"] >= 0
    assert payload["cardinality"]["distinct_sectors"] >= 0

    # Evolution: legacy_null_count is a non-negative int
    assert payload["evolution"]["legacy_null_count"] >= 0

    # Duplication: offline_count equals floor(offline_rate * base_count)
    base = payload["duplication"]["offline_base_count"]
    rate = payload["duplication"]["offline_rate"]
    assert payload["duplication"]["offline_count"] == int(rate * base)
    assert payload["duplication"]["after_dedup"] <= base

    # Streaming: counts are non-negative ints
    assert payload["streaming"]["burst_count"] >= 0
    assert payload["streaming"]["late_count"] >= 0
    assert payload["streaming"]["duplicate_count"] >= 0

    # Volume: parquet format
    assert payload["volume"]["format"] == "parquet"
    for v in payload["volume"]["row_counts"].values():
        assert v >= 0


def test_write_generator_characteristics_evidence_writes_json(tmp_path: Path) -> None:
    out_path = write_generator_characteristics_evidence(tmp_path)
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "skew" in data and "streaming" in data and "volume" in data
