# Evidence — Validation & Verification (base row)

Proves fixture/mock-based Web API tests achieve the declared >90%
coverage gate, with visible fixture and mock usage.

- rubric_id: LLM-validation-verification-validation-verification
- execution_timestamp: 2026-08-10T13:00:00+07:00
- source_sha: 84c612de87d289de768c5a67439817c6df520b9a
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: coverage 7.15.4, pytest 9.1.1, unittest.mock (stdlib)
- command: `python scripts/run_phase5_web_gate.py`
- expected_result: coverage above 90% lines/branches on the Phase 2 LLM Web API code, with fixture and mock usage visible in the test source
- actual_result: **96.17% lines** (352/366) and **93.48% branches** (43/46), above the 90% gate; `tests/phase2/verification/test_web_api_adapters.py` uses `unittest.mock.patch`/`MagicMock` fixtures for the Feast/MCP boundaries
- redaction_status: reviewed — fixture/mock data only, no secrets

## Command output (real run)

```
$ python scripts/run_phase5_web_gate.py
Lines: 352/366 = 96.17%
Branches: 43/46 = 93.48%
Gate (>=90% lines and branches): PASS
```
