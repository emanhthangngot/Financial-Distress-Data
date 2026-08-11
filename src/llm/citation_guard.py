"""Citation and PII guard for trace-linked model decisions.

The guard is a policy boundary after tool retrieval and before a response is
shown to a user.  Unsupported claims fail closed; sensitive values are
rewritten while preserving a structured decision record that can be joined to
an OpenTelemetry trace and the evidence manifest.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\s.\-]?){8,15}(?!\d)")
_NATIONAL_ID_RE = re.compile(r"(?<!\d)\d{9,12}(?!\d)")


@dataclass(frozen=True)
class CitationDecision:
    """Auditable result of one response policy decision."""

    allowed: bool
    action: str
    output: str
    trace_id: str
    evidence_manifest: str
    citations: tuple[str, ...]
    pii_findings: tuple[str, ...]
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "action": self.action,
            "output": self.output,
            "trace_id": self.trace_id,
            "evidence_manifest": self.evidence_manifest,
            "citations": list(self.citations),
            "pii_findings": list(self.pii_findings),
            "reason": self.reason,
        }


class CitationGuard:
    """Validate citations and redact PII without exposing matched values."""

    def __init__(self, citation_exists: Callable[[str], bool] | None = None) -> None:
        # A policy boundary must not treat a syntactically plausible URL as
        # proof that a source exists. Production callers inject a resolver
        # backed by the evidence manifest; local/default callers fail closed.
        self._citation_exists = citation_exists or (lambda _citation: False)

    def evaluate(
        self,
        output: str,
        citations: Iterable[str],
        *,
        trace_id: str,
        evidence_manifest: str,
        rewrite_sensitive: bool = True,
    ) -> CitationDecision:
        """Return a blocked or rewritten response with trace-linked metadata."""

        if not trace_id.strip():
            raise ValueError("trace_id must not be empty")
        if not evidence_manifest.strip():
            raise ValueError("evidence_manifest must not be empty")
        normalized = tuple(str(citation).strip() for citation in citations if str(citation).strip())
        try:
            missing = tuple(
                citation for citation in normalized if not self._citation_exists(citation)
            )
        except Exception:
            return CitationDecision(
                allowed=False,
                action="blocked",
                output="The response was blocked because its citations could not be verified.",
                trace_id=trace_id,
                evidence_manifest=evidence_manifest,
                citations=normalized,
                pii_findings=(),
                reason="citation_resolver_error",
            )
        if not normalized or missing:
            return CitationDecision(
                allowed=False,
                action="blocked",
                output="The response was blocked because its claims lack supported citations.",
                trace_id=trace_id,
                evidence_manifest=evidence_manifest,
                citations=normalized,
                pii_findings=(),
                reason="missing_or_unsupported_citation",
            )

        findings = self.find_pii(output)
        if findings and not rewrite_sensitive:
            return CitationDecision(
                allowed=False,
                action="blocked",
                output="The response was blocked because it contains sensitive data.",
                trace_id=trace_id,
                evidence_manifest=evidence_manifest,
                citations=normalized,
                pii_findings=findings,
                reason="pii_detected",
            )

        safe_output = self.redact(output) if findings else output
        return CitationDecision(
            allowed=True,
            action="rewritten" if findings else "allowed",
            output=safe_output,
            trace_id=trace_id,
            evidence_manifest=evidence_manifest,
            citations=normalized,
            pii_findings=findings,
            reason="pii_redacted" if findings else "citations_verified",
        )

    @staticmethod
    def find_pii(output: str) -> tuple[str, ...]:
        """Return stable PII category names, never the matched values."""

        findings: list[str] = []
        if _EMAIL_RE.search(output):
            findings.append("email")
        if _PHONE_RE.search(output):
            findings.append("phone")
        if _NATIONAL_ID_RE.search(output):
            findings.append("national_id")
        return tuple(findings)

    @staticmethod
    def redact(output: str) -> str:
        """Replace sensitive values while retaining the surrounding answer."""

        safe = _EMAIL_RE.sub("[redacted:email]", output)
        safe = _PHONE_RE.sub("[redacted:phone]", safe)
        return _NATIONAL_ID_RE.sub("[redacted:national_id]", safe)


def guard_response(
    output: str,
    citations: Iterable[str],
    *,
    trace_id: str,
    evidence_manifest: str,
    citation_exists: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    """Convenience wrapper returning a JSON-serializable citation decision."""

    return (
        CitationGuard(citation_exists)
        .evaluate(
            output,
            citations,
            trace_id=trace_id,
            evidence_manifest=evidence_manifest,
        )
        .as_dict()
    )
