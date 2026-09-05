from __future__ import annotations

import pytest

from src.ml.leakage_guard import LeakageError, assert_no_leakage
from src.transforms.silver.core import deduplicate_preserve_vintage


def test_restatements_survive_and_leakage_guard_enforces_decision_boundary():
    vintages = deduplicate_preserve_vintage(
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

    assert len(vintages) == 2
    assert sum(row["is_latest_vintage"] for row in vintages) == 1
    assert next(row for row in vintages if row["is_latest_vintage"])["total_equity"] == 120e9

    decision_ts = "2023-12-31T00:00:00+00:00"
    restated = next(row for row in vintages if row["total_equity"] == 120e9)
    original = next(row for row in vintages if row["total_equity"] == 500e9)

    with pytest.raises(LeakageError):
        assert_no_leakage([{**restated, "decision_ts": decision_ts}])

    assert_no_leakage([{**original, "decision_ts": decision_ts}])
