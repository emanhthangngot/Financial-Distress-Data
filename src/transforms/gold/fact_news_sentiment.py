from __future__ import annotations

from typing import Any

from src.transforms.keys import date_key, stable_company_key


def build_fact_news_sentiment(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts = []
    latest: dict[str, dict[str, Any]] = {}
    for row in sorted(
        rows,
        key=lambda item: (item.get("event_id", ""), item.get("created_ts", "")),
        reverse=True,
    ):
        event_id = str(row["event_id"])
        if event_id in latest:
            continue
        latest[event_id] = row
        ticker = str(row["ticker"]).upper()
        fact = dict(row)
        fact["ticker"] = ticker
        fact["company_key"] = stable_company_key(ticker)
        fact["date_key"] = date_key(row["event_timestamp"])
        fact["sentiment_score"] = (
            None if row.get("sentiment_score") is None else float(row["sentiment_score"])
        )
        fact["risk_keyword_flag"] = bool(row.get("risk_keyword_flag", False))
        fact["severity_score"] = (
            None if row.get("severity_score") is None else float(row["severity_score"])
        )
        facts.append(fact)
    return facts
