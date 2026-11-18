---
title: Close LLM observability evidence
date: 2026-08-12
tags: [phase2, llm, observability, evidence, gke]
---

# Close LLM observability evidence

## Context

The LLM track had two remaining design-only rows worth four points: per-agent
and per-MCP-tool call metrics, and per-request token/latency/PII metrics.

## What happened

- Replaced drift MCP's loopback HTTP self-call with an in-process drift client
  while preserving the split-service HTTP path.
- Raised the coordinator timeout budget to 50 seconds, made it configurable,
  and added warning-level failure visibility.
- Rebuilt and rolled out the coordinator, feature-agent, drift-agent, and
  drift-MCP images through CI/GitOps at immutable Artifact Registry digests.
- Sent a valid live coordinator request using the stream feature contract and
  synthetic market-stress data. It returned HTTP 200, a non-empty answer, two
  citations, and both specialists.
- Captured Prometheus output for all requested token, generation, TTFT, PII,
  agent-call, MCP-tool-call, and invocation-failure families.
- Registered both rows, regenerated the matrix, and passed the strict two-repo
  audit at 60/60 LLM rows and 100/100 points without design-only cuts.
- Ran platform .nd platform .est gates successfully, then hibernated the cluster:
  the evidence VM is `TERMINATED` and both node pools have zero active nodes.

## Decisions

Evidence stores aggregate labels and synthetic data only. Pod names, IPs,
credentials, and infrastructure identifiers are omitted from the machine-
readable artifacts. The successful nested coordinator payload is the canonical
capture; an earlier malformed top-level probe is retained only as a diagnosis
note and is not claimed as evidence.

## Verification

- Strict platform .vidence audit: passed, no `--accept-design-only`.
- Stage 1 quality gates: `311 passed`, all four gates passed.
- platform .uite: `503 passed, 35 skipped`.
- Observability requirement tests with GitOps checkout: `6 passed`.
