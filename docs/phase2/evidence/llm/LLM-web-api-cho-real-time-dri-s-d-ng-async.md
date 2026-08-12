# Evidence — Drift async API

- rubric_id: LLM-web-api-cho-real-time-dri-s-d-ng-async
- execution_timestamp: 2026-08-10T05:09:00+00:00
- source_sha: 52dc00c17e69cdc46403f377ae83f00a5406fac5
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: FastAPI 0.141.1, httpx 0.28.1, Uvicorn 0.34.0
- command: `.venv-phase2/bin/python -m pytest tests/phase2/apps/test_drift_api_and_mcp.py -q`
- expected_result: async drift endpoint offloads pure domain calculation and preserves idempotent result
- actual_result: focused drift API/MCP tests passed, including async offload and repeated identical response; live readiness returned green
- redaction_status: reviewed — no secrets or personal data
