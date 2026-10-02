---
phase: 4
title: "Gap 04: Complete ML and LangGraph runtime"
status: pending
priority: P1
effort: "Remaining implementation after data contract"
dependencies: ["phase-02-data-and-features.md"]
---

# Gap 04: Complete ML and LangGraph runtime

## Objective

Finish missing production behavior only: a real model lifecycle and a clean hand-written-agent
cutover to LangChain/LangGraph while preserving current API/auth/MCP contracts.

## Tasks

1. Complete MLflow/KFP/Ray training, snapshot-safe promotion, drift trigger and model-serving proof.
2. Add LangChain/LangGraph dependencies and implement one parity graph behind the existing API.
3. Use PostgreSQL checkpointer for multi-replica session state, TTL, restart and tenant isolation.
4. Preserve repository-owned MCP validation, authorization, citation/abstention and circuit breaking.
5. Map typed graph events to the existing SSE contract, then delete the old renderer/coordinator path.
6. Run the fixed evaluation corpus and record only measured provider/model capabilities.

## Progress snapshot

The LangGraph coordinator pilot is implemented in `src/agents/langgraph_runtime.py` and is
selectable through `AGENT_ORCHESTRATION_BACKEND=langgraph`. Four focused graph tests and the
combined legacy/runtime suite pass, including provider-failure short-circuiting, citation
validation and tenant-scoped thread IDs. Provider execution, PostgreSQL checkpointer recovery,
model parity, SSE event mapping and deletion of the legacy path remain unverified because no
approved provider endpoint or production runtime window is available. This phase remains pending.

## Acceptance criteria

- [ ] ML pipeline -> trains on a frozen knowledge-time snapshot -> registry artifact and promotion result are compatible and reproducible.
- [ ] LangGraph pilot -> runs the existing feature/drift/answer flow -> task success, citations, auth, telemetry and external schemas are unchanged or improved.
- [ ] Graph replica -> restarts between nodes -> state resumes or returns an explicit incomplete result without duplicating side effects.
- [ ] Cutover -> removes old renderer/coordinator callers -> exactly one production orchestration path remains.

## Risks

Parity failure blocks cutover. Do not retain a permanent dual runtime or silently change provider after
partial streaming.
