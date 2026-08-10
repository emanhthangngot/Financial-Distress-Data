# Evidence — Drift async API

- rubric_id: LLM-web-api-cho-real-time-dri-s-d-ng-async
- execution_timestamp: 2026-08-10T05:09:00+00:00
- source_sha: 2f0d189fb3607bd0d509201869792246202f23b0
- gitops_sha: 6ba77a0464916ee86206b4e63090d5bd4742e048
- versions: FastAPI 0.141.1, httpx 0.28.1, Uvicorn 0.34.0
- command: `.venv-phase2/bin/python -m pytest tests/phase2/apps/test_drift_api_and_mcp.py -q`
- expected_result: async drift endpoint offloads pure domain calculation and preserves idempotent result
- actual_result: focused drift API/MCP tests passed, including async offload and repeated identical response; live readiness returned green
- redaction_status: reviewed — no secrets or personal data
