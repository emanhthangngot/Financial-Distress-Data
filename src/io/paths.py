from __future__ import annotations

DEFAULT_BUCKET = "financial-distress-lake"


def dataset_object_key(bucket: str, layer: str, dataset_name: str) -> str:
    return f"{bucket}/{layer}/{dataset_name}/data.parquet"


def stage1_dataset_object_keys(bucket: str = DEFAULT_BUCKET) -> list[str]:
    datasets = [
        ("bronze", "companies"),
        ("bronze", "financial_statements"),
        ("bronze", "market_prices_daily"),
        ("silver", "companies"),
        ("silver", "financial_statements"),
        ("silver", "market_prices_daily"),
        ("gold", "dim_company"),
        ("gold", "fact_financial_statement"),
        ("gold", "fact_market_price"),
        ("gold", "distress_labels"),
        ("gold", "obt_company_quarter_risk"),
        ("gold", "feat_company_unified"),
    ]
    return [dataset_object_key(bucket, layer, dataset_name) for layer, dataset_name in datasets]
