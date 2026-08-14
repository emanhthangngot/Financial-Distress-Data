# Evidence — Drift agent registry publication

- rubric_id: LLM-web-api-cho-real-time-dri-publish-agent-tr-n-l-n-registr
- execution_timestamp: 2026-08-10T05:13:00+00:00
- source_sha: 0bcaf1490b7ffe3561cbe409717b525488e452eb
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: agentregistry API 1.0.0, registry.fd.dev/v1alpha1
- command: `kubectl exec -n kagent deploy/agentregistry -- python -c "urllib.request.urlopen('http://127.0.0.1:8000/v1/agents/drift-agent')"`
- expected_result: registry exposes drift-agent governance and tool metadata
- actual_result: returned drift-agent version `1.0.0`, active status, replicas `2..3`, global model config, sandbox policy and `drift-mcp.build_realtime_drift_report`
- redaction_status: reviewed — no secret material
