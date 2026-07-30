from __future__ import annotations

from typing import Any

from src.transforms.compute_distress_labels import compute_labels
from src.transforms.features.pit import (
    build_feat_company_financial_4q,
    build_feat_company_market_30d,
    build_feat_company_news_30d,
    build_feat_company_unified,
    pit_join_features,
)
from src.transforms.gold.dim_company import build_dim_company, build_dim_date, merge_dim_company
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


def build_distress_labels(financial_statement_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return compute_labels(financial_statement_rows)


__all__ = [
    "build_dim_company",
    "build_dim_date",
    "merge_dim_company",
    "build_distress_labels",
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
