from src.transforms.keys import stable_company_key
from src.transforms.silver_to_gold import (
    build_dim_company,
    build_dim_date,
    build_fact_financial_statement,
    build_fact_market_alert,
    build_fact_news_sentiment,
    build_feat_company_financial_4q,
    build_feat_company_market_30d,
    build_feat_company_news_30d,
    build_obt_company_quarter_risk,
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


def test_fact_financial_statement_preserves_statement_type():
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
                "statement_type": "consolidated",
                "created_ts": "2026-01-30T00:00:00+00:00",
            }
        ]
    )[0]

    assert fact["statement_type"] == "consolidated"


def test_pit_join_never_uses_future_feature_timestamp():
    joined = pit_join_features(
        [{"ticker": "AAA", "event_timestamp": "2026-01-10"}],
        [
            {"ticker": "AAA", "event_timestamp": "2026-01-09", "value": 1},
            {"ticker": "AAA", "event_timestamp": "2026-01-11", "value": 2},
        ],
    )
    assert joined[0]["feature_value"] == 1


def test_obt_includes_label_metadata_fields():
    financial_fact = {
        "ticker": "AAA",
        "report_period": "2025Q4",
        "total_assets": 1000,
        "total_liabilities": 500,
        "equity": 500,
        "current_assets": 300,
        "current_liabilities": 200,
        "net_income": 80,
        "ebit": 120,
        "interest_expense": 20,
    }
    labels = [
        {
            "ticker": "AAA",
            "report_period": "2025Q4",
            "distress_label": 0,
            "distress_reason": "z_score_safe_zone",
            "z_score": 3.0,
            "label_source": "rule_based_v1",
            "label_confidence": "high",
            "training_eligible": True,
        }
    ]

    obt = build_obt_company_quarter_risk([financial_fact], labels)[0]

    assert obt["label_source"] == "rule_based_v1"
    assert obt["label_confidence"] == "high"
    assert obt["training_eligible"] is True


def test_dim_date_materializes_calendar_range():
    dim = build_dim_date("2026-01-01", "2026-01-03")

    assert [row["date_key"] for row in dim] == [20260101, 20260102, 20260103]
    assert dim[0]["quarter"] == 1


def test_fact_news_sentiment_has_company_and_date_keys():
    fact = build_fact_news_sentiment(
        [
            {
                "event_id": "news-1",
                "ticker": "AAA",
                "event_timestamp": "2026-01-02T09:00:00+00:00",
                "created_ts": "2026-01-02T09:01:00+00:00",
                "sentiment_score": -0.4,
                "risk_keyword_flag": True,
                "severity_score": 0.8,
            }
        ]
    )[0]

    assert fact["company_key"] == stable_company_key("AAA")
    assert fact["date_key"] == 20260102
    assert fact["risk_keyword_flag"] is True


def test_fact_market_alert_has_company_date_keys_and_deduplicates_event_id():
    facts = build_fact_market_alert(
        [
            {
                "event_id": "alert-1",
                "ticker": "aaa",
                "event_timestamp": "2026-01-02T09:00:00+00:00",
                "created_ts": "2026-01-02T09:01:00+00:00",
                "alert_type": "price_drop",
            },
            {
                "event_id": "alert-1",
                "ticker": "AAA",
                "event_timestamp": "2026-01-02T09:00:00+00:00",
                "created_ts": "2026-01-02T09:02:00+00:00",
                "alert_type": "price_drop",
            },
        ]
    )

    assert len(facts) == 1
    assert facts[0]["ticker"] == "AAA"
    assert facts[0]["company_key"] == stable_company_key("AAA")
    assert facts[0]["date_key"] == 20260102


def test_split_feature_tables_are_materialized_from_gold_rows():
    financial = [
        {
            "ticker": "AAA",
            "report_period": "2025Q4",
            "event_timestamp": "2026-01-30",
            "current_ratio": 1.5,
            "debt_to_asset": 0.5,
            "z_score": 3.0,
        }
    ]
    market = [
        {
            "ticker": "AAA",
            "trading_date": "2026-01-15",
            "event_timestamp": "2026-01-15",
            "daily_return": 0.1,
            "volatility_signal": True,
        }
    ]
    news = [
        {
            "ticker": "AAA",
            "event_timestamp": "2026-01-20T00:00:00+00:00",
            "sentiment_score": -0.5,
            "risk_keyword_flag": True,
            "severity_score": 0.9,
        }
    ]

    assert build_feat_company_financial_4q(financial)[0]["feature_family"] == "financial_4q"
    assert build_feat_company_market_30d(market)[0]["feature_family"] == "market_30d"
    assert build_feat_company_news_30d(news)[0]["feature_family"] == "news_30d"
