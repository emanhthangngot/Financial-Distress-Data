from __future__ import annotations

import pytest

from src.transforms.features.pit import _parse_timestamp, pit_join_features
from src.transforms.silver.core import (
    deduplicate_latest,
    deduplicate_preserve_vintage,
)


def test_report_period_and_knowledge_time_are_independent_axes():
    rows = deduplicate_preserve_vintage(
        [
            {
                "ticker": "AAA",
                "report_period": "2023Q2",
                "known_from_ts": "2023-08-01T00:00:00+00:00",
                "created_ts": "2023-08-01T01:00:00+00:00",
                "total_equity": 500e9,
            },
            {
                "ticker": "AAA",
                "report_period": "2023Q2",
                "known_from_ts": "2024-03-01T00:00:00+00:00",
                "created_ts": "2024-03-01T01:00:00+00:00",
                "total_equity": 120e9,
            },
        ],
        ["ticker", "report_period"],
    )

    assert {row["report_period"] for row in rows} == {"2023Q2"}
    assert {row["known_from_ts"] for row in rows} == {
        "2023-08-01T00:00:00+00:00",
        "2024-03-01T00:00:00+00:00",
    }
    assert {row["total_equity"] for row in rows} == {500e9, 120e9}


def test_unparseable_timestamps_fail_closed():
    with pytest.raises(ValueError, match="created_ts"):
        deduplicate_latest(
            [{"ticker": "AAA", "created_ts": "not-a-timestamp"}],
            ["ticker"],
        )
    with pytest.raises(ValueError, match="timestamp"):
        _parse_timestamp("not-a-timestamp")


def test_pit_join_honors_explicit_knowledge_time_cutoff():
    joined = pit_join_features(
        [{"ticker": "AAA", "known_from_ts": "2024-04-01T00:00:00+00:00"}],
        [
            {
                "ticker": "AAA",
                "known_from_ts": "2024-02-01T00:00:00+00:00",
                "value": "eligible",
            },
            {
                "ticker": "AAA",
                "known_from_ts": "2024-03-01T00:00:00+00:00",
                "value": "after-cutoff",
            },
        ],
        knowledge_time_cutoff="2024-02-15T00:00:00+00:00",
    )

    assert joined[0]["feature_value"] == "eligible"
