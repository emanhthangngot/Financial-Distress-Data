# Evidence — Feature agent registry publication

- rubric_id: LLM-web-api-k-o-d-li-u-user-publish-agent-tr-n-l-n-registr
- execution_timestamp: 2026-08-10T05:07:00+00:00
- source_sha: f59a5ef32c976eef88cb396f56f105305da4228f
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: registry.fd.dev/v1alpha1, agentregistry API 1.0.0
- command: `kubectl exec -n kagent deploy/agentregistry -- python -c "urllib.request.urlopen('http://127.0.0.1:8000/v1/agents')"`
- expected_result: registry exposes feature-agent with version, active status, replica ceiling, model config, sandbox policy and MCP tool
- actual_result: live registry returned feature-agent version `1.0.0`, status `active`, replicas `2..3`, `fd-global-model-config`, sandbox policy and `feature-mcp.lookup_feature_context`
- redaction_status: reviewed — private registry data contains no secret material
