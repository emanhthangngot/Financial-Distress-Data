from src.transforms.keys import date_key, stable_company_key


def test_company_key_is_stable_and_case_insensitive():
    assert stable_company_key("aaa") == stable_company_key("AAA")
    assert stable_company_key("AAA") == "cb1ad2119d8fafb6"


def test_date_key_uses_yyyymmdd():
    assert date_key("2026-05-30T12:00:00+00:00") == 20260530
