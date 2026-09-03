"""Behavioral proof for the Phase 06 LLM novel ideas."""

from __future__ import annotations

import pytest

from src.llm.citation_guard import CitationGuard
from src.llm.embedding_registry import EmbeddingVersionRegistry


def digest(char: str = "a") -> str:
    return f"sha256:{char * 64}"


def test_embedding_registry_dual_reads_before_atomic_alias_swap() -> None:
    registry = EmbeddingVersionRegistry()
    old = registry.register_version("e5-small", 3, digest())
    new = registry.register_version("e5-small", 3, digest("b"))
    reads: list[str] = []

    def read(version: str) -> list[dict[str, list[float]]]:
        reads.append(version)
        return [{"vector": [0.1, 0.2, 0.3]}]

    result = registry.hot_swap(new, dual_read=read)

    assert reads == [old, new]
    assert result["dual_read"]["previous_count"] == 1
    assert result["dual_read"]["candidate_count"] == 1
    assert registry.resolve_active() == new


def test_embedding_registry_rejects_mixed_dimensions_before_swap() -> None:
    registry = EmbeddingVersionRegistry()
    registry.register_version("e5-small", 3, digest())
    new = registry.register_version("large", 4, digest("b"))

    with pytest.raises(ValueError, match="dimensions"):
        registry.hot_swap(new)


def test_embedding_registry_rejects_wrong_query_vector_shape() -> None:
    registry = EmbeddingVersionRegistry()
    version = registry.register_version("e5-small", 3, digest())

    with pytest.raises(ValueError, match="dimensions"):
        registry.validate_query(version, [0.1, 0.2])


def test_citation_guard_rewrites_pii_and_keeps_trace_manifest_link() -> None:
    guard = CitationGuard(lambda citation: citation == "feature://user/u-1")

    decision = guard.evaluate(
        "Risk contact is analyst@example.com; cite the feature result.",
        ["feature://user/u-1"],
        trace_id="trace-123",
        evidence_manifest="evidence/manifest.json",
    )

    assert decision.allowed is True
    assert decision.action == "rewritten"
    assert "analyst@example.com" not in decision.output
    assert decision.pii_findings == ("email",)
    assert decision.trace_id == "trace-123"
    assert decision.evidence_manifest == "evidence/manifest.json"


def test_citation_guard_blocks_unsupported_claims() -> None:
    guard = CitationGuard(lambda _citation: False)

    decision = guard.evaluate(
        "An unsupported answer.",
        ["unknown://source"],
        trace_id="trace-456",
        evidence_manifest="evidence/manifest.json",
    )

    assert decision.allowed is False
    assert decision.action == "blocked"
    assert decision.reason == "missing_or_unsupported_citation"


def test_citation_guard_defaults_to_fail_closed() -> None:
    decision = CitationGuard().evaluate(
        "An answer with an unverified citation.",
        ["https://example.test/source"],
        trace_id="trace-default",
        evidence_manifest="evidence/manifest.json",
    )

    assert decision.allowed is False
    assert decision.reason == "missing_or_unsupported_citation"


def test_citation_guard_blocks_resolver_errors() -> None:
    def unavailable(_citation: str) -> bool:
        raise RuntimeError("resolver unavailable")

    decision = CitationGuard(unavailable).evaluate(
        "An answer whose source lookup failed.",
        ["feature://user/u-1"],
        trace_id="trace-resolver-error",
        evidence_manifest="evidence/manifest.json",
    )

    assert decision.allowed is False
    assert decision.reason == "citation_resolver_error"


def test_citation_guard_can_fail_closed_on_pii() -> None:
    guard = CitationGuard(lambda _citation: True)

    decision = guard.evaluate(
        "Sensitive number 0123456789.",
        ["https://example.test/source"],
        trace_id="trace-789",
        evidence_manifest="evidence/manifest.json",
        rewrite_sensitive=False,
    )

    assert decision.allowed is False
    assert decision.reason == "pii_detected"
