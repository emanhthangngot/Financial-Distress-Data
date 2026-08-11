# Evidence — Feature agent registry publication

- rubric_id: LLM-web-api-k-o-d-li-u-user-publish-agent-tr-n-l-n-registr
- execution_timestamp: 2026-08-10T05:07:00+00:00
- source_sha: 758722c52ef3035a7e3f9464dc03c5a39e50a74e
- gitops_sha: 921bdc1075ef8335e0f509747bd64db2d525f73e
- versions: registry.fd.dev/v1alpha1, agentregistry API 1.0.0
- command: `kubectl exec -n kagent deploy/agentregistry -- python -c "urllib.request.urlopen('http://127.0.0.1:8000/v1/agents')"`
- expected_result: registry exposes feature-agent with version, active status, replica ceiling, model config, sandbox policy and MCP tool
- actual_result: live registry returned feature-agent version `1.0.0`, status `active`, replicas `2..3`, `fd-global-model-config`, sandbox policy and `feature-mcp.lookup_feature_context`
- redaction_status: reviewed — private registry data contains no secret material
