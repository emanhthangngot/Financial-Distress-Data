"""Runtime proof for the structured Feast knowledge-time contract.

Every file-backed view joins on ``known_from_ts`` and keeps ingest time only
as its retry tie-break. The materialization check exercises the v2 aggregate
FeatureView against a partitioned local Parquet prefix with two vintages.
"""

from __future__ import annotations

from scripts.run_cluster_pipeline import verify_materialized_vintage
from src.ml.feast import feature_definitions
from src.ml.feast.feature_definitions import GOLD_DATASETS, build_feature_objects


def test_every_file_backed_feature_view_binds_known_from_ts_as_event_timestamp() -> None:
    objects = build_feature_objects()
    for view_name in GOLD_DATASETS:
        source = objects[view_name].batch_source
        assert (
            source.timestamp_field == "known_from_ts"
        ), f"{view_name} must join on known_from_ts, not a raw event_timestamp field"
        assert (
            source.created_timestamp_column == "created_timestamp"
        ), f"{view_name} must use ingest time only to break retries of one vintage"
        if view_name != "company_financial_4q_features":
            assert source.field_mapping == {"created_ts": "created_timestamp"}
        assert not source.path.endswith(
            "data.parquet"
        ), f"{view_name} must read its partitioned Gold prefix"


def test_stream_view_batch_fallback_also_binds_known_from_ts() -> None:
    objects = build_feature_objects()
    fallback_source = objects["stream_market_features"].batch_source
    assert fallback_source.timestamp_field == "known_from_ts"


def test_partitioned_aggregate_materialization_selects_eligible_vintage_and_excludes_newer(
    tmp_path, monkeypatch
) -> None:
    from datetime import UTC, datetime
    from pathlib import Path

    import pandas as pd
    from feast import FeatureStore

    source_root = tmp_path / "gold" / "feat_company_financial_4q"
    january = source_root / "known_from_month=2026-01"
    february = source_root / "known_from_month=2026-02"
    january.mkdir(parents=True)
    february.mkdir(parents=True)

    original = {
        "ticker": "AAA",
        "known_from_ts": datetime(2026, 1, 1, tzinfo=UTC),
        "created_timestamp": datetime(2026, 1, 1, 1, tzinfo=UTC),
        "report_period": "2025-Q4",
        "feature_family": "financial_4q",
        "window_period_count": 4,
        "feature_completeness": 1.0,
        "current_ratio": 0.6,
        "debt_to_asset": 0.8,
        "debt_to_equity": 4.0,
        "roa": -0.1,
        "roe": -0.4,
        "ebit_interest_coverage": 0.5,
        "z_score": 1.0,
    }
    retry = {
        **original,
        "created_timestamp": datetime(2026, 1, 2, tzinfo=UTC),
        "current_ratio": 0.7,
        "z_score": 2.0,
    }
    newer_vintage = {
        **retry,
        "known_from_ts": datetime(2026, 2, 1, tzinfo=UTC),
        "created_timestamp": datetime(2026, 2, 1, 1, tzinfo=UTC),
        "current_ratio": 9.9,
        "z_score": 99.0,
    }
    pd.DataFrame([original, retry]).to_parquet(january / "part-000.parquet", index=False)
    pd.DataFrame([newer_vintage]).to_parquet(february / "part-000.parquet", index=False)

    unused_root = tmp_path / "unused"
    monkeypatch.setattr(
        feature_definitions,
        "gold_source_path",
        lambda dataset_name: (
            str(source_root)
            if dataset_name == "feat_company_financial_4q"
            else str(unused_root / dataset_name)
        ),
    )
    repo_path = tmp_path / "feature_repo"
    repo_path.mkdir()
    Path(repo_path, "feature_store.yaml").write_text(
        "\n".join(
            (
                "project: vintage_materialization",
                "provider: local",
                f"registry: {repo_path / 'registry.db'}",
                "online_store:",
                "  type: sqlite",
                f"  path: {repo_path / 'online.db'}",
                "offline_store:",
                "  type: file",
                "entity_key_serialization_version: 3",
            )
        ),
        encoding="utf-8",
    )

    store = FeatureStore(repo_path=str(repo_path))
    store.apply(list(build_feature_objects().values()))
    cutoff = datetime(2026, 1, 15, tzinfo=UTC)

    store.materialize(
        start_date=datetime(2025, 12, 31, tzinfo=UTC),
        end_date=cutoff,
        feature_views=["company_financial_4q_features"],
    )
    online, identity = verify_materialized_vintage(
        store,
        "AAA",
        cutoff.isoformat(),
        "company_financial_4q_features",
        (
            "report_period",
            "window_period_count",
            "feature_completeness",
            "current_ratio",
            "z_score",
        ),
    )

    assert online["report_period"] == ["2025-Q4"]
    assert online["window_period_count"] == [4]
    assert online["feature_completeness"] == [1.0]
    assert online["current_ratio"] == [0.7]
    assert online["z_score"] == [2.0]
    assert identity == {
        "ticker": "AAA",
        "cutoff_ts": cutoff.isoformat(),
        "known_from_ts": original["known_from_ts"].isoformat(),
    }
    assert online["z_score"] != [newer_vintage["z_score"]]
