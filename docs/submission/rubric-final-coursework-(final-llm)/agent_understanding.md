---
title: "Agent Understanding"
date: 2026-08-14
status: active
---

# Agent Understanding: two notebooks demonstrating governed MCP tool calls

This doc proves the two rows in "Demonstrate basic understanding of Agents":
committed, reproducible Jupyter notebooks showing an agent call a governed
MCP tool (never Redis/PostgreSQL directly) and a second notebook showing one
agent bound to two MCP tools concurrently. It does not claim novel agent
architecture — this is the basic-understanding deliverable, distinct from
`coordinator_agent.md`'s orchestration proof.

**Active deployment facts:** `feature-mcp` and `drift-mcp`, port-forwarded
for notebook execution; Python 3.11, `mcp` streamable-http client.

## Part I — Single-tool notebook

### 1. `notebooks/agent-understanding-demo.ipynb`

```text
Port-forward feature-mcp; run with
  DEMO_USER_ID=VNM, DEMO_CHUNK_ID=phase3-chunk, DEMO_SCOPE=financial-distress:read

-> ok=true
   feature payload: z_score=null (no online value materialized for VNM —
     kept as the real service result, not replaced with fixture data)
   RAG payload: chunk_id=phase3-chunk, company=VNM, report_date=2026-08-10,
     access_class=public
```

The agent never connects to Redis or PostgreSQL directly — every value comes
through the governed MCP tool call. Full evidence:
[`LLM-demonstrate-basic-underst-jupyter-notebook-demonstrate-a.md`](../../platform/evidence/llm/LLM-demonstrate-basic-underst-jupyter-notebook-demonstrate-a.md).

## Part II — Two-tool notebook

### 2. `notebooks/agent-mcp-demo.ipynb`

```text
Port-forward feature-mcp and drift-mcp; feature scope
  financial-distress:read, drift scope financial-distress:drift

-> both tool calls ok=true
   drift report: debt_to_asset mean 0.5 -> 1.075 (relative change 1.15),
     direction=increase, PSI=27.63099348490743, passed=true, ticker=VNM
   feature/RAG result: same audited phase3-chunk context as Part I
```

One bounded agent invocation calls both governed tools concurrently with
distinct scopes per tool. Full evidence:
[`LLM-demonstrate-basic-underst-jupyter-notebooks-to-demonstra.md`](../../platform/evidence/llm/LLM-demonstrate-basic-underst-jupyter-notebooks-to-demonstra.md).

## Limitations

`z_score=null` in Part I is the genuine service result — no online value was
materialized for VNM in the feature store at capture time. It is kept
honestly rather than swapped for a fixture value that would look better.

## References

- MCP (Model Context Protocol): https://modelcontextprotocol.io/
