"""Pins the pure aggregation logic shared by
src/ml/feast/offline_job.py and online_job.py — no Kafka, no Feast, runs in
the fast loop."""

from __future__ import annotations

from src.ml.feast.offline_job import aggregate_stream_events


def _payload(ticker: str, price: float, event_timestamp: str) -> dict:
    return {"ticker": ticker, "price": price, "event_timestamp": event_timestamp}


def test_aggregate_groups_by_ticker() -> None:
    events = [
        _payload("AAA", 10.0, "2026-08-08T09:00:00+00:00"),
        _payload("BBB", 20.0, "2026-08-08T09:00:00+00:00"),
    ]
    rows = aggregate_stream_events(events)
    assert {row["ticker"] for row in rows} == {"AAA", "BBB"}


def test_last_price_is_the_latest_by_event_timestamp() -> None:
    events = [
        _payload("AAA", 10.0, "2026-08-08T09:00:00+00:00"),
        _payload("AAA", 12.0, "2026-08-08T09:30:00+00:00"),
        _payload("AAA", 11.0, "2026-08-08T09:15:00+00:00"),  # out of order on purpose
    ]
    rows = aggregate_stream_events(events)
    assert rows[0]["last_price"] == 12.0


def test_event_count_1h_is_the_batch_count() -> None:
    events = [_payload("AAA", 10.0 + i, f"2026-08-08T09:{i:02d}:00+00:00") for i in range(5)]
    rows = aggregate_stream_events(events)
    assert rows[0]["event_count_1h"] == 5


def test_price_change_pct_is_relative_first_to_last() -> None:
    events = [
        _payload("AAA", 100.0, "2026-08-08T09:00:00+00:00"),
        _payload("AAA", 110.0, "2026-08-08T09:30:00+00:00"),
    ]
    rows = aggregate_stream_events(events)
    assert rows[0]["price_change_pct_1h"] == 0.1


def test_price_change_pct_is_none_when_first_price_is_zero() -> None:
    events = [
        _payload("AAA", 0.0, "2026-08-08T09:00:00+00:00"),
        _payload("AAA", 10.0, "2026-08-08T09:30:00+00:00"),
    ]
    rows = aggregate_stream_events(events)
    assert rows[0]["price_change_pct_1h"] is None


def test_accepts_kafka_message_shaped_events_with_nested_payload() -> None:
    events = [{"topic": "financial.price_events", "payload": _payload("AAA", 5.0, "t1")}]
    rows = aggregate_stream_events(events)
    assert rows[0]["ticker"] == "AAA"


def test_empty_batch_yields_no_rows() -> None:
    assert aggregate_stream_events([]) == []
