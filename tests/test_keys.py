import pytest

from src.transforms.keys import (
    company_version_key,
    date_key,
    resolve_company_version_key,
)


def test_company_version_key_is_stable_and_case_insensitive():
    valid_from = "2025-01-01T00:00:00+00:00"
    assert company_version_key("aaa", valid_from) == company_version_key("AAA", valid_from)
    assert company_version_key("AAA", valid_from) == "34ba4ed1bf03b968"


def test_resolve_company_version_key_requires_exactly_one_range_match():
    dim_rows = [
        {
            "ticker": "AAA",
            "company_version_key": "old-version",
            "valid_from_ts": "2025-01-01T00:00:00+00:00",
            "valid_to_ts": "2026-01-01T00:00:00+00:00",
        },
        {
            "ticker": "AAA",
            "company_version_key": "current-version",
            "valid_from_ts": "2026-01-01T00:00:00+00:00",
            "valid_to_ts": None,
        },
    ]

    assert (
        resolve_company_version_key("aaa", "2025-06-01T00:00:00+00:00", dim_rows) == "old-version"
    )
    with pytest.raises(ValueError, match="found 0"):
        resolve_company_version_key("AAA", "2024-01-01T00:00:00+00:00", dim_rows)
    with pytest.raises(ValueError, match="found 2"):
        resolve_company_version_key(
            "AAA",
            "2025-06-01T00:00:00+00:00",
            [
                *dim_rows,
                {
                    "ticker": "AAA",
                    "company_version_key": "overlap",
                    "valid_from_ts": "2025-03-01T00:00:00+00:00",
                    "valid_to_ts": "2025-09-01T00:00:00+00:00",
                },
            ],
        )


def test_date_key_uses_yyyymmdd():
    assert date_key("2026-05-30T12:00:00+00:00") == 20260530
