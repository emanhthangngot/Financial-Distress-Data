"""Streaming problem factory helpers (W17.3).

Pure functions that build synthetic streaming events so the rubric lines
"burst", "late arrivals", and "streaming duplicates" can be exercised
without touching the Kafka producer. The helpers consume and emit
``StreamEvent`` dataclasses from ``src.streaming.events`` so the wire
contract is unchanged.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Iterable

from src.streaming.events import StreamEvent


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _format(ts: datetime) -> str:
    return ts.isoformat()


def _latest_created_ts(events: Iterable[StreamEvent]) -> datetime:
    parsed = [_parse(e.created_ts) for e in events]
    if not parsed:
        return datetime.now(timezone.utc)
    return max(parsed)


def plan_burst(
    base_events: list[StreamEvent],
    *,
    window_seconds: int,
    record_count: int,
    start_at: datetime | None = None,
) -> list[StreamEvent]:
    """Emit ``record_count`` price-update events that span ``window_seconds``.

    The burst is deterministic when ``start_at`` is provided. Otherwise it
    starts at the latest ``created_ts`` in ``base_events``. Every event uses
    the ticker of the first base event (or ``"AAA"`` if the list is empty)
    and a price that increments by ``0.01`` per record.
    """
    if window_seconds <= 0:
        raise ValueError("window_seconds must be > 0")
    if record_count <= 0:
        raise ValueError("record_count must be > 0")

    ticker = base_events[0].ticker if base_events else "AAA"
    start = start_at or _latest_created_ts(base_events)
    step = timedelta(seconds=window_seconds) / max(record_count - 1, 1)
    events: list[StreamEvent] = []
    for i in range(record_count):
        ts = start + step * i
        events.append(
            StreamEvent.price_update(
                ticker=ticker,
                event_timestamp=_format(ts),
                created_ts=_format(ts),
                price=10.0 + 0.01 * i,
                volume=100 + i,
            )
        )
    return events


def plan_late_arrivals(
    base_events: list[StreamEvent],
    *,
    max_lag_seconds: int,
    seed: int = 0,
) -> list[StreamEvent]:
    """Return clones of ``base_events`` whose ``event_timestamp`` is lagged.

    The lag is uniformly sampled in ``[1, max_lag_seconds]`` and the
    ``created_ts`` carries forward unchanged so the gap between the two
    timestamps represents the late-arrival delay. ``seed`` makes the
    factory deterministic when needed (default 0 keeps the test output
    stable).
    """
    if max_lag_seconds <= 0:
        raise ValueError("max_lag_seconds must be > 0")
    rng = random.Random(seed)
    out: list[StreamEvent] = []
    for src in base_events:
        lag = rng.randint(1, max_lag_seconds)
        ts = _parse(src.event_timestamp) - timedelta(seconds=lag)
        out.append(
            StreamEvent.price_update(
                ticker=src.ticker,
                event_timestamp=_format(ts),
                created_ts=src.created_ts,
                price=float(src.payload.get("price", 10.0)),
                volume=int(src.payload.get("volume", 100)),
            )
        )
    return out


def inject_streaming_duplicates(
    events: list[StreamEvent],
    *,
    rate: float,
    seed: int = 0,
) -> list[StreamEvent]:
    """Append ``floor(rate * N)`` duplicate events whose ``event_id`` collides.

    The duplicate events copy the canonical record but shift ``created_ts``
    one second into the future so they are distinguishable in the consumer.
    """
    if rate < 0:
        raise ValueError("rate must be >= 0")
    extra = int(rate * len(events))
    if extra == 0 or not events:
        return list(events)
    rng = random.Random(seed)
    out = list(events)
    for _ in range(extra):
        src = events[rng.randrange(len(events))]
        bumped = _parse(src.created_ts) + timedelta(seconds=1)
        clone = StreamEvent.price_update(
            ticker=src.ticker,
            event_timestamp=src.event_timestamp,
            created_ts=_format(bumped),
            price=float(src.payload.get("price", 10.0)),
            volume=int(src.payload.get("volume", 100)),
        )
        # Re-stamp event_id so it collides with the canonical event.
        object.__setattr__(clone, "event_id", src.event_id)
        out.append(clone)
    return out


__all__ = [
    "inject_streaming_duplicates",
    "plan_burst",
    "plan_late_arrivals",
]
