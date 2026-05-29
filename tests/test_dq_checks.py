from src.quality.dq_checks import check_not_null, check_referential_integrity, check_retention


def test_critical_not_null_failure():
    result = check_not_null([{"ticker": None}], "companies", "ticker")
    assert result.status == "fail"
    assert result.severity == "critical"


def test_referential_integrity_failure():
    result = check_referential_integrity(
        [{"company_key": "missing"}], {"known"}, "fact_financial_statement", "company_key"
    )
    assert result.status == "fail"
    assert result.severity == "critical"


def test_retention_warning():
    result = check_retention(100, 50, "stg_companies")
    assert result.status == "warning"
    assert result.severity == "warning"
