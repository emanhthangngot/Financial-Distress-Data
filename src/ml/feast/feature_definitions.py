"""Feast entity + FeatureView definitions for the ``fd_structured`` project.

``FEATURE_VIEW_TTL`` is a plain module-level constant declared before any
Feast import, so ``.venv``'s fast loop can read it without Feast installed
(Feast lives only in ``.venv-platform`` — D4 lazy-import rule,
phase-04-implementation-notes.md section 0). ``build_feature_objects()`` is
the single place Entity/FeatureView objects are actually constructed; Feast
is imported lazily inside it. ``feature_repo/structured/definitions.py``
(loaded only by the ``feast`` CLI, which runs under ``.venv-platform``) calls
it once and injects the result into its own module globals — this is a
reasoned resolution between the star-re-export design in
phase-04-implementation-notes.md section 3.4 (verified working against
Feast 0.65 in a throwaway spike, 2026-08-08) and D4: a plain
``from ... import *`` would need every re-exported name to already be a
real object at *this* module's import time, which conflicts with keeping
Feast import lazy here.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

ENTITY_NAME = "ticker"

FEATURE_VIEW_TTL: dict[str, timedelta] = {
    "company_financial_features": timedelta(days=400),
    "company_risk_features": timedelta(days=400),
    "market_price_features": timedelta(days=45),
    "news_features": timedelta(days=45),
    "unified_features": timedelta(days=400),
    "stream_market_features": timedelta(hours=1),
}

FEATURE_VIEW_RATIONALE: dict[str, str] = {
    "company_financial_features": (
        "A quarterly filing stays authoritative across a four-quarter window "
        "plus publication lag; 400 days prevents expiry before replacement."
    ),
    "company_risk_features": (
        "Derived from the quarterly financial fact and label; it shares the "
        "400-day parent horizon so the risk leg cannot expire first."
    ),
    "market_price_features": (
        "A 30-day daily market window plus a 15-day holiday and late-arrival "
        "buffer requires 45 days to avoid serving an incomplete feature."
    ),
    "news_features": (
        "News uses the same 30-day observation window as market data; 45 days "
        "absorbs quiet periods and late-arriving articles."
    ),
    "unified_features": (
        "The unified feature joins financial, market, and news inputs; 400 "
        "days matches the longest quarterly financial input."
    ),
    "stream_market_features": (
        "Intraday aggregates describe the current trading hour; a longer TTL "
        "would allow stale ticks to answer a live query."
    ),
}

# Real Gold column/dataset names, verified against src/transforms/gold/*.py
# and src/generator/offline.py.
GOLD_DATASETS: dict[str, str] = {
    "company_financial_features": "feat_company_financial_4q",
    "company_risk_features": "obt_company_quarter_risk",
    "market_price_features": "feat_company_market_30d",
    "news_features": "feat_company_news_30d",
    "unified_features": "feat_company_unified",
}


def gold_source_path(dataset_name: str) -> str:
    """Return the partitioned Gold dataset prefix used by Feast FileSource."""
    from src.io.paths import DEFAULT_BUCKET

    return f"s3://{DEFAULT_BUCKET}/gold/{dataset_name}/"


def build_feature_objects() -> dict[str, Any]:
    """Constructs the entity and every FeatureView. Every ``FileSource``
    binds Feast's ``event_timestamp`` join axis to the Gold ``known_from_ts``
    column (ADR-017 §Feast temporal contract, F14) — never a raw
    ``event_timestamp`` field, which for ``fact_financial_statement`` in
    particular carries a different, non-knowledge-time value derived from
    the source row rather than ``report_release_date``."""
    from feast import Entity, FeatureView, Field, FileSource, PushSource
    from feast.types import Bool, Float64, Int64, String
    from feast.value_type import ValueType

    ticker = Entity(name=ENTITY_NAME, join_keys=["ticker"], value_type=ValueType.STRING)

    financial_source = FileSource(
        name="feat_company_financial_4q_source",
        path=gold_source_path(GOLD_DATASETS["company_financial_features"]),
        timestamp_field="known_from_ts",
        created_timestamp_column="created_timestamp",
    )
    company_financial_features = FeatureView(
        name="company_financial_features",
        entities=[ticker],
        ttl=FEATURE_VIEW_TTL["company_financial_features"],
        schema=[
            Field(name="current_ratio", dtype=Float64),
            Field(name="debt_to_asset", dtype=Float64),
            Field(name="debt_to_equity", dtype=Float64),
            Field(name="roa", dtype=Float64),
            Field(name="roe", dtype=Float64),
            Field(name="ebit_interest_coverage", dtype=Float64),
            Field(name="z_score", dtype=Float64),
            Field(name="window_period_count", dtype=Int64),
            Field(name="feature_completeness", dtype=Float64),
        ],
        source=financial_source,
        description=FEATURE_VIEW_RATIONALE["company_financial_features"],
    )

    risk_source = FileSource(
        name="obt_company_quarter_risk_source",
        path=gold_source_path(GOLD_DATASETS["company_risk_features"]),
        timestamp_field="known_from_ts",
        created_timestamp_column="created_timestamp",
    )
    company_risk_features = FeatureView(
        name="company_risk_features",
        entities=[ticker],
        ttl=FEATURE_VIEW_TTL["company_risk_features"],
        schema=[
            Field(name="current_ratio", dtype=Float64),
            Field(name="debt_to_asset", dtype=Float64),
            Field(name="roa", dtype=Float64),
            Field(name="z_score", dtype=Float64),
            Field(name="distress_label", dtype=Int64),
            Field(name="distress_reason", dtype=String),
            Field(name="training_eligible", dtype=Bool),
        ],
        source=risk_source,
        description=FEATURE_VIEW_RATIONALE["company_risk_features"],
    )

    price_source = FileSource(
        name="feat_company_market_30d_source",
        path=gold_source_path(GOLD_DATASETS["market_price_features"]),
        timestamp_field="known_from_ts",
        created_timestamp_column="created_timestamp",
    )
    market_price_features = FeatureView(
        name="market_price_features",
        entities=[ticker],
        ttl=FEATURE_VIEW_TTL["market_price_features"],
        schema=[
            Field(name="close_price", dtype=Float64),
            Field(name="volume", dtype=Int64),
            Field(name="daily_return", dtype=Float64),
            Field(name="volatility_signal", dtype=Bool),
            Field(name="window_period_count", dtype=Int64),
            Field(name="feature_completeness", dtype=Float64),
        ],
        source=price_source,
        description=FEATURE_VIEW_RATIONALE["market_price_features"],
    )

    news_source = FileSource(
        name="feat_company_news_30d_source",
        path=gold_source_path(GOLD_DATASETS["news_features"]),
        timestamp_field="known_from_ts",
        created_timestamp_column="created_timestamp",
    )
    news_features = FeatureView(
        name="news_features",
        entities=[ticker],
        ttl=FEATURE_VIEW_TTL["news_features"],
        schema=[
            Field(name="article_count", dtype=Int64),
            Field(name="sentiment_score", dtype=Float64),
            Field(name="risk_keyword_count", dtype=Int64),
            Field(name="severity_score", dtype=Float64),
            Field(name="window_period_count", dtype=Int64),
            Field(name="feature_completeness", dtype=Float64),
        ],
        source=news_source,
        description=FEATURE_VIEW_RATIONALE["news_features"],
    )

    unified_source = FileSource(
        name="feat_company_unified_source",
        path=gold_source_path(GOLD_DATASETS["unified_features"]),
        timestamp_field="known_from_ts",
        created_timestamp_column="created_timestamp",
    )
    unified_features = FeatureView(
        name="unified_features",
        entities=[ticker],
        ttl=FEATURE_VIEW_TTL["unified_features"],
        schema=[
            Field(name="feature_close_price", dtype=Float64),
            Field(name="feature_daily_return", dtype=Float64),
            Field(name="feature_volatility_signal", dtype=Bool),
        ],
        source=unified_source,
        description=FEATURE_VIEW_RATIONALE["unified_features"],
    )

    # Batch fallback = the same price fact, per phase-04.md:108 (every
    # FeatureView must declare an offline source, no skipping it for the
    # stream-only view).
    stream_source = PushSource(
        name="stream_market_features_push_source",
        batch_source=price_source,
    )
    stream_market_features = FeatureView(
        name="stream_market_features",
        entities=[ticker],
        ttl=FEATURE_VIEW_TTL["stream_market_features"],
        schema=[
            Field(name="last_price", dtype=Float64),
            Field(name="event_count_1h", dtype=Int64),
            Field(name="price_change_pct_1h", dtype=Float64),
        ],
        source=stream_source,
        description=FEATURE_VIEW_RATIONALE["stream_market_features"],
    )

    return {
        "ticker": ticker,
        "company_financial_features": company_financial_features,
        "company_risk_features": company_risk_features,
        "market_price_features": market_price_features,
        "news_features": news_features,
        "unified_features": unified_features,
        "stream_market_features": stream_market_features,
    }


# Touched to trigger stream-feature-offline/online after the gitops-pr base-branch fix.
