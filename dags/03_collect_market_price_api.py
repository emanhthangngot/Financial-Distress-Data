"""
DAG 03 - Collect market prices.

Pulls daily OHLCV bars for the watchlist from the market-price collector. Output is
Bronze-zone raw price history; Silver and Gold transforms derive 30-day return
volatility and distress features from this feed.
"""

from __future__ import annotations

from dags.utils.dag_utils import DEFAULT_ARGS, airflow_imports
from src.collectors.market_price_collector import collect_market_prices

DAG, PythonOperator = airflow_imports()


def _collect() -> list[dict]:
    return collect_market_prices(["AAA", "BBB"], 2024, 2025)


if DAG is not None:
    with DAG(
        dag_id="03_collect_market_price_api",
        default_args=DEFAULT_ARGS,
        schedule=None,
        catchup=False,
        tags=["financial-distress", "stage-1"],
    ) as dag:
        PythonOperator(task_id="call_historical_price_api", python_callable=_collect)
