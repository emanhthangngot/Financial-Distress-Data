# Evidence — Coordinator registry publication

- rubric_id: LLM-1-coordinator-agent-publish-agent-n-y-l-n-registry
- execution_timestamp: 2026-08-10T05:16:00+00:00
- source_sha: 2f0d189fb3607bd0d509201869792246202f23b0
- gitops_sha: 6ba77a0464916ee86206b4e63090d5bd4742e048
- versions: agentregistry API 1.0.0, registry.fd.dev/v1alpha1
- command: `kubectl exec -n kagent deploy/agentregistry -- python -c "urllib.request.urlopen('http://127.0.0.1:8000/v1/agents/coordinator')"`
- expected_result: coordinator is registered with its two specialists and bounded hop policy
- actual_result: registry returned coordinator version `1.0.0`, active, replicas `2..3`, `fd-global-model-config`, sandbox policy, specialists `[feature-agent, drift-agent]` and `maxHops=2`
- redaction_status: reviewed — no secrets or personal data
