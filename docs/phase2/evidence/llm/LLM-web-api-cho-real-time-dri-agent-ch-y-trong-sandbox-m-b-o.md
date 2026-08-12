# Evidence — Drift agent sandbox

- rubric_id: LLM-web-api-cho-real-time-dri-agent-ch-y-trong-sandbox-m-b-o
- execution_timestamp: 2026-08-10T05:12:00+00:00
- source_sha: 29f6a7ce00a2a6ff2ac42604983e814b1eeffe06
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: restricted Pod Security, tokenless ServiceAccount, default-deny Calico policies
- command: `kubectl get networkpolicy -n agents-sandbox` and the five negative commands executed from sandbox-negative-probe
- expected_result: drift agent has the same non-root, read-only, tokenless and narrowly scoped controls as feature agent
- actual_result: sandbox namespace and per-agent egress policies were enforced; five negatives were denied, while drift MCP/gateway readiness and positive drift path were allowed
- redaction_status: reviewed — no token values, credentials or private IPs recorded
