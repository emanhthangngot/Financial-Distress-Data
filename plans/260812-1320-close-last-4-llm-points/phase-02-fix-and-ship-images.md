---
phase: 2
title: "Fix the loopback and the coordinator timeout budget, ship through CI"
status: completed
priority: P1
effort: "0.5d code + 1 CI round"
dependencies: [1]
---

# Phase 2: Fix the loopback and the coordinator timeout budget, ship through CI

# 0 points (unblocks 4)

## Overview

Two source changes, both narrow, plus the image rebuild that closes Defect B as
a side effect: remove drift-mcp's HTTP call to its own process, and make the
coordinator's fan-out timeout larger than the budgets it wraps and configurable
from the Deployment.

## Requirements

- Functional:
  - The drift MCP tool reaches `_calculate_drift` without a network hop when it
    is served from the same process, while still supporting a split deployment
    where the drift API is a separate service.
  - `Coordinator.timeout_seconds` is set from the environment in `create_app`
    and defaults above the specialist HTTP budget, so a slow-but-successful
    generation returns an answer instead of `AgentFailure`.
  - A coordinator `AgentFailure` is distinguishable in logs from a successful
    response, so a future live failure names itself instead of surfacing as
    `MALFORMED_RESPONSE`.
- Non-functional: `DriftApiClient` stays a Protocol with the same `report`
  signature — no public contract break. No Phase 1 file touched. No test's
  expected value edited to pass.

## Architecture

**Loopback removal.** `DriftMcpService` already depends on the
`DriftApiClient` Protocol (`mcp_server.py:20-21`), so the fix is a second
implementation, not a rewrite: an in-process client whose `report` validates the
payload into `DriftRequest` and runs `_calculate_drift` under
`asyncio.to_thread` — exactly what the HTTP route does today
(`main.py:239-241`), minus serialization and the socket.

`create_mcp_runtime` selects it when `DRIFT_API_BASE_URL` is unset or resolves
to this process's own loopback address; an explicit non-loopback URL keeps the
existing `HttpxDriftApiClient`. That preserves the split-deployment path while
making the default path incapable of self-calling.

Import direction: `main.py` already imports `mcp_server` lazily inside
`create_app` (`main.py:144`), so `mcp_server` importing `_calculate_drift` and
`DriftRequest` from `.main` must also be lazy (inside the client's `report` or
the factory) to avoid a cycle at module import. `create_mcp_runtime`'s docstring
promises "no sockets or sessions on import" — the in-process client must keep
that promise, and `McpRuntime.api` must stay a valid async context manager so
`main.py`'s lifespan (`main.py:152-157`) still works unchanged.

If phase 1 proved the cause is environmental rather than in-process, this change
still ships — a service HTTP-calling itself to reach an imported pure function
is wrong regardless — and the environmental fix lands alongside it, in the
GitOps repo if it is a NetworkPolicy/config matter.

**Timeout budget.** Today: coordinator `10.0s` wrapping an
`HttpSpecialistClient` at `45.0s` wrapping a renderer at `30.0s` generating 256
tokens on CPU. The outermost bound must be the largest. Read it from
`AGENT_TIMEOUT_SECONDS` in `create_app` with a default above the 45s specialist
budget, and set it explicitly on the coordinator Deployment. Keep the web
route's own deadline (`config.timeoutMs`) in mind — if it is below the new
coordinator budget the UI still times out first, so check
`readInferenceConfig` and the coordinator Deployment env together and make the
edge budget the largest of all.

**Failure visibility.** `/v1/run` returns `AgentFailure` with HTTP 200
(`runtime.py:380-391`), which is why a real failure reads as
`MALFORMED_RESPONSE` at the UI. Changing the status code is a public-contract
change and is **out of scope**; instead log the `AgentFailure.error` at WARNING
in the coordinator branch so phase 3 can read the cause from pod logs in
seconds. If the correlated round-trip in phase 3 still fails, that log line is
the diagnosis.

## Related Code Files

- Modify: `apps/drift-mcp/app/mcp_server.py` — add the in-process client;
  select it in `create_mcp_runtime`
- Modify: `src/agents/runtime.py` — `AGENT_TIMEOUT_SECONDS` wiring in
  `create_app`; WARNING log on the coordinator `AgentFailure` branch
- Modify (only if the budget fix needs it): `src/agents/coordinator.py`
- Modify: `tests/phase2/` — drift-mcp tool tests and coordinator runtime tests
- Modify (GitOps repo): `platform/agents/agent-deployments.yaml` —
  `AGENT_TIMEOUT_SECONDS` on the coordinator container; digest bumps land via CI
- Read: `apps/web/src/lib/server/inference-config.ts` — confirm the edge
  deadline exceeds the new coordinator budget
- Do not touch: any `dags/*.py` outside `phase2/`, `src/collectors`,
  `src/generator`, `src/streaming`, `src/transforms`, `src/quality`,
  `src/catalog`, `src/metadata`

## Implementation Steps

1. Write the failing test first: an MCP `build_realtime_drift_report` call
   against `create_app(mount_mcp=True)` that asserts `ok=True` and a report
   body, with no HTTP client configured. It must fail before the fix.
2. Add the in-process `DriftApiClient` implementation and the selection logic in
   `create_mcp_runtime`. Keep `HttpxDriftApiClient` and its tests intact.
3. Add a test asserting the split-deployment path still uses the HTTP client
   when `DRIFT_API_BASE_URL` names a non-loopback host.
4. Wire `AGENT_TIMEOUT_SECONDS` in `create_app`; test that a specialist slower
   than the old 10s default now returns a `CoordinatorResponse` rather than
   `AgentFailure`.
5. Add the coordinator `AgentFailure` WARNING log and a test that the error
   string reaches the logger.
6. Run narrow first: `.venv/bin/python -m pytest tests -k "drift_mcp or
   coordinator or runtime"`. Then the full suite:
   `.venv/bin/python -m pytest tests`. Then
   `.venv/bin/python scripts/run_stage1_quality_gates.py` (ruff, black,
   compose config, Phase 1 no-regression) — exit 0 is the definition of done.
7. Commit with Conventional Commits, no AI attribution trailer, and open a PR to
   `dev`. The diff touches `src/agents/**`, so the coordinator, feature and
   drift agent workflows all fire in one round; `apps/drift-mcp/**` triggers the
   drift-mcp image build.
8. Watch CI to green on all four images, then confirm the four digest-bump PRs
   land on GitOps `master`.
9. Set `AGENT_TIMEOUT_SECONDS` on the coordinator Deployment in the GitOps repo
   and confirm the edge deadline is the largest budget in the chain.

## Success Criteria

- [x] New drift-mcp test fails before the fix and passes after.
- [x] Split-deployment HTTP path still covered and green.
- [x] Coordinator returns a response for a specialist slower than 10s.
- [x] `AgentFailure.error` appears in coordinator logs at WARNING.
- [x] `.venv/bin/python -m pytest tests` green, zero skips beyond the documented
      Docker/Postgres-gated ones.
- [x] `scripts/run_stage1_quality_gates.py` exit 0, `status: pass`.
- [x] Four images built and signed; four digests bumped on GitOps `master`:
      `drift-mcp`, `coordinator`, `feature-agent`, `drift-agent`.
- [x] `AGENT_TIMEOUT_SECONDS` present on the coordinator Deployment; the web
      edge deadline is greater than it.
- [x] No Phase 1 file and no existing test expectation modified.

## Risk Assessment

- **Import cycle between `main.py` and `mcp_server.py`.** Mitigation: keep the
  import inside the function, and cover it with a test that imports
  `mcp_server` standalone and asserts no socket or session is opened.
- **`McpRuntime.api` is entered as an async context manager by the lifespan.**
  The in-process client must implement `__aenter__`/`__aexit__` as no-ops or the
  app will not start. Covered by the phase's app-startup test.
- **Raising the coordinator timeout hides a genuinely hung dependency.**
  Mitigation: the WARNING log plus the existing `observe_failure` counters make
  a hang visible as a slow-but-counted failure rather than a silent one; the
  edge deadline still bounds the user-visible request.
- **Four parallel image builds contend or one fails mid-round.** Mitigation:
  they are independent workflows; a single failure is re-runnable via
  `workflow_dispatch` without rebuilding the other three.
- **The GitOps digest-bump PR does not auto-merge.** Mitigation: phase 3 starts
  by verifying the running digests match the fix commit, before spending window
  time on anything else.
