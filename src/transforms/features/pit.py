from __future__ import annotations

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


def pit_join_features(
    references: list[dict[str, Any]], features: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    by_ticker: dict[str, list[dict[str, Any]]] = {}
    for feature in features:
        by_ticker.setdefault(str(feature["ticker"]).upper(), []).append(feature)
    for ticker_features in by_ticker.values():
        ticker_features.sort(key=lambda item: item["event_timestamp"], reverse=True)
    for reference in references:
        ticker = str(reference["ticker"]).upper()
        ref_ts = reference["event_timestamp"]
        candidate = next(
            (
                feature
                for feature in by_ticker.get(ticker, [])
                if str(feature["event_timestamp"]) <= str(ref_ts)
            ),
            {},
        )
        output.append(
            {**reference, **{f"feature_{key}": value for key, value in candidate.items()}}
        )
    return output
