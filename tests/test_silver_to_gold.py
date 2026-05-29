from src.transforms.keys import stable_company_key
from src.transforms.silver_to_gold import (
    build_dim_company,
    build_fact_financial_statement,
    pit_join_features,
)


def test_dim_company_scd2_rebuild_keeps_company_key_stable():
    dim = build_dim_company(
        [
            {
                "ticker": "AAA",
                "company_name": "AAA",
                "exchange": "HOSE",
                "industry": "Old",
                "sector": "Industrial",
                "created_ts": "2025-01-01T00:00:00+00:00",
            },
            {
                "ticker": "AAA",
                "company_name": "AAA",
                "exchange": "HOSE",
                "industry": "New",
                "sector": "Industrial",
                "created_ts": "2026-01-01T00:00:00+00:00",
            },
        ]
    )
    assert len(dim) == 2
    assert {row["company_key"] for row in dim} == {stable_company_key("AAA")}
    assert dim[0]["is_current"] is False
    assert dim[1]["is_current"] is True


def test_fact_financial_statement_has_company_and_date_keys():
    fact = build_fact_financial_statement(
        [
            {
                "ticker": "AAA",
                "report_period": "2025Q4",
                "fiscal_year": 2025,
                "fiscal_quarter": 4,
                "total_assets": 1000,
                "total_liabilities": 500,
                "equity": 500,
                "report_release_date": "2026-01-30",
                "created_ts": "2026-01-30T00:00:00+00:00",
            }
        ]
    )[0]
    assert fact["company_key"] == stable_company_key("AAA")
    assert fact["date_key"] == 20260130


def test_pit_join_never_uses_future_feature_timestamp():
    joined = pit_join_features(
        [{"ticker": "AAA", "event_timestamp": "2026-01-10"}],
        [
            {"ticker": "AAA", "event_timestamp": "2026-01-09", "value": 1},
            {"ticker": "AAA", "event_timestamp": "2026-01-11", "value": 2},
        ],
    )
    assert joined[0]["feature_value"] == 1
