# Evidence — Drift MCP Helm deployment

- rubric_id: LLM-web-api-cho-real-time-dri-in-the-form-of-mcp-tool-to-k8s
- execution_timestamp: 2026-08-10T05:10:00+00:00
- source_sha: 6c13197663dd6e2a11981167a19bd3ca21ce44ea
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: Helm 3, drift-mcp chart 0.1.0, Artifact Registry immutable digest
- command: `helm upgrade --install drift-mcp charts/drift-mcp -n phase2-data -f apps/dev/drift-mcp/values.yaml --atomic --timeout 5m`
- expected_result: shared parameterized chart deploys drift MCP with rolling update and atomic behavior
- actual_result: release revision 3 deployed successfully; bad-image atomic rollback and healthy rolling update were verified for the MCP release family
- redaction_status: reviewed — no credentials in deployment output
