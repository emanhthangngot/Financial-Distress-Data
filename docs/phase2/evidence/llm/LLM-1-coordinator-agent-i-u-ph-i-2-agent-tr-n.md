# Evidence — Coordinator fan-out and hop bound

- rubric_id: LLM-1-coordinator-agent-i-u-ph-i-2-agent-tr-n
- execution_timestamp: 2026-08-10T05:15:00+00:00
- source_sha: 758722c52ef3035a7e3f9464dc03c5a39e50a74e
- gitops_sha: 921bdc1075ef8335e0f509747bd64db2d525f73e
- versions: coordinator runtime 1.0.0, MAX_AGENT_HOPS=2, Qwen2.5 0.5B Q4_K_M
- command: `kubectl exec sandbox-negative-probe -n agents-sandbox -- curl -fsS -X POST http://coordinator.agents-sandbox.svc.cluster.local/v1/run ...`
- expected_result: coordinator calls both specialists within the hop bound and returns citations
- actual_result: live response had `status=ok`, both feature and drift specialist objects, two citations, and `hops_used=1`; coordinator endpoint had 2 replicas after HPA settled
- redaction_status: reviewed — synthetic query and fixture citations only
