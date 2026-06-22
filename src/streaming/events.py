"""
Event schemas and serializers for the streaming pipeline.

Defines the canonical Pydantic / dataclass models for market ticks, news sentiment, and alert events
flowing through Kafka. Producers and consumers must import from this module to keep schema evolution
disciplined.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class StreamEvent:
    topic: str
    event_id: str
    event_type: str
    ticker: str
    event_timestamp: str
    created_ts: str
    payload: dict[str, Any]

    @classmethod
    def price_update(
        cls, ticker: str, event_timestamp: str, created_ts: str, price: float, volume: int
    ) -> StreamEvent:
        payload = {
            "ticker": ticker,
            "event_timestamp": event_timestamp,
            "created_ts": created_ts,
            "price": price,
            "volume": volume,
        }
        event_hash = sha256(repr(sorted(payload.items())).encode("utf-8")).hexdigest()
        return cls(
            topic="financial.price_events",
            event_id=event_hash,
            event_type="price_update",
            ticker=ticker,
            event_timestamp=event_timestamp,
            created_ts=created_ts,
            payload=payload,
        )

    @classmethod
    def alert(
        cls, ticker: str, event_timestamp: str, created_ts: str, alert_type: str
    ) -> StreamEvent:
        return cls(
            topic="financial.alert_events",
            event_id=str(uuid4()),
            event_type="market_alert",
            ticker=ticker,
            event_timestamp=event_timestamp,
            created_ts=created_ts,
            payload={"ticker": ticker, "alert_type": alert_type},
        )

    @classmethod
    def news_sentiment(
        cls,
        ticker: str,
        event_timestamp: str,
        created_ts: str,
        sentiment_score: float,
        risk_keyword_flag: bool,
        severity_score: float,
        source_url: str | None = None,
    ) -> StreamEvent:
        payload = {
            "ticker": ticker,
            "event_timestamp": event_timestamp,
            "created_ts": created_ts,
            "sentiment_score": sentiment_score,
            "risk_keyword_flag": risk_keyword_flag,
            "severity_score": severity_score,
            "source_url": source_url,
        }
        event_hash = sha256(repr(sorted(payload.items())).encode("utf-8")).hexdigest()
        return cls(
            topic="financial.news_events",
            event_id=event_hash,
            event_type="news_sentiment",
            ticker=ticker,
            event_timestamp=event_timestamp,
            created_ts=created_ts,
            payload=payload,
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "ticker": self.ticker,
            "event_timestamp": self.event_timestamp,
            "created_ts": self.created_ts,
            **self.payload,
        }
