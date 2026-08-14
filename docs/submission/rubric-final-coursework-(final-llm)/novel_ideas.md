---
title: "Novel Ideas"
date: 2026-08-14
status: active
---

# Novel Ideas: hot-swappable embedding versions and a fail-closed citation/PII guard

This doc proves the two rows in "Novel ideas": (1) an embedding-version
registry that validates dual-read compatibility before hot-swapping the
active alias, and (2) a citation guard that blocks unsupported claims and
redacts PII, failing closed on resolver errors rather than open. Neither
claims to be a novel research contribution — both are real engineering
techniques applied to this platform's specific correctness/safety needs, per
the rubric's own framing ("không nhất thiết tự sáng tạo ra cái gì").

**Active deployment facts:** Python 3.11, `src/llm/embedding_registry.py`
(`EmbeddingVersionRegistry`), `src/llm/citation_guard.py` (`CitationGuard`).

## Part I — Idea 1: embedding-version hot swap

### 1. Dual-read validation before promoting a candidate version

```text
$ pytest tests/phase2/verification/test_llm_novel_ideas.py -k embedding_registry -q
-> registry tests passed: injected reader called for both previous and
   candidate versions, one match recorded from each, candidate became
   active only after validation; incompatible dimensions and wrong vector
   length were rejected before query or alias use
```

`EmbeddingVersionRegistry.validate_dual_read` reads both the previous and
candidate embedding namespaces, `compatibility_check` rejects mismatched
dimensions, and `hot_swap` changes the active alias only after validation
passes — this is the mechanism `rag.md`'s embed step relies on for a
production embedding-model upgrade without downtime. Full evidence:
[`LLM-novel-ideas-idea-1.md`](../../phase2/evidence/llm/LLM-novel-ideas-idea-1.md).

## Part II — Idea 2: citation and PII guard, fail-closed

### 2. Unsupported citations block; PII redacts; resolver errors fail closed

```python
# src/llm/citation_guard.py:47-86
class CitationGuard:
    """Validate citations and redact PII without exposing matched values."""

    def __init__(self, citation_exists: Callable[[str], bool] | None = None) -> None:
        # A policy boundary must not treat a syntactically plausible URL as
        # proof that a source exists. Production callers inject a resolver
        # backed by the evidence manifest; local/default callers fail closed.
        self._citation_exists = citation_exists or (lambda _citation: False)

    def evaluate(self, output, citations, *, trace_id, evidence_manifest, rewrite_sensitive=True):
        try:
            missing = tuple(c for c in normalized if not self._citation_exists(c))
        except Exception:
            return CitationDecision(allowed=False, action="blocked",
                output="The response was blocked because its citations could not be verified.",
                reason="citation_resolver_error", ...)
```

```text
$ pytest tests/phase2/verification/test_llm_novel_ideas.py -k citation_guard -q
-> guard tests passed: email output rewritten with category-only findings,
   unsupported/default citations blocked, resolver exceptions blocked,
   fail-closed PII mode blocked sensitive output while preserving
   trace_id and evidence_manifest
```

The default constructor (`citation_exists=None`) resolves every citation as
non-existent — a caller must explicitly inject a real resolver backed by the
evidence manifest, or nothing is ever allowed through. This is the same
guard `coordinator_agent.md`'s `citations_are_valid` check relies on before
a coordinator response is returned. Full evidence:
[`LLM-novel-ideas-idea-2.md`](../../phase2/evidence/llm/LLM-novel-ideas-idea-2.md).

## Limitations

Both mechanisms are proven at the unit-test level with injected
readers/resolvers, not against a live production embedding-store swap or a
real adversarial PII-leak attempt — the fail-closed defaults are the safety
property being proven, not a claim of exhaustive red-team coverage.

## References

- None external — both mechanisms are original to this codebase, built on
  standard dual-read/blue-green patterns.
</content>
