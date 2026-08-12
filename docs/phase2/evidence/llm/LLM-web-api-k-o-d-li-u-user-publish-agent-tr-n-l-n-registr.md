# Evidence — Feature agent registry publication

- rubric_id: LLM-web-api-k-o-d-li-u-user-publish-agent-tr-n-l-n-registr
- execution_timestamp: 2026-08-10T05:07:00+00:00
- source_sha: 52dc00c17e69cdc46403f377ae83f00a5406fac5
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: registry.fd.dev/v1alpha1, agentregistry API 1.0.0
- command: `kubectl exec -n kagent deploy/agentregistry -- python -c "urllib.request.urlopen('http://127.0.0.1:8000/v1/agents')"`
- expected_result: registry exposes feature-agent with version, active status, replica ceiling, model config, sandbox policy and MCP tool
- actual_result: live registry returned feature-agent version `1.0.0`, status `active`, replicas `2..3`, `fd-global-model-config`, sandbox policy and `feature-mcp.lookup_feature_context`
- redaction_status: reviewed — private registry data contains no secret material
