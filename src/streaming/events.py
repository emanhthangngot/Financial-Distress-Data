from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


def _stable_event_id(event_type: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        {"event_type": event_type, **payload}, sort_keys=True, separators=(",", ":")
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


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
        event_hash = _stable_event_id("price_update", payload)
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
        payload = {
            "ticker": ticker,
            "event_timestamp": event_timestamp,
            "created_ts": created_ts,
            "alert_type": alert_type,
        }
        return cls(
            topic="financial.alert_events",
            event_id=_stable_event_id("market_alert", payload),
            event_type="market_alert",
            ticker=ticker,
            event_timestamp=event_timestamp,
            created_ts=created_ts,
            payload=payload,
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
        event_hash = _stable_event_id("news_sentiment", payload)
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
