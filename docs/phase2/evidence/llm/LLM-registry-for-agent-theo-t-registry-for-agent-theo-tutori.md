# Evidence — Queryable agent registry

- rubric_id: LLM-registry-for-agent-theo-t-registry-for-agent-theo-tutori
- execution_timestamp: 2026-08-10T05:14:00+00:00
- source_sha: 2f0d189fb3607bd0d509201869792246202f23b0
- gitops_sha: 6ba77a0464916ee86206b4e63090d5bd4742e048
- versions: FastAPI registry 1.0.0, ConfigMap registry.fd.dev/v1alpha1
- command: `kubectl exec -n kagent deploy/agentregistry -- python -c "urllib.request.urlopen('/readyz'); urllib.request.urlopen('/v1/agents')"`
- expected_result: deployed registry API is ready and returns all registered agents
- actual_result: `/readyz` returned `{"status":"ready","agents":3}`; `/v1/agents` returned feature-agent, drift-agent and coordinator with version/status/replicas/model/sandbox metadata
- redaction_status: reviewed — private GitOps repository, no credentials
