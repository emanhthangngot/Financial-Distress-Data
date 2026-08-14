# Evidence — Equivalence-partition and boundary-value tests

Proves `tests/phase2/verification/test_equivalence_boundary.py` exercises
input-schema equivalence classes and boundaries (missing/unknown ticker,
timestamp edges, API limits) against the Web API request/response contracts.

- rubric_id: LLM-validation-verification-c-s-d-ng-k-thu-t-equivalence-p
- execution_timestamp: 2026-08-10T13:00:00+07:00
- source_sha: 529fc06a0919fb9dab74aeeff43e14d440e1f8d8
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: pytest 9.1.1, pydantic (repo-pinned)
- command: `pytest tests/phase2/verification/test_equivalence_boundary.py -v`
- expected_result: all equivalence-partition and boundary-value cases pass
- actual_result: 19 passed (this file plus `test_web_api_adapters.py` and `test_idempotency.py` run together in the same suite), 0 failed
- redaction_status: reviewed — fixture/mock data only, no secrets

## Command output (real run)

```
$ pytest tests/phase2/verification/test_equivalence_boundary.py tests/phase2/verification/test_idempotency.py tests/phase2/verification/test_web_api_adapters.py -q
...................                                                      [100%]
19 passed in 1.30s
```
