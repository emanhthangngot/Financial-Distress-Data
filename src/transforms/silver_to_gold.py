"""
Silver-to-Gold transform entry point.

Re-exports dimension builders, fact builders, the rule-based distress labeler, and the unified
feature builder from ``src.transforms.gold`` and ``src.transforms.features``. Callers depend on this
module rather than the inner subpackages.
"""

from __future__ import annotations

from src.transforms.features.point_in_time import (
    build_feat_company_financial_4q,
    build_feat_company_market_30d,
    build_feat_company_news_30d,
    build_feat_company_unified,
    pit_join_features,
)
from src.transforms.gold.dim_company import build_dim_company, build_dim_date
from src.transforms.gold.fact_financial_statement import (
    build_fact_financial_statement,
    build_fact_financial_statement_spark,
)
from src.transforms.gold.fact_market_alert import build_fact_market_alert
from src.transforms.gold.fact_market_price import (
    build_fact_market_price,
    build_fact_market_price_spark,
)
from src.transforms.gold.fact_news_sentiment import build_fact_news_sentiment
from src.transforms.gold.obt_company_quarter_risk import build_obt_company_quarter_risk
from src.transforms.gold.parquet import write_partitioned_parquet

__all__ = [
    "build_dim_company",
    "build_dim_date",
    "build_fact_financial_statement",
    "build_fact_financial_statement_spark",
    "build_fact_market_alert",
    "build_fact_market_price",
    "build_fact_market_price_spark",
    "build_fact_news_sentiment",
    "build_feat_company_financial_4q",
    "build_feat_company_market_30d",
    "build_feat_company_news_30d",
    "build_feat_company_unified",
    "build_obt_company_quarter_risk",
    "pit_join_features",
    "write_partitioned_parquet",
]
