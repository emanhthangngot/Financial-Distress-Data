# Evidence — Drift async API

- rubric_id: LLM-web-api-cho-real-time-dri-s-d-ng-async
- execution_timestamp: 2026-08-10T05:09:00+00:00
- source_sha: 6dc70ba62f2a664aaeba484a34c23604246e0017
- gitops_sha: 921bdc1075ef8335e0f509747bd64db2d525f73e
- versions: FastAPI 0.141.1, httpx 0.28.1, Uvicorn 0.34.0
- command: `.venv-phase2/bin/python -m pytest tests/phase2/apps/test_drift_api_and_mcp.py -q`
- expected_result: async drift endpoint offloads pure domain calculation and preserves idempotent result
- actual_result: focused drift API/MCP tests passed, including async offload and repeated identical response; live readiness returned green
- redaction_status: reviewed — no secrets or personal data
