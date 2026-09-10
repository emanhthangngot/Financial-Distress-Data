"""ADR-017 §Feast temporal contract / F14: every file-backed FeatureView's
``event_timestamp`` join axis is bound to the Gold ``known_from_ts`` column,
never a raw ``event_timestamp`` field — Feast's default tie-break on the
highest ``created_timestamp`` for a given axis value would otherwise select
the newest vintage, exactly the leakage this data model exists to prevent.
Imports real Feast, so this file runs under ``.venv-platform`` only (D4)."""

from __future__ import annotations

from src.ml.feast.feature_definitions import GOLD_DATASETS, build_feature_objects


def test_every_file_backed_feature_view_binds_known_from_ts_as_event_timestamp() -> None:
    objects = build_feature_objects()
    for view_name in GOLD_DATASETS:
        source = objects[view_name].batch_source
        assert source.timestamp_field == "known_from_ts", (
            f"{view_name} must join on known_from_ts, not a raw event_timestamp field "
            "(ADR-017 F14) — Feast's default tie-break otherwise leaks the newest vintage"
        )


def test_stream_view_batch_fallback_also_binds_known_from_ts() -> None:
    objects = build_feature_objects()
    fallback_source = objects["stream_market_features"].batch_source
    assert fallback_source.timestamp_field == "known_from_ts"
