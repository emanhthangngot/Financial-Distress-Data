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


# --- _deterministic_batch_id (offline-job write-key idempotency) -------------


def test_batch_id_is_stable_for_an_exact_replay() -> None:
    from src.ml.feast.offline_job import _deterministic_batch_id

    events = [_payload("AAA", 10.0, "2026-08-08T09:00:00+00:00")]
    rows = aggregate_stream_events(events)
    replayed_rows = aggregate_stream_events(events)  # same Kafka messages redelivered
    assert _deterministic_batch_id(rows) == _deterministic_batch_id(replayed_rows)


def test_batch_id_differs_when_event_count_differs_but_last_price_matches() -> None:
    """Regression: hashing only ticker/timestamp/last_price let a
    3-event batch and a 1-event batch that happen to share the same last
    price collide on the same object key and silently overwrite each
    other — event_count_1h/price_change_pct_1h must be part of the hash."""
    from src.ml.feast.offline_job import _deterministic_batch_id

    three_events = [
        _payload("AAA", 10.0, "2026-08-08T09:00:00+00:00"),
        _payload("AAA", 11.0, "2026-08-08T09:15:00+00:00"),
        _payload("AAA", 12.0, "2026-08-08T09:30:00+00:00"),
    ]
    one_event = [_payload("AAA", 12.0, "2026-08-08T09:30:00+00:00")]
    rows_a = aggregate_stream_events(three_events)
    rows_b = aggregate_stream_events(one_event)
    assert rows_a[0]["last_price"] == rows_b[0]["last_price"] == 12.0  # same tail price
    assert rows_a[0]["event_timestamp"] == rows_b[0]["event_timestamp"]  # same timestamp
    assert _deterministic_batch_id(rows_a) != _deterministic_batch_id(rows_b)


def test_batch_id_differs_for_a_different_ticker_set() -> None:
    from src.ml.feast.offline_job import _deterministic_batch_id

    rows_a = aggregate_stream_events([_payload("AAA", 10.0, "2026-08-08T09:00:00+00:00")])
    rows_b = aggregate_stream_events([_payload("BBB", 10.0, "2026-08-08T09:00:00+00:00")])
    assert _deterministic_batch_id(rows_a) != _deterministic_batch_id(rows_b)
