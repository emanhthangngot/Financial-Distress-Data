from src.quality.dq_checks import (
    check_freshness,
    check_latest_vintage_unique,
    check_not_null,
    check_null_rate_ceiling,
    check_referential_integrity,
    check_retention,
)


def test_critical_not_null_failure():
    result = check_not_null([{"ticker": None}], "companies", "ticker")
    assert result.status == "fail"
    assert result.severity == "critical"


def test_referential_integrity_failure():
    result = check_referential_integrity(
        [{"company_version_key": "missing"}],
        {"known"},
        "fact_financial_statement",
        "company_version_key",
    )
    assert result.status == "fail"
    assert result.severity == "critical"


def test_retention_warning():
    result = check_retention(100, 50, "stg_companies")
    assert result.status == "warning"
    assert result.severity == "warning"


def test_freshness_warning_when_latest_event_exceeds_sla():
    result = check_freshness(
        [{"event_timestamp": "2026-01-01T00:00:00+00:00"}],
        "market_prices_daily",
        reference_timestamp="2026-01-01T02:30:00+00:00",
        sla_minutes=60,
    )

    assert result.status == "warning"
    assert result.severity == "warning"
    assert result.metric_value == 150.0
    assert result.threshold_value == 60.0


def test_freshness_passes_when_latest_event_is_within_sla():
    result = check_freshness(
        [{"event_timestamp": "2026-01-01T02:00:00+00:00"}],
        "market_prices_daily",
        reference_timestamp="2026-01-01T02:30:00+00:00",
        sla_minutes=60,
    )

    assert result.status == "pass"
    assert result.metric_value == 30.0


def test_latest_vintage_unique_passes_with_exactly_one_flag_per_business_key():
    rows = [
        {"ticker": "AAA", "report_period": "2023Q2", "is_latest_vintage": False},
        {"ticker": "AAA", "report_period": "2023Q2", "is_latest_vintage": True},
    ]
    result = check_latest_vintage_unique(
        rows, "fact_financial_statement", ["ticker", "report_period"]
    )
    assert result.status == "pass"
    assert result.severity == "critical"


def test_latest_vintage_unique_fails_when_two_vintages_both_flagged_latest():
    """AC-P2-4 negative test: forgetting the vintage filter must be a visible failure."""
    rows = [
        {"ticker": "AAA", "report_period": "2023Q2", "is_latest_vintage": True},
        {"ticker": "AAA", "report_period": "2023Q2", "is_latest_vintage": True},
    ]
    result = check_latest_vintage_unique(
        rows, "fact_financial_statement", ["ticker", "report_period"]
    )
    assert result.status == "fail"
    assert result.severity == "critical"
    assert result.metric_value == 1.0


def test_null_rate_ceiling_passes_below_threshold():
    rows = [{"run_id": "r1"}] * 19 + [{"run_id": None}]
    result = check_null_rate_ceiling(rows, "ops.failed_records", "run_id", ceiling=0.05)
    assert result.status == "pass"


def test_null_rate_ceiling_fails_above_threshold():
    """F16: an entirely-NULL nullable FK column must fail, not pass vacuously."""
    rows = [{"run_id": None}] * 10
    result = check_null_rate_ceiling(rows, "ops.failed_records", "run_id", ceiling=0.05)
    assert result.status == "fail"
    assert result.severity == "critical"
    assert result.metric_value == 1.0
