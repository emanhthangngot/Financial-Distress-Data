from __future__ import annotations

from typing import Any


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
