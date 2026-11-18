# Evidence — Validation & Verification (base row)

Proves fixture/mock-based Web API tests achieve the declared >90%
coverage gate, with visible fixture and mock usage.

- rubric_id: LLM-validation-verification-validation-verification
- execution_timestamp: 2026-08-10T13:00:00+07:00
- source_sha: 9ec6f065276d316bad1e308c88028c5662edc4db
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: coverage 7.15.4, pytest 9.1.1, unittest.mock (stdlib)
- command: `python scripts/run_phase5_web_gate.py`
- expected_result: coverage above 90% lines/branches on the the platform LLM Web API code, with fixture and mock usage visible in the test source
- actual_result: **96.17% lines** (352/366) and **93.48% branches** (43/46), above the 90% gate; `tests/platform/verification/test_web_api_adapters.py` uses `unittest.mock.patch`/`MagicMock` fixtures for the Feast/MCP boundaries
- redaction_status: reviewed — fixture/mock data only, no secrets

## Command output (real run)

```
$ python scripts/run_phase5_web_gate.py
Lines: 352/366 = 96.17%
Branches: 43/46 = 93.48%
Gate (>=90% lines and branches): PASS
```
