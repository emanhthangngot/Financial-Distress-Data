from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def build_feat_company_financial_4q(financial_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in financial_rows:
        rows.append(
            {
                "ticker": str(row["ticker"]).upper(),
                "report_period": row.get("report_period"),
                "event_timestamp": row.get("report_release_date")
                or row.get("event_timestamp")
                or row.get("created_ts"),
                "created_ts": row.get("created_ts"),
                "current_ratio": row.get("current_ratio"),
                "debt_to_asset": row.get("debt_to_asset"),
                "debt_to_equity": row.get("debt_to_equity"),
                "roa": row.get("roa"),
                "roe": row.get("roe"),
                "ebit_interest_coverage": row.get("ebit_interest_coverage"),
                "z_score": row.get("z_score"),
                "feature_family": "financial_4q",
            }
        )
    return rows


def build_feat_company_market_30d(market_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in market_rows:
        rows.append(
            {
                "ticker": str(row["ticker"]).upper(),
                "event_timestamp": row.get("event_timestamp") or row.get("trading_date"),
                "created_ts": row.get("created_ts"),
                "trading_date": row.get("trading_date"),
                "close_price": row.get("close_price"),
                "volume": row.get("volume"),
                "daily_return": row.get("daily_return"),
                "volatility_signal": row.get("volatility_signal"),
                "feature_family": "market_30d",
            }
        )
    return rows


def build_feat_company_news_30d(news_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in news_rows:
        rows.append(
            {
                "ticker": str(row["ticker"]).upper(),
                "event_timestamp": row.get("event_timestamp"),
                "created_ts": row.get("created_ts"),
                "sentiment_score": row.get("sentiment_score"),
                "risk_keyword_flag": row.get("risk_keyword_flag"),
                "severity_score": row.get("severity_score"),
                "feature_family": "news_30d",
            }
        )
    return rows


def build_feat_company_unified(
    company_quarter_rows: list[dict[str, Any]],
    market_facts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    references = []
    for row in company_quarter_rows:
        reference_timestamp = (
            row.get("report_release_date") or row.get("event_timestamp") or row.get("created_ts")
        )
        references.append({**row, "event_timestamp": reference_timestamp})

    feature_rows = []
    for row in market_facts:
        feature_timestamp = row.get("event_timestamp") or row.get("trading_date")
        feature_rows.append({**row, "event_timestamp": feature_timestamp})

    return pit_join_features(references, feature_rows)


def _parse_timestamp(val: Any) -> datetime:
    if not val:
        return datetime.min.replace(tzinfo=UTC)
    s = str(val).strip()
    if len(s) == 10:
        s += "T00:00:00+00:00"
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    if " " in s and "T" not in s:
        s = s.replace(" ", "T")
    if "+" not in s and "-" not in s.split("T")[-1]:
        s += "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        try:
            return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            return datetime.min.replace(tzinfo=UTC)


def pit_join_features(
    references: list[dict[str, Any]], features: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    by_ticker: dict[str, list[dict[str, Any]]] = {}
    for feature in features:
        by_ticker.setdefault(str(feature["ticker"]).upper(), []).append(feature)
    for ticker_features in by_ticker.values():
        ticker_features.sort(
            key=lambda item: _parse_timestamp(item["event_timestamp"]), reverse=True
        )
    for reference in references:
        ticker = str(reference["ticker"]).upper()
        ref_ts = _parse_timestamp(reference["event_timestamp"])
        candidate = next(
            (
                feature
                for feature in by_ticker.get(ticker, [])
                if _parse_timestamp(feature["event_timestamp"]) <= ref_ts
            ),
            {},
        )
        output.append(
            {**reference, **{f"feature_{key}": value for key, value in candidate.items()}}
        )
    return output
