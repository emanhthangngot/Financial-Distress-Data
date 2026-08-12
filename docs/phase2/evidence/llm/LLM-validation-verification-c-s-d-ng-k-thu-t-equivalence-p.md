# Evidence — Equivalence-partition and boundary-value tests

Proves `tests/phase2/verification/test_equivalence_boundary.py` exercises
input-schema equivalence classes and boundaries (missing/unknown ticker,
timestamp edges, API limits) against the Web API request/response contracts.

- rubric_id: LLM-validation-verification-c-s-d-ng-k-thu-t-equivalence-p
- execution_timestamp: 2026-08-10T13:00:00+07:00
- source_sha: 1b38709b4ef1b28e7a1bb7f12a49b68cbfe1c049
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
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
