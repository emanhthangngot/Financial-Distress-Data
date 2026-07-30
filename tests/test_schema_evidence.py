from pathlib import Path

import pytest


def test_schema_evidence_has_all_zones_relationships_scd2_and_timestamps(tmp_path):
    pytest.importorskip("duckdb")
    from scripts.build_schema_evidence import build_schema_evidence

    report = build_schema_evidence(Path("sql/schema_evidence.sql"), tmp_path / "warehouse.db")

    assert report["status"] == "pass"
    assert report["zones"] == ["bronze", "gold", "silver"]
    assert report["table_count"] >= 15
    assert report["foreign_key_count"] >= 4
    assert report["feature_timestamp_contract"]["missing_tables"] == []
    assert report["scd2_history"] == [{"ticker": "AAA", "versions": 2, "current_versions": 1}]
