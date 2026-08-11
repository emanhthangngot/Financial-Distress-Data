# Evidence — Drift agent registry publication

- rubric_id: LLM-web-api-cho-real-time-dri-publish-agent-tr-n-l-n-registr
- execution_timestamp: 2026-08-10T05:13:00+00:00
- source_sha: 758722c52ef3035a7e3f9464dc03c5a39e50a74e
- gitops_sha: 921bdc1075ef8335e0f509747bd64db2d525f73e
- versions: agentregistry API 1.0.0, registry.fd.dev/v1alpha1
- command: `kubectl exec -n kagent deploy/agentregistry -- python -c "urllib.request.urlopen('http://127.0.0.1:8000/v1/agents/drift-agent')"`
- expected_result: registry exposes drift-agent governance and tool metadata
- actual_result: returned drift-agent version `1.0.0`, active status, replicas `2..3`, global model config, sandbox policy and `drift-mcp.build_realtime_drift_report`
- redaction_status: reviewed — no secret material
