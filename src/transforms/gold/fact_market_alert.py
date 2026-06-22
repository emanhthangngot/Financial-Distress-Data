"""
Gold-zone fact builder for market alerts.

Builds the alert fact from the streaming topic, deriving simple thresholds (e.g. daily drop > 7%)
and joining with company dimension. Powers the news/alert dashboard.
"""

from __future__ import annotations

from typing import Any

from src.transforms.keys import date_key, stable_company_key


def build_fact_market_alert(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts = []
    seen: set[str] = set()
    for row in sorted(
        rows,
        key=lambda item: (item.get("event_id", ""), item.get("created_ts", "")),
    ):
        event_id = str(row["event_id"])
        if event_id in seen:
            continue
        seen.add(event_id)
        ticker = str(row["ticker"]).upper()
        fact = dict(row)
        fact["ticker"] = ticker
        fact["company_key"] = stable_company_key(ticker)
        fact["date_key"] = date_key(row["event_timestamp"])
        fact["alert_type"] = str(row.get("alert_type", "unknown"))
        facts.append(fact)
    return facts
