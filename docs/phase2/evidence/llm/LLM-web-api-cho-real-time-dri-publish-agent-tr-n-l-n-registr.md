# Evidence — Drift agent registry publication

- rubric_id: LLM-web-api-cho-real-time-dri-publish-agent-tr-n-l-n-registr
- execution_timestamp: 2026-08-10T05:13:00+00:00
- source_sha: 6ee3175073333df7ed3ed6737bc6c2ac65e6a0a8
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: agentregistry API 1.0.0, registry.fd.dev/v1alpha1
- command: `kubectl exec -n kagent deploy/agentregistry -- python -c "urllib.request.urlopen('http://127.0.0.1:8000/v1/agents/drift-agent')"`
- expected_result: registry exposes drift-agent governance and tool metadata
- actual_result: returned drift-agent version `1.0.0`, active status, replicas `2..3`, global model config, sandbox policy and `drift-mcp.build_realtime_drift_report`
- redaction_status: reviewed — no secret material
