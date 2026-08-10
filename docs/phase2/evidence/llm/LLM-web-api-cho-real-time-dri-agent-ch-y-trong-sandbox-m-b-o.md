# Evidence — Drift agent sandbox

- rubric_id: LLM-web-api-cho-real-time-dri-agent-ch-y-trong-sandbox-m-b-o
- execution_timestamp: 2026-08-10T05:12:00+00:00
- source_sha: 2f0d189fb3607bd0d509201869792246202f23b0
- gitops_sha: 6ba77a0464916ee86206b4e63090d5bd4742e048
- versions: restricted Pod Security, tokenless ServiceAccount, default-deny Calico policies
- command: `kubectl get networkpolicy -n agents-sandbox` and the five negative commands executed from sandbox-negative-probe
- expected_result: drift agent has the same non-root, read-only, tokenless and narrowly scoped controls as feature agent
- actual_result: sandbox namespace and per-agent egress policies were enforced; five negatives were denied, while drift MCP/gateway readiness and positive drift path were allowed
- redaction_status: reviewed — no token values, credentials or private IPs recorded
