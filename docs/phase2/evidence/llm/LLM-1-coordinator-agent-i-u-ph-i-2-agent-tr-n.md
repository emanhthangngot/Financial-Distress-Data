# Evidence — Coordinator fan-out and hop bound

- rubric_id: LLM-1-coordinator-agent-i-u-ph-i-2-agent-tr-n
- execution_timestamp: 2026-08-10T05:15:00+00:00
- source_sha: 2f0d189fb3607bd0d509201869792246202f23b0
- gitops_sha: 6ba77a0464916ee86206b4e63090d5bd4742e048
- versions: coordinator runtime 1.0.0, MAX_AGENT_HOPS=2, Qwen2.5 0.5B Q4_K_M
- command: `kubectl exec sandbox-negative-probe -n agents-sandbox -- curl -fsS -X POST http://coordinator.agents-sandbox.svc.cluster.local/v1/run ...`
- expected_result: coordinator calls both specialists within the hop bound and returns citations
- actual_result: live response had `status=ok`, both feature and drift specialist objects, two citations, and `hops_used=1`; coordinator endpoint had 2 replicas after HPA settled
- redaction_status: reviewed — synthetic query and fixture citations only
