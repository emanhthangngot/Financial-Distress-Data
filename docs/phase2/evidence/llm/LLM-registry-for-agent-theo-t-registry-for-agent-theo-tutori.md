# Evidence — Queryable agent registry

- rubric_id: LLM-registry-for-agent-theo-t-registry-for-agent-theo-tutori
- execution_timestamp: 2026-08-10T05:14:00+00:00
- source_sha: 0bcaf1490b7ffe3561cbe409717b525488e452eb
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: FastAPI registry 1.0.0, ConfigMap registry.fd.dev/v1alpha1
- command: `kubectl exec -n kagent deploy/agentregistry -- python -c "urllib.request.urlopen('/readyz'); urllib.request.urlopen('/v1/agents')"`
- expected_result: deployed registry API is ready and returns all registered agents
- actual_result: `/readyz` returned `{"status":"ready","agents":3}`; `/v1/agents` returned feature-agent, drift-agent and coordinator with version/status/replicas/model/sandbox metadata
- redaction_status: reviewed — private GitOps repository, no credentials
