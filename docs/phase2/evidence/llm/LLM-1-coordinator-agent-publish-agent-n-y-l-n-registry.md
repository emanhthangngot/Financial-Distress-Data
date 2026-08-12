# Evidence — Coordinator registry publication

- rubric_id: LLM-1-coordinator-agent-publish-agent-n-y-l-n-registry
- execution_timestamp: 2026-08-10T05:16:00+00:00
- source_sha: 52dc00c17e69cdc46403f377ae83f00a5406fac5
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: agentregistry API 1.0.0, registry.fd.dev/v1alpha1
- command: `kubectl exec -n kagent deploy/agentregistry -- python -c "urllib.request.urlopen('http://127.0.0.1:8000/v1/agents/coordinator')"`
- expected_result: coordinator is registered with its two specialists and bounded hop policy
- actual_result: registry returned coordinator version `1.0.0`, active, replicas `2..3`, `fd-global-model-config`, sandbox policy, specialists `[feature-agent, drift-agent]` and `maxHops=2`
- redaction_status: reviewed — no secrets or personal data
