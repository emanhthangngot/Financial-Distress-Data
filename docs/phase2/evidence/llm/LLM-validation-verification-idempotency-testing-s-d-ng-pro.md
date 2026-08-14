# Evidence — Idempotency testing (Hypothesis)

Proves `tests/phase2/verification/test_idempotency.py` uses Hypothesis
property-based testing to confirm repeated retrieval and repeated tool
invocation are idempotent (same input yields the same result on retry).

- rubric_id: LLM-validation-verification-idempotency-testing-s-d-ng-pro
- execution_timestamp: 2026-08-10T13:00:00+07:00
- source_sha: 8adb668c68941be821cae879fac15db60853d96e
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: hypothesis 6.165.2, pytest 9.1.1
- command: `pytest tests/phase2/verification/test_idempotency.py -v`
- expected_result: Hypothesis-generated cases all pass, proving idempotent retrieval/tool-call behavior
- actual_result: 2 passed, 0 failed, 0 flaky examples (each test runs many Hypothesis-generated examples internally)
- redaction_status: reviewed — fixture/mock data only, no secrets

## Command output (real run)

```
$ pytest tests/phase2/verification/test_idempotency.py -q
..                                                                        [100%]
2 passed in 0.21s
```
