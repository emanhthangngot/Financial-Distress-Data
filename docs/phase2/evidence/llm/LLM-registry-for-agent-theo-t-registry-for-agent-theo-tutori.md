# Evidence — Queryable agent registry

- rubric_id: LLM-registry-for-agent-theo-t-registry-for-agent-theo-tutori
- execution_timestamp: 2026-08-10T05:14:00+00:00
- source_sha: 84c612de87d289de768c5a67439817c6df520b9a
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: FastAPI registry 1.0.0, ConfigMap registry.fd.dev/v1alpha1
- command: `kubectl exec -n kagent deploy/agentregistry -- python -c "urllib.request.urlopen('/readyz'); urllib.request.urlopen('/v1/agents')"`
- expected_result: deployed registry API is ready and returns all registered agents
- actual_result: `/readyz` returned `{"status":"ready","agents":3}`; `/v1/agents` returned feature-agent, drift-agent and coordinator with version/status/replicas/model/sandbox metadata
- redaction_status: reviewed — private GitOps repository, no credentials
