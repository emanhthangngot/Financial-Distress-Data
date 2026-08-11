# Evidence — Drift agent sandbox

- rubric_id: LLM-web-api-cho-real-time-dri-agent-ch-y-trong-sandbox-m-b-o
- execution_timestamp: 2026-08-10T05:12:00+00:00
- source_sha: f09d391bb7bd8f51561477b619ae4b1c5a88011c
- gitops_sha: 921bdc1075ef8335e0f509747bd64db2d525f73e
- versions: restricted Pod Security, tokenless ServiceAccount, default-deny Calico policies
- command: `kubectl get networkpolicy -n agents-sandbox` and the five negative commands executed from sandbox-negative-probe
- expected_result: drift agent has the same non-root, read-only, tokenless and narrowly scoped controls as feature agent
- actual_result: sandbox namespace and per-agent egress policies were enforced; five negatives were denied, while drift MCP/gateway readiness and positive drift path were allowed
- redaction_status: reviewed — no token values, credentials or private IPs recorded
