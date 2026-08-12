# Evidence — Drift specialist agent

- rubric_id: LLM-web-api-cho-real-time-dri-1-agent-s-d-ng-mcp-tool-tr-n-v
- execution_timestamp: 2026-08-10T05:11:00+00:00
- source_sha: 3c99fb7fcdbae3e94840ebb1ed1b69b690da7785
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: drift-agent runtime 1.0.0, MCP 1.29.0, HPA min 2 max 3
- command: `kubectl exec sandbox-negative-probe -n agents-sandbox -- curl -fsS http://drift-agent.agents-sandbox.svc.cluster.local/readyz` and coordinator fan-out smoke
- expected_result: drift specialist reaches its scoped MCP tool and returns a cited report under sandbox autoscaling
- actual_result: drift readiness returned `{"status":"ready"}`; direct drift call and coordinator fan-out succeeded with `drift://scenario/market_stress`; endpoints showed 3 drift-agent replicas after HPA settled
- redaction_status: reviewed — synthetic market-stress rows only
