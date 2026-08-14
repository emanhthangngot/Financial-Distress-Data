# Evidence — Drift FastAPI API validation

- rubric_id: LLM-web-api-cho-real-time-dri-c-s-d-ng-fastapi-data-validati
- execution_timestamp: 2026-08-10T05:08:00+00:00
- source_sha: 09640b7ede4848f47be9dd9a1cd11b4d041a7170
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: FastAPI 0.141.1, Pydantic 2.13.4, drift generator Phase 2
- command: `.venv-phase2/bin/python -m pytest tests/phase2/apps/test_drift_api_and_mcp.py -q` and live `/healthz`
- expected_result: drift API validates scenario/rows with Pydantic and serves a real drift report asynchronously
- actual_result: focused drift API/MCP tests passed; live drift health returned `{"status":"ok"}` and valid coordinator fan-out produced a cited `drift://scenario/market_stress` result
- redaction_status: reviewed — synthetic scenario only
