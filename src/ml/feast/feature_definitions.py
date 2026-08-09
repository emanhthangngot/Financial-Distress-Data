"""Feast entity + FeatureView definitions for the ``fd_structured`` project.

``FEATURE_VIEW_TTL`` is a plain module-level constant declared before any
Feast import, so ``.venv``'s fast loop can read it without Feast installed
(Feast lives only in ``.venv-phase2`` — D4 lazy-import rule,
phase-04-implementation-notes.md section 0). ``build_feature_objects()`` is
the single place Entity/FeatureView objects are actually constructed; Feast
is imported lazily inside it. ``feature_repo/structured/definitions.py``
(loaded only by the ``feast`` CLI, which runs under ``.venv-phase2``) calls
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
    "company_financial_features": timedelta(days=100),
    "company_risk_features": timedelta(days=100),
    "market_price_features": timedelta(days=2),
    "stream_market_features": timedelta(hours=1),
}

FEATURE_VIEW_RATIONALE: dict[str, str] = {
    "company_financial_features": (
        "A quarterly filing stays the authoritative view of the company until "
        "the next filing lands; 100 days is approximately one quarter plus "
        "filing lag, so nothing expires while it is still the newest truth."
    ),
    "company_risk_features": (
        "Derived from the same quarterly filing as company_financial_features "
        "(obt_company_quarter_risk joins the fact to the label), so it must "
        "not expire before its parent fact does."
    ),
    "market_price_features": (
        "A daily bar is superseded by the next trading session; 2 days "
        "survives a weekend/holiday gap without ever serving a week-old "
        "price as current."
    ),
    "stream_market_features": (
        "Intraday aggregates describe the current trading hour only; a "
        "longer TTL would let the online API answer 'live' with a stale tick."
    ),
}

# Real Gold column/dataset names, verified against src/transforms/gold/*.py
# and src/generator/offline.py — not the generic names in
# phase-04-implementation-notes.md section 3.2, which predates reading the
# actual builders (they retain every Silver column via ``dict(row)`` /
# ``**row`` plus surrogate keys, not a fixed renamed subset).
GOLD_DATASETS: dict[str, str] = {
    "company_financial_features": "fact_financial_statement",
    "company_risk_features": "obt_company_quarter_risk",
    "market_price_features": "fact_market_price",
}


def gold_source_path(dataset_name: str) -> str:
    """s3:// URI for a Gold dataset's single ``data.parquet`` object,
    resolved through the same ``src.io.paths`` module Phase 1's writers use
    — no new path convention invented for Feast."""
    from src.io.paths import DEFAULT_BUCKET, dataset_object_key

    return f"s3://{dataset_object_key(DEFAULT_BUCKET, 'gold', dataset_name)}"


def build_feature_objects() -> dict[str, Any]:
    """Constructs the entity and every FeatureView. Every ``event_timestamp_
    column`` is declared even though only the online store is read this
    week (phase-04.md:110, non-negotiable) — each Gold builder retains the
    original ``event_timestamp`` field via ``dict(row)``/``**row``."""
    from feast import Entity, FeatureView, Field, FileSource, PushSource
    from feast.types import Bool, Float64, Int64, String
    from feast.value_type import ValueType

    ticker = Entity(name=ENTITY_NAME, join_keys=["ticker"], value_type=ValueType.STRING)

    financial_source = FileSource(
        name="fact_financial_statement_source",
        path=gold_source_path(GOLD_DATASETS["company_financial_features"]),
        timestamp_field="event_timestamp",
    )
    company_financial_features = FeatureView(
        name="company_financial_features",
        entities=[ticker],
        ttl=FEATURE_VIEW_TTL["company_financial_features"],
        schema=[
            Field(name="total_assets", dtype=Float64),
            Field(name="total_liabilities", dtype=Float64),
            Field(name="equity", dtype=Float64),
            Field(name="current_assets", dtype=Float64),
            Field(name="current_liabilities", dtype=Float64),
            Field(name="ebit", dtype=Float64),
            Field(name="net_income", dtype=Float64),
        ],
        source=financial_source,
        description=FEATURE_VIEW_RATIONALE["company_financial_features"],
    )

    risk_source = FileSource(
        name="obt_company_quarter_risk_source",
        path=gold_source_path(GOLD_DATASETS["company_risk_features"]),
        timestamp_field="event_timestamp",
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
        name="fact_market_price_source",
        path=gold_source_path(GOLD_DATASETS["market_price_features"]),
        timestamp_field="event_timestamp",
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
        ],
        source=price_source,
        description=FEATURE_VIEW_RATIONALE["market_price_features"],
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
        "stream_market_features": stream_market_features,
    }


# Touched to trigger the stream-feature-offline/online workflows after secrets configuration.
