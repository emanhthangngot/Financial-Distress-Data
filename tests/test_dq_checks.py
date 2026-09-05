from src.quality.dq_checks import (
    check_freshness,
    check_not_null,
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
