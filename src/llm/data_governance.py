"""Governance gates for the RAG ingestion pipeline: licensing, PII
detection/redaction, rate limiting, retry policy, and per-chunk enforcement.

No database access (that lives in ``src.llm.rag.pgvector_store``), so every
function here is testable without a live Postgres connection. ``retry_policy``
is transport-retry configuration rather than a governance *gate* — it lives
here anyway because ``src.llm.rag.embedding``'s DRY TODO explicitly asked for
this hoist target (phase-06-embedding-slice-notes.md Phase E3); a fourth
tiny module just to house it would be over-splitting for one function.

Severity mapping — a deliberate narrowing of
``phase-04-implementation-notes.md`` section 4.4, which frames *any*
governance violation (including license/access-class) as **critical**
(halt the ingestion task). This module instead treats every violation
category the same way: a metadata gap (``assert_metadata_complete``) raises
directly (a pipeline bug, not a per-document event); a
license/access-class/PII violation is **warning-level** — the offending
chunk is routed to quarantine (see
``src.llm.rag.pgvector_store.PgVectorStore.insert_quarantine``) and the batch
continues. Rationale: halting the whole ingestion run on one bad-licensed
document among many would make an entire evidence run all-or-nothing on a
single row, which the quarantine table exists specifically to avoid
recording as an unexplained failure. If the stricter reading is required,
raise ``GovernanceViolation`` from ``enforce_chunk_governance`` instead of
returning a reason string.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.llm.rag_pipeline import Chunk


class GovernanceViolation(Exception):
    """Raised only for a metadata-completeness gap (programmer error, not a
    per-document data-quality event — see module docstring)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class PiiFinding:
    finding_type: str
    span: tuple[int, int]


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# (?<!\d) / (?!\d) bound both ends so this never matches a substring inside a
# longer digit run (e.g. a 12-digit national ID no longer misreports as
# "phone"). Optional separators between digit groups so formatted numbers
# like "0912 345 678" / "0912-345-678" are caught too — the un-anchored,
# separator-blind original pattern missed all of these.
_PHONE_RE = re.compile(r"(?<!\d)(?:\+84|0)(?:[\s.\-]?\d){8,9}(?!\d)")

# vn_national_id and bank_account are bare digit-run patterns with no
# structural way to distinguish a CCCD/CMND or an account number from an
# ordinary financial figure of the same length — a *financial-document*
# corpus is exactly where that ambiguity is worst (revenue, assets, and
# liabilities routinely run 9-16 digits). Both are gated on a nearby
# Vietnamese keyword instead of firing on every bare digit run; see
# detect_pii and _has_keyword_nearby.
_VN_ID_RE = re.compile(r"(?<!\d)\d{9}(?:\d{3})?(?!\d)")
_BANK_ACCOUNT_RE = re.compile(r"(?<!\d)\d{8,16}(?!\d)")

_ID_KEYWORDS = ("cccd", "cmnd", "can cuoc", "chung minh")
_BANK_KEYWORDS = ("stk", "so tai khoan", "tai khoan")
_KEYWORD_WINDOW = 25  # chars of context scanned immediately before a match


def _spans_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def _has_keyword_nearby(text: str, match_start: int, keywords: tuple[str, ...]) -> bool:
    context = text[max(0, match_start - _KEYWORD_WINDOW) : match_start].lower()
    return any(keyword in context for keyword in keywords)


def _add_finding(findings: list[PiiFinding], finding_type: str, span: tuple[int, int]) -> None:
    if any(_spans_overlap(span, existing.span) for existing in findings):
        return  # a more specific pattern already claimed this span
    findings.append(PiiFinding(finding_type, span))


def detect_pii(text: str) -> list[PiiFinding]:
    """Vietnamese national ID, phone, email, bank-account patterns. Findings
    carry only the finding *type* and span — never the matched value — so a
    caller can log/quarantine without leaking the PII itself."""
    findings: list[PiiFinding] = []
    for match in _EMAIL_RE.finditer(text):
        _add_finding(findings, "email", match.span())
    for match in _PHONE_RE.finditer(text):
        _add_finding(findings, "phone", match.span())
    for match in _VN_ID_RE.finditer(text):
        if _has_keyword_nearby(text, match.start(), _ID_KEYWORDS):
            _add_finding(findings, "vn_national_id", match.span())
    for match in _BANK_ACCOUNT_RE.finditer(text):
        if _has_keyword_nearby(text, match.start(), _BANK_KEYWORDS):
            _add_finding(findings, "bank_account", match.span())
    return findings


def redact(text: str, findings: list[PiiFinding]) -> str:
    """Not called by ``RagIngestionPipeline`` today —
    ``ml_metadata.rag_quarantine`` (sql/init_ml_metadata.sql) has no
    chunk-text column at all, so there is nothing to redact into yet; a
    quarantined chunk's raw text is simply never persisted. Kept for the
    quarantine record a future audit-trail column would need — redact,
    never the raw text, into any place PII findings get logged or stored."""
    redacted = text
    for finding in sorted(findings, key=lambda f: f.span[0], reverse=True):
        start, end = finding.span
        redacted = redacted[:start] + f"[REDACTED:{finding.finding_type}]" + redacted[end:]
    return redacted


class RateLimiter:
    """Simple token-bucket-of-one: blocks the caller until ``1/rps`` seconds
    have passed since the last ``acquire()``. Not called by
    ``RagIngestionPipeline.fetch_documents`` today — it reads an instant
    local fixture file, nothing to rate-limit. Each source's
    ``rate_limit_rps`` in configs/rag-sources.yaml is reserved for a future
    live-fetch backend, not read by the current implementation. Not
    thread-safe (unguarded read-modify-write on ``_last_acquire``); fine
    while unused, worth a lock before this is wired to concurrent fetches."""

    def __init__(self, rps: float) -> None:
        self.min_interval = 1.0 / rps if rps > 0 else 0.0
        self._last_acquire: float | None = None

    def acquire(self) -> None:
        now = time.monotonic()
        if self._last_acquire is not None:
            wait = self.min_interval - (now - self._last_acquire)
            if wait > 0:
                time.sleep(wait)
        self._last_acquire = time.monotonic()


def retry_policy() -> Any:
    """Retries only on transport/5xx/429; never on 4xx.

    Hoisted from ``src.llm.rag.embedding._retry_policy`` now that this
    module exists — that was the deliberate DRY placeholder left in
    phase-06-embedding-slice-notes.md Phase E3. ``src.llm.rag.embedding``
    should import this instead of keeping its own copy.
    """
    from tenacity import (
        retry,
        retry_if_exception,
        stop_after_attempt,
        wait_exponential,
    )

    def _is_retryable(exc: BaseException) -> bool:
        import requests

        if isinstance(exc, requests.ConnectionError | requests.Timeout):
            return True
        if isinstance(exc, requests.HTTPError):
            status = exc.response.status_code if exc.response is not None else None
            return status is not None and (status == 429 or status >= 500)
        return False

    return retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )


# The seven fields required non-empty on every chunk (company/report_date
# are the two nullable fields of the documented nine-field metadata
# contract — phase-04-implementation-notes.md section 4.3).
_REQUIRED_CHUNK_FIELDS = (
    "document_hash",
    "content_hash",
    "chunk_text",
    "source_uri",
    "parser_version",
    "access_class",
)


def assert_metadata_complete(chunk: Chunk) -> None:
    """Raises ``GovernanceViolation`` naming the first empty required field."""
    for field_name in _REQUIRED_CHUNK_FIELDS:
        if not getattr(chunk, field_name):
            raise GovernanceViolation(f"chunk missing required field {field_name!r}")
    if chunk.chunk_index is None or chunk.chunk_index < 0:
        raise GovernanceViolation("chunk missing required field 'chunk_index'")


def check_licensing(license_name: str, allowed_licenses: set[str]) -> str | None:
    if license_name in allowed_licenses:
        return None
    return f"license {license_name!r} not in allowlist {sorted(allowed_licenses)}"


def check_access_class(access_class: str, allowed_access_classes: set[str]) -> str | None:
    if access_class in allowed_access_classes:
        return None
    return f"access_class {access_class!r} not in allowed set {sorted(allowed_access_classes)}"


def enforce_chunk_governance(
    chunk: Chunk,
    license_name: str,
    allowed_licenses: set[str],
    allowed_access_classes: set[str],
) -> str | None:
    """Runs metadata completeness (raises on a gap — programmer error),
    then license, access-class, and PII checks (returned as a reason string
    so the caller can quarantine without aborting the batch). Returns
    ``None`` when the chunk is clean."""
    assert_metadata_complete(chunk)
    reason = check_licensing(license_name, allowed_licenses)
    if reason is not None:
        return reason
    reason = check_access_class(chunk.access_class, allowed_access_classes)
    if reason is not None:
        return reason
    findings = detect_pii(chunk.chunk_text)
    if findings:
        types = sorted({finding.finding_type for finding in findings})
        return f"pii detected: {', '.join(types)}"
    return None
