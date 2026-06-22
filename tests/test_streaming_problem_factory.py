"""Tests for the streaming problem factory (W17.3)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.generators.streaming_problem_factory import (
    inject_streaming_duplicates,
    plan_burst,
    plan_late_arrivals,
)
from src.streaming.events import StreamEvent


def _iso(ts: datetime) -> str:
    return ts.isoformat()


@pytest.fixture
def base_events() -> list[StreamEvent]:
    base_ts = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    return [
        StreamEvent.price_update(
            ticker="AAA",
            event_timestamp=_iso(base_ts),
            created_ts=_iso(base_ts),
            price=10.0,
            volume=100,
        ),
        StreamEvent.price_update(
            ticker="AAA",
            event_timestamp=_iso(base_ts + timedelta(seconds=1)),
            created_ts=_iso(base_ts + timedelta(seconds=1)),
            price=10.1,
            volume=120,
        ),
    ]


def test_plan_burst_returns_exact_record_count(base_events: list[StreamEvent]) -> None:
    burst = plan_burst(base_events, window_seconds=10, record_count=200)
    assert len(burst) == 200
    assert all(isinstance(e, StreamEvent) for e in burst)


def test_plan_burst_events_fall_inside_window(base_events: list[StreamEvent]) -> None:
    burst = plan_burst(base_events, window_seconds=10, record_count=50)
    timestamps = [datetime.fromisoformat(e.event_timestamp) for e in burst]
    start = timestamps[0]
    end = start + timedelta(seconds=10)
    # Allow a 1-second micro-bump for division rounding in the factory.
    assert all(start <= t <= end + timedelta(seconds=1) for t in timestamps)
    assert (timestamps[-1] - timestamps[0]).total_seconds() <= 11


def test_plan_burst_uses_base_ticker(base_events: list[StreamEvent]) -> None:
    burst = plan_burst(base_events, window_seconds=5, record_count=20)
    assert all(e.ticker == "AAA" for e in burst)


def test_plan_late_arrivals_offsets_event_timestamp_into_past(base_events: list[StreamEvent]) -> None:
    late = plan_late_arrivals(base_events, max_lag_seconds=3600)
    assert len(late) == len(base_events)
    for src, out in zip(base_events, late):
        src_ts = datetime.fromisoformat(src.event_timestamp)
        out_ts = datetime.fromisoformat(out.event_timestamp)
        src_created = datetime.fromisoformat(src.created_ts)
        out_created = datetime.fromisoformat(out.created_ts)
        lag = (src_created - out_ts).total_seconds()
        assert 1 <= lag <= 3600
        # created_ts carries forward unchanged
        assert out_created == src_created


def test_inject_streaming_duplicates_preserves_originals(base_events: list[StreamEvent]) -> None:
    out = inject_streaming_duplicates(base_events, rate=0.5)
    original_ids = [e.event_id for e in base_events]
    assert all(e.event_id in original_ids for e in out[: len(base_events)])


def test_inject_streaming_duplicates_adds_expected_count(base_events: list[StreamEvent]) -> None:
    out = inject_streaming_duplicates(base_events, rate=0.5)
    expected_extra = int(0.5 * len(base_events))
    assert len(out) == len(base_events) + expected_extra


def test_inject_streaming_duplicates_event_id_collides(base_events: list[StreamEvent]) -> None:
    out = inject_streaming_duplicates(base_events, rate=0.5)
    extra = out[len(base_events):]
    assert extra, "expected at least one duplicate"
    original_ids = {e.event_id for e in base_events}
    assert all(e.event_id in original_ids for e in extra)


def test_inject_streaming_duplicates_zero_rate(base_events: list[StreamEvent]) -> None:
    out = inject_streaming_duplicates(base_events, rate=0.0)
    assert out == list(base_events)


def test_plan_burst_raises_on_zero_window(base_events: list[StreamEvent]) -> None:
    with pytest.raises(ValueError):
        plan_burst(base_events, window_seconds=0, record_count=10)


def test_plan_burst_raises_on_zero_records(base_events: list[StreamEvent]) -> None:
    with pytest.raises(ValueError):
        plan_burst(base_events, window_seconds=10, record_count=0)
