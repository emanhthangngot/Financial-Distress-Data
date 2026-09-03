# Validation & Verification Evidence

## Coverage

| Component | Line coverage |
| --- | ---: |
| apps/drift-mcp | 100% |
| apps/feature-mcp | 95% |
| **Total** | **97%** |

## Required Proof

- Web API unit tests use FastAPI's `TestClient`, pytest fixtures, and mocked
  Feast/MCP boundaries
  ([test_web_api_adapters.py](../../../../../tests/platform/verification/test_web_api_adapters.py),
  [LLM-validation-verification-validation-verification.md](../LLM-validation-verification-validation-verification.md)).
- EP/BVA cases are visible in pytest IDs containing `valid-partition`,
  `max-inclusive-boundary`, `quarter-below-domain`
  ([test_equivalence_boundary.py](../../../../../tests/platform/verification/test_equivalence_boundary.py),
  [LLM-validation-verification-c-s-d-ng-k-thu-t-equivalence-p.md](../LLM-validation-verification-c-s-d-ng-k-thu-t-equivalence-p.md)).
- Property-based idempotency uses Hypothesis
  ([test_idempotency.py](../../../../../tests/platform/verification/test_idempotency.py),
  [LLM-validation-verification-idempotency-testing-s-d-ng-pro.md](../LLM-validation-verification-idempotency-testing-s-d-ng-pro.md)).
- Mutation score: 86.11%.
- Locust HTML SLA report: archived [`locust-report.html`](../locust-report.html).

## Screenshot Checklist

- [`screenshots/coverage-html-report.jpg`](screenshots/coverage-html-report.jpg): `coverage.py`'s own HTML report showing `>90%` line coverage.
- [`screenshots/locust-sla-report.jpg`](screenshots/locust-sla-report.jpg): opened `locust-report.html` SLA report.
- Mutation, idempotency, and EP/BVA have no screenshot — no browser/HTML report tool exists for them in this repo (`mutmut` has no HTML command; no `pytest-html` plugin installed). Their command output is quoted in the canonical evidence files linked above.

## Mutation Summary

# Mutation Testing
- Mutation score: 86.11%
- Gate: > 80.00%
- Killed: 62
- Survived: 9
- Timeout: 1
- Suspicious: 0
- No tests: 0
- Targets: src/llm/rag/chunking.py
- Mutant filters: none — full-module scope via `llm.rag.chunking.*`

## Locust Summary

# Locust Web API SLA
- Host: distresslens.duckdns.org (feature-mcp, POST /v1/features/by-id)
- Requests: 1352
- Failures: 0
- Failure rate: 0.00%
- Throughput: 15.06 req/s
- p95 latency: 140.00 ms
- SLA: failure rate 0%, p95 < 500 ms, throughput >= 10 req/s
- Result: PASS
