# Evidence — Drift specialist agent

- rubric_id: LLM-web-api-cho-real-time-dri-1-agent-s-d-ng-mcp-tool-tr-n-v
- execution_timestamp: 2026-08-10T05:11:00+00:00
- source_sha: f09d391bb7bd8f51561477b619ae4b1c5a88011c
- gitops_sha: 921bdc1075ef8335e0f509747bd64db2d525f73e
- versions: drift-agent runtime 1.0.0, MCP 1.29.0, HPA min 2 max 3
- command: `kubectl exec sandbox-negative-probe -n agents-sandbox -- curl -fsS http://drift-agent.agents-sandbox.svc.cluster.local/readyz` and coordinator fan-out smoke
- expected_result: drift specialist reaches its scoped MCP tool and returns a cited report under sandbox autoscaling
- actual_result: drift readiness returned `{"status":"ready"}`; direct drift call and coordinator fan-out succeeded with `drift://scenario/market_stress`; endpoints showed 3 drift-agent replicas after HPA settled
- redaction_status: reviewed — synthetic market-stress rows only
