# Evidence — feature and drift MCP notebook

- rubric_id: LLM-demonstrate-basic-underst-jupyter-notebooks-to-demonstra
- execution_timestamp: 2026-08-11T08:52:37Z
- source_sha: f59a5ef32c976eef88cb396f56f105305da4228f
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: Python 3.11; mcp streamable-http client; feature-mcp and drift-mcp images deployed from the recorded GitOps revision
- command: Port-forward `feature-mcp` and `drift-mcp` and run the code cells in `notebooks/agent-mcp-demo.ipynb` with feature scope `financial-distress:read` and drift scope `financial-distress:drift`
- expected_result: one bounded agent invocation calls both governed MCP tools and returns feature/RAG context plus a deterministic drift report
- actual_result: both tool calls returned `ok=true`; the drift report changed `debt_to_asset` from mean `0.5` to `1.075`, relative change `1.15`, observed/configured direction `increase`, PSI `27.63099348490743`, `passed=true`, and affected ticker `VNM`; the feature/RAG result returned the same audited `phase3-chunk` context
- redaction_status: reviewed — no credentials, project identifiers, node addresses, prompts, or personal data were recorded

## Reproducible output

The notebook uses separate scopes for the feature and drift agents, calls both
MCP endpoints concurrently, and commits the returned JSON output.
