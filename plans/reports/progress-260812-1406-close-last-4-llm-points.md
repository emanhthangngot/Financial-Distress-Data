# Close Last 4 LLM Points — Progress Report

Date: 2026-08-12 14:06 Asia/Saigon
Branch: `codex/phase06-llm-submission`

## Completed

- Phase 1 reproduced the configured drift-MCP topology under bare uvicorn and
  the built image with `--cpus 0.5 --memory 512m`; both MCP calls returned
  `ok=True` in under 0.1s and emitted the `/v1/drift/report` access line.
- Added `InProcessDriftApiClient` with lazy imports and async-context-manager
  compatibility. Loopback/default URLs use it; explicit non-loopback URLs keep
  `HttpxDriftApiClient`.
- Raised the coordinator default timeout to 50s, wired `AGENT_TIMEOUT_SECONDS`,
  and added a WARNING log for coordinator `AgentFailure` while retaining the
  HTTP-200 response contract.
- Added the coordinator Deployment env entry in the sibling GitOps checkout.
- Added mounted MCP, split-deployment, timeout wiring, slow specialist, and
  failure-log tests.

## Verification

- `.venv-phase2/bin/python -m pytest tests/phase2 -q` → `503 passed, 35 skipped`.
- `.venv/bin/python -m pytest tests -q` → `311 passed`.
- `.venv/bin/python scripts/run_stage1_quality_gates.py` → all four gates pass,
  including `status: pass` for the Stage 1 evidence audit.
- Ruff passes for the full configured source/test/script scope.
- Full-repo Black was also checked with `.venv-phase2`; it reports two existing
  unrelated script formatting failures:
  `scripts/demo_duckdb_index.py` and `scripts/build_schema_evidence.py`.

## Not complete / blockers

- CI image builds, digest-bump PRs, and the GitOps timeout change are not
  committed or pushed; the source and sibling GitOps worktrees are intentionally
  dirty pending user commit/PR direction.
- The active GKE context has no running workloads: the observed pod list is
  `Pending`, and `kubectl -n phase2-data get pods -l app=drift-mcp` returns no
  resources. Phase 3 cannot capture live HTTPS, PromQL, Jaeger, or screenshots.
- The two rows remain `design_only`; no evidence file, rubric registration, or
  matrix regeneration was performed. The strict zero-cut gate was not run.
- The local probes do not prove the cluster-side hang mechanism. The exact
  in-pod loopback confirmation command is recorded in
  `reports/phase-01-repro.md` for the next live window.

## Acceptance criteria status

- Drift-MCP runtime -> invokes the loopback report path -> mounted MCP returns a
  successful report without an HTTP self-call (verified locally).
- Split deployment -> sets a non-loopback API URL -> existing HTTP client path
  remains selected (unit-tested).
- Coordinator runtime -> uses default/env timeout -> budget is 50s by default
  and configurable, above the 45s specialist HTTP budget (unit-tested).
- Coordinator runtime -> returns `AgentFailure` -> HTTP 200 schema remains
  stable and the error is emitted at WARNING (unit-tested).
- Live cluster -> runs all four new images and serves PromQL/HTTPS evidence ->
  not yet satisfied because the current cluster workloads are Pending.
