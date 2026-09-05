from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _knowledge_timestamp(row: dict[str, Any], *fallback_fields: str) -> Any:
    value = row.get("known_from_ts")
    if value in (None, ""):
        value = next(
            (row.get(field) for field in fallback_fields if row.get(field) not in (None, "")),
            None,
        )
    _parse_timestamp(value)
    return value


def build_feat_company_financial_4q(financial_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in financial_rows:
        known_from_ts = _knowledge_timestamp(
            row, "report_release_date", "event_timestamp", "created_ts"
        )
        rows.append(
            {
                "ticker": str(row["ticker"]).upper(),
                "report_period": row.get("report_period"),
                "event_timestamp": known_from_ts,
                "known_from_ts": known_from_ts,
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
        known_from_ts = _knowledge_timestamp(row, "event_timestamp", "created_ts", "trading_date")
        rows.append(
            {
                "ticker": str(row["ticker"]).upper(),
                "event_timestamp": known_from_ts,
                "known_from_ts": known_from_ts,
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
        known_from_ts = _knowledge_timestamp(row, "event_timestamp", "created_ts")
        rows.append(
            {
                "ticker": str(row["ticker"]).upper(),
                "event_timestamp": known_from_ts,
                "known_from_ts": known_from_ts,
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
    *,
    knowledge_time_cutoff: Any | None = None,
) -> list[dict[str, Any]]:
    references = []
    for row in company_quarter_rows:
        reference_timestamp = _knowledge_timestamp(
            row, "report_release_date", "event_timestamp", "created_ts"
        )
        references.append(
            {
                **row,
                "known_from_ts": reference_timestamp,
                "event_timestamp": reference_timestamp,
            }
        )

    feature_rows = []
    for row in market_facts:
        feature_timestamp = _knowledge_timestamp(
            row, "event_timestamp", "created_ts", "trading_date"
        )
        feature_rows.append(
            {
                **row,
                "known_from_ts": feature_timestamp,
                "event_timestamp": feature_timestamp,
            }
        )

    return pit_join_features(
        references,
        feature_rows,
        knowledge_time_cutoff=knowledge_time_cutoff,
    )


def _parse_timestamp(val: Any) -> datetime:
    if isinstance(val, datetime):
        parsed = val
    else:
        text = str(val or "").strip()
        if not text:
            raise ValueError("timestamp is required")
        if len(text) == 10:
            text += "T00:00:00+00:00"
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        if " " in text and "T" not in text:
            text = text.replace(" ", "T")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"timestamp must be ISO formatted, got {val!r}") from exc
    parsed = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def pit_join_features(
    references: list[dict[str, Any]],
    features: list[dict[str, Any]],
    *,
    knowledge_time_cutoff: Any | None = None,
) -> list[dict[str, Any]]:
    cutoff = _parse_timestamp(knowledge_time_cutoff) if knowledge_time_cutoff is not None else None
    output: list[dict[str, Any]] = []
    by_ticker: dict[str, list[dict[str, Any]]] = {}
    for feature in features:
        by_ticker.setdefault(str(feature["ticker"]).upper(), []).append(feature)
    for ticker_features in by_ticker.values():
        ticker_features.sort(
            key=lambda item: _parse_timestamp(
                item.get("known_from_ts") or item.get("event_timestamp")
            ),
            reverse=True,
        )
    for reference in references:
        ticker = str(reference["ticker"]).upper()
        ref_ts = _parse_timestamp(
            reference.get("known_from_ts") or reference.get("event_timestamp")
        )
        candidate = next(
            (
                feature
                for feature in by_ticker.get(ticker, [])
                if (
                    feature_ts := _parse_timestamp(
                        feature.get("known_from_ts") or feature.get("event_timestamp")
                    )
                )
                <= ref_ts
                and (cutoff is None or feature_ts <= cutoff)
            ),
            {},
        )
        output.append(
            {**reference, **{f"feature_{key}": value for key, value in candidate.items()}}
        )
    return output
