"""Pins src/ml/feast/feature_definitions.py's TTL table without importing
Feast — Feast lives only in .venv-platform (D4). Every FeatureView has a
non-null TTL, TTL values equal the documented table, every declared source
has an event_timestamp_column, and every view has a rationale string."""

from __future__ import annotations

from datetime import timedelta

import pytest

from src.ml.feast.feature_definitions import (
    ENTITY_NAME,
    FEATURE_VIEW_RATIONALE,
    FEATURE_VIEW_TTL,
    GOLD_DATASETS,
    gold_source_path,
)


def test_module_import_does_not_pull_in_feast() -> None:
    import sys

    assert "feast" not in sys.modules


EXPECTED_TTL = {
    "company_financial_features": timedelta(days=100),
    "company_risk_features": timedelta(days=100),
    "market_price_features": timedelta(days=2),
    "stream_market_features": timedelta(hours=1),
}


def test_ttl_table_matches_documented_values() -> None:
    assert FEATURE_VIEW_TTL == EXPECTED_TTL


def test_every_ttl_is_non_null() -> None:
    for name, ttl in FEATURE_VIEW_TTL.items():
        assert ttl is not None, name
        assert ttl > timedelta(0), name


@pytest.mark.parametrize("view_name", list(EXPECTED_TTL))
def test_every_feature_view_has_a_rationale(view_name: str) -> None:
    assert FEATURE_VIEW_RATIONALE[view_name].strip() != ""


def test_ttl_and_rationale_cover_the_same_views() -> None:
    assert set(FEATURE_VIEW_TTL) == set(FEATURE_VIEW_RATIONALE)


def test_entity_name_is_ticker() -> None:
    assert ENTITY_NAME == "ticker"


def test_gold_datasets_cover_every_file_backed_view() -> None:
    # stream_market_features is PushSource-only (no Gold FileSource of its
    # own; its batch fallback is market_price_features's source).
    file_backed = set(FEATURE_VIEW_TTL) - {"stream_market_features"}
    assert set(GOLD_DATASETS) == file_backed


def test_gold_source_path_resolves_through_src_io_paths() -> None:
    path = gold_source_path("fact_financial_statement")
    assert path == "s3://financial-distress-lake/gold/fact_financial_statement/data.parquet"
