"""Pins src/llm/data_governance.py: license allowlist, PII regexes
(positive + negative per type), rate limiter spacing, retry policy retries
5xx/429 and not 4xx, quarantine-routing (not silent-drop) behaviour."""

from __future__ import annotations

import time

import pytest

from src.llm.data_governance import (
    GovernanceViolation,
    RateLimiter,
    assert_metadata_complete,
    check_access_class,
    check_licensing,
    detect_pii,
    enforce_chunk_governance,
    redact,
    retry_policy,
)
from src.llm.rag_pipeline import Chunk

_VALID_CHUNK = Chunk(
    document_hash="doc-1",
    content_hash="content-1",
    chunk_index=0,
    chunk_text="Vinamilk cong bo ket qua kinh doanh quy gan nhat.",
    source_uri="tests/phase2/fixtures/rag_corpus/vnstock_news_vnm.txt",
    company="VNM",
    report_date=None,
    parser_version="v1",
    access_class="public_market_commentary",
)


# --- licensing / access class -------------------------------------------------


def test_check_licensing_allows_registered_license() -> None:
    assert check_licensing("vnstock_public_api_terms", {"vnstock_public_api_terms"}) is None


def test_check_licensing_rejects_unknown_license() -> None:
    reason = check_licensing("gpl-3.0", {"vnstock_public_api_terms"})
    assert reason is not None and "gpl-3.0" in reason


def test_check_access_class_rejects_unallowed_class() -> None:
    reason = check_access_class("internal_only", {"public_market_commentary"})
    assert reason is not None and "internal_only" in reason


# --- metadata completeness ----------------------------------------------------


def test_assert_metadata_complete_passes_valid_chunk() -> None:
    assert_metadata_complete(_VALID_CHUNK)


@pytest.mark.parametrize(
    "field_name",
    ["document_hash", "content_hash", "chunk_text", "source_uri", "parser_version", "access_class"],
)
def test_assert_metadata_complete_raises_on_each_empty_field(field_name: str) -> None:
    payload = _VALID_CHUNK.__dict__ | {field_name: ""}
    chunk = Chunk(**payload)
    with pytest.raises(GovernanceViolation, match=field_name):
        assert_metadata_complete(chunk)


def test_assert_metadata_complete_raises_on_negative_chunk_index() -> None:
    chunk = Chunk(**(_VALID_CHUNK.__dict__ | {"chunk_index": -1}))
    with pytest.raises(GovernanceViolation, match="chunk_index"):
        assert_metadata_complete(chunk)


def test_assert_metadata_complete_allows_zero_chunk_index() -> None:
    # chunk_index=0 is falsy in Python — must not be treated as "missing".
    chunk = Chunk(**(_VALID_CHUNK.__dict__ | {"chunk_index": 0}))
    assert_metadata_complete(chunk)


def test_assert_metadata_complete_allows_null_company_and_report_date() -> None:
    chunk = Chunk(**(_VALID_CHUNK.__dict__ | {"company": None, "report_date": None}))
    assert_metadata_complete(chunk)


# --- PII detection -------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected_type"),
    [
        ("Lien he: nguyen.van.a@example.com de biet them chi tiet.", "email"),
        ("Goi cho toi qua so 0912345678 neu can ho tro.", "phone"),
        ("Goi cho toi qua so 0912 345 678 neu can ho tro.", "phone"),
        ("Goi cho toi qua so 0912-345-678 neu can ho tro.", "phone"),
        ("Hotline: +84 912 345 678", "phone"),
        ("So CCCD cua khach hang la 012345678901.", "vn_national_id"),
        ("So tai khoan ngan hang: 0123456789012", "bank_account"),
    ],
)
def test_detect_pii_positive(text: str, expected_type: str) -> None:
    findings = detect_pii(text)
    assert any(finding.finding_type == expected_type for finding in findings)


def test_detect_pii_negative_on_clean_financial_text() -> None:
    findings = detect_pii(_VALID_CHUNK.chunk_text)
    assert findings == []


def test_detect_pii_ignores_bare_financial_figures_without_id_or_bank_context() -> None:
    # A 9-16 digit revenue/asset figure is not, by itself, a national ID or
    # bank account number — only a nearby keyword should make it one.
    text = "Doanh thu thuan dat 123456789012 dong trong quy vua qua."
    findings = detect_pii(text)
    assert findings == []


def test_detect_pii_phone_does_not_misread_a_national_id_substring() -> None:
    # A 12-digit CCCD used to be misreported as "phone" because the old
    # phone pattern had no leading word boundary.
    findings = detect_pii("So CCCD: 001099012345")
    types = [finding.finding_type for finding in findings]
    assert "phone" not in types
    assert "vn_national_id" in types


def test_detect_pii_does_not_double_count_overlapping_spans() -> None:
    # A 12-digit national ID also matches the generic bank-account pattern;
    # it must be reported once, as the more specific type.
    findings = detect_pii("So CCCD: 012345678901")
    types = [finding.finding_type for finding in findings]
    assert types.count("vn_national_id") == 1
    assert "bank_account" not in types


def test_redact_replaces_matched_spans_without_leaking_value() -> None:
    findings = detect_pii("Email: test@example.com")
    redacted = redact("Email: test@example.com", findings)
    assert "test@example.com" not in redacted
    assert "[REDACTED:email]" in redacted


# --- enforce_chunk_governance (the per-chunk orchestrator) ---------------------


def test_enforce_chunk_governance_passes_clean_chunk() -> None:
    reason = enforce_chunk_governance(
        _VALID_CHUNK,
        "vnstock_public_api_terms",
        {"vnstock_public_api_terms"},
        {"public_market_commentary"},
    )
    assert reason is None


def test_enforce_chunk_governance_returns_reason_for_bad_license_without_raising() -> None:
    reason = enforce_chunk_governance(
        _VALID_CHUNK,
        "unlicensed",
        {"vnstock_public_api_terms"},
        {"public_market_commentary"},
    )
    assert reason is not None and "unlicensed" in reason


def test_enforce_chunk_governance_returns_reason_for_pii() -> None:
    chunk = Chunk(**(_VALID_CHUNK.__dict__ | {"chunk_text": "Email: leak@example.com"}))
    reason = enforce_chunk_governance(
        chunk,
        "vnstock_public_api_terms",
        {"vnstock_public_api_terms"},
        {"public_market_commentary"},
    )
    assert reason is not None and "pii detected" in reason


def test_enforce_chunk_governance_raises_on_metadata_gap() -> None:
    chunk = Chunk(**(_VALID_CHUNK.__dict__ | {"source_uri": ""}))
    with pytest.raises(GovernanceViolation):
        enforce_chunk_governance(
            chunk,
            "vnstock_public_api_terms",
            {"vnstock_public_api_terms"},
            {"public_market_commentary"},
        )


# --- rate limiter ---------------------------------------------------------------


def test_rate_limiter_spaces_calls_by_the_configured_interval() -> None:
    limiter = RateLimiter(rps=10)  # 100ms minimum spacing
    start = time.monotonic()
    limiter.acquire()
    limiter.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.09  # small tolerance below the 100ms floor


def test_rate_limiter_first_call_never_waits() -> None:
    limiter = RateLimiter(rps=1)  # 1s minimum spacing
    start = time.monotonic()
    limiter.acquire()
    assert time.monotonic() - start < 0.05


# --- retry policy ----------------------------------------------------------------


def test_retry_policy_retries_on_5xx_and_not_on_4xx() -> None:
    import requests

    policy = retry_policy()
    attempts = {"count": 0}

    @policy
    def flaky_5xx():
        attempts["count"] += 1
        if attempts["count"] < 3:
            response = requests.Response()
            response.status_code = 503
            raise requests.HTTPError(response=response)
        return "ok"

    assert flaky_5xx() == "ok"
    assert attempts["count"] == 3

    @policy
    def always_4xx():
        response = requests.Response()
        response.status_code = 400
        raise requests.HTTPError(response=response)

    with pytest.raises(requests.HTTPError):
        always_4xx()
