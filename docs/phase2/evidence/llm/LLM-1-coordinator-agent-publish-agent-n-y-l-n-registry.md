# Evidence — Coordinator registry publication

- rubric_id: LLM-1-coordinator-agent-publish-agent-n-y-l-n-registry
- execution_timestamp: 2026-08-10T05:16:00+00:00
- source_sha: f59a5ef32c976eef88cb396f56f105305da4228f
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: agentregistry API 1.0.0, registry.fd.dev/v1alpha1
- command: `kubectl exec -n kagent deploy/agentregistry -- python -c "urllib.request.urlopen('http://127.0.0.1:8000/v1/agents/coordinator')"`
- expected_result: coordinator is registered with its two specialists and bounded hop policy
- actual_result: registry returned coordinator version `1.0.0`, active, replicas `2..3`, `fd-global-model-config`, sandbox policy, specialists `[feature-agent, drift-agent]` and `maxHops=2`
- redaction_status: reviewed — no secrets or personal data
