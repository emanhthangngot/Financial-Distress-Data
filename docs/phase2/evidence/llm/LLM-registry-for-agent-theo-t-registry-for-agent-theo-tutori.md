# Evidence — Queryable agent registry

- rubric_id: LLM-registry-for-agent-theo-t-registry-for-agent-theo-tutori
- execution_timestamp: 2026-08-10T05:14:00+00:00
- source_sha: f09d391bb7bd8f51561477b619ae4b1c5a88011c
- gitops_sha: 921bdc1075ef8335e0f509747bd64db2d525f73e
- versions: FastAPI registry 1.0.0, ConfigMap registry.fd.dev/v1alpha1
- command: `kubectl exec -n kagent deploy/agentregistry -- python -c "urllib.request.urlopen('/readyz'); urllib.request.urlopen('/v1/agents')"`
- expected_result: deployed registry API is ready and returns all registered agents
- actual_result: `/readyz` returned `{"status":"ready","agents":3}`; `/v1/agents` returned feature-agent, drift-agent and coordinator with version/status/replicas/model/sandbox metadata
- redaction_status: reviewed — private GitOps repository, no credentials
