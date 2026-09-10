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


def _as_of_rows(rows: list[dict[str, Any]], ticker: str, cutoff: datetime) -> list[dict[str, Any]]:
    candidates = [
        row
        for row in rows
        if str(row.get("ticker", "")).upper() == ticker
        and _parse_timestamp(row.get("known_from_ts") or row.get("event_timestamp")) <= cutoff
    ]
    by_period: dict[Any, dict[str, Any]] = {}
    for row in candidates:
        period = row.get("report_period") or row.get("trading_date") or row.get("article_hash")
        current = by_period.get(period)
        if current is None or _parse_timestamp(
            row.get("known_from_ts") or row.get("event_timestamp")
        ) > _parse_timestamp(current.get("known_from_ts") or current.get("event_timestamp")):
            by_period[period] = row
    return list(by_period.values())


def _feature_metadata(
    ticker: str, cutoff: datetime, created_ts: Any, family: str, count: int, expected: int
) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "event_timestamp": cutoff,
        "created_timestamp": created_ts,
        "known_from_ts": cutoff,
        "feature_family": family,
        "window_period_count": count,
        "feature_completeness": count / expected,
    }


def build_feat_company_financial_4q(financial_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    tickers = sorted({str(row["ticker"]).upper() for row in financial_rows})
    numeric_fields = (
        "current_ratio",
        "debt_to_asset",
        "debt_to_equity",
        "roa",
        "roe",
        "ebit_interest_coverage",
        "z_score",
    )
    for ticker in tickers:
        ticker_rows = [row for row in financial_rows if str(row["ticker"]).upper() == ticker]
        cutoffs = sorted(
            {
                _parse_timestamp(
                    _knowledge_timestamp(
                        row, "report_release_date", "event_timestamp", "created_ts"
                    )
                )
                for row in ticker_rows
            }
        )
        for cutoff in cutoffs:
            window = _as_of_rows(ticker_rows, ticker, cutoff)[-4:]
            count = len(window)
            values = {
                field: (
                    sum(float(row[field]) for row in window if row.get(field) is not None) / count
                    if count == 4 and all(row.get(field) is not None for row in window)
                    else None
                )
                for field in numeric_fields
            }
            output = _feature_metadata(
                ticker,
                cutoff,
                window[-1].get("created_ts") if window else None,
                "financial_4q",
                count,
                4,
            )
            output.update({"report_period": window[-1].get("report_period") if window else None})
            output.update(values)
            rows.append(output)
    return rows


def build_feat_company_market_30d(market_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ticker in sorted({str(row["ticker"]).upper() for row in market_rows}):
        ticker_rows = [row for row in market_rows if str(row["ticker"]).upper() == ticker]
        cutoffs = sorted(
            {
                _parse_timestamp(
                    _knowledge_timestamp(row, "event_timestamp", "created_ts", "trading_date")
                )
                for row in ticker_rows
            }
        )
        for cutoff in cutoffs:
            window = [
                row
                for row in _as_of_rows(ticker_rows, ticker, cutoff)
                if cutoff.date().toordinal()
                - _parse_timestamp(row["trading_date"]).date().toordinal()
                < 30
            ]
            count = len(window)
            output = _feature_metadata(
                ticker,
                cutoff,
                window[-1].get("created_ts") if window else None,
                "market_30d",
                count,
                30,
            )
            output.update(
                {
                    "trading_date": cutoff.date(),
                    "close_price": (
                        sum(float(row["close_price"]) for row in window) / count
                        if count == 30
                        else None
                    ),
                    "daily_return": (
                        sum(
                            float(row["daily_return"])
                            for row in window
                            if row.get("daily_return") is not None
                        )
                        / count
                        if count == 30
                        and all(row.get("daily_return") is not None for row in window)
                        else None
                    ),
                    "volatility_signal": (
                        any(row.get("volatility_signal") for row in window) if count == 30 else None
                    ),
                }
            )
            rows.append(output)
    return rows


def build_feat_company_news_30d(news_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ticker in sorted({str(row["ticker"]).upper() for row in news_rows}):
        ticker_rows = [row for row in news_rows if str(row["ticker"]).upper() == ticker]
        cutoffs = sorted(
            {
                _parse_timestamp(_knowledge_timestamp(row, "event_timestamp", "created_ts"))
                for row in ticker_rows
            }
        )
        for cutoff in cutoffs:
            window = [
                row
                for row in _as_of_rows(ticker_rows, ticker, cutoff)
                if cutoff.date().toordinal()
                - _parse_timestamp(
                    row.get("published_ts")
                    or row.get("known_from_ts")
                    or row.get("event_timestamp")
                )
                .date()
                .toordinal()
                < 30
            ]
            count = len(window)
            output = _feature_metadata(
                ticker,
                cutoff,
                window[-1].get("created_ts") if window else None,
                "news_30d",
                count,
                30,
            )
            output.update(
                {
                    "article_count": count,
                    "sentiment_score": (
                        sum(
                            float(row["sentiment_score"])
                            for row in window
                            if row.get("sentiment_score") is not None
                        )
                        / count
                        if count and all(row.get("sentiment_score") is not None for row in window)
                        else None
                    ),
                    "risk_keyword_count": sum(bool(row.get("risk_keyword_flag")) for row in window),
                    "severity_score": max(
                        (row.get("severity_score") or 0 for row in window), default=None
                    ),
                }
            )
            rows.append(output)
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
