# End-to-end service integration

Status: completed (verified 2026-08-12)

## Objective

Make the Phase 2 product/evidence path reproducibly runnable end to end through the existing GitOps/GKE runtime: web request → coordinator → specialist agents → MCP tools → live model gateway/inference, with readiness, drift data, and telemetry checks. Keep the Phase 1 local-first pipeline unchanged.

## Expected output

1. A documented, repeatable E2E command/runner that brings the deployed service graph to a ready state, warms the inference service when it is cold, executes a real coordinator request, and reports PASS/FAIL evidence for every required service.
2. A compatible web/coordinator request contract that sends real numeric drift observations when available, producing a non-empty drift report instead of a `count=0` artifact.
3. GitOps policy/configuration that permits the deployed agents to export OTLP telemetry to the existing Jaeger service and a verification check proving that export no longer times out.
4. Focused automated tests and user-facing runbook updates for the new E2E path.

## Acceptance criteria

- The E2E runner -> waits for web, feature-MCP, drift-MCP, feature-agent, drift-agent, coordinator, gateway/model, Prometheus, and Jaeger -> prints a structured PASS/FAIL result with actionable diagnostics.
- The inference warm-up path -> invokes the configured live gateway/model and waits for a ready endpoint -> handles a cold Knative revision without requiring an undocumented manual `kubectl scale` operation.
- The coordinator -> receives a valid feature request plus numeric drift rows -> returns a non-empty answer with feature and drift citations, both specialist tool calls, and a non-empty drift observation set.
- The web assistant route -> preserves its existing response/stream contract -> forwards optional real drift observations without inventing data and remains compatible with callers that do not provide them.
- The agents -> export OTLP traces to the existing monitoring namespace -> stop producing the current Jaeger egress timeout when the E2E request is executed.
- The verification suite -> exercises the runner/configuration and changed web/data contracts -> passes focused tests, lint/type checks for touched packages, and the repository’s applicable quality gates.
- The documentation -> describes exact prerequisites, command, environment variables, expected output, and cleanup -> lets another operator reproduce the same E2E run.

## Scope boundary

In scope: source-repo E2E orchestration and contract tests, the web assistant drift-input boundary, GitOps NetworkPolicy/readiness/warm-up integration, and docs needed to operate the path.

Out of scope: replacing GitOps/GKE with a new local Docker Compose architecture, changing Phase 1 DAGs or data contracts, retraining/replacing the model, redesigning the web UI, changing Supabase authentication policy, or adding cloud infrastructure outside the existing GitOps repo.

## Non-negotiable constraints

- Phase 2 is additive-only in the source repo; do not edit Phase 1 DAGs or generated `warehouse.db`, `outputs/**`, or `docs/evidence/**`.
- GitOps remains the deployment source of truth; no production-only manual patch is accepted as the implementation.
- Do not fabricate feature or drift observations. The compatibility path must tolerate absent optional observations and only forward values supplied by the real caller/context.
- Preserve existing public web stream/API contracts and existing coordinator specialist payload shape unless a deliberately additive field is required.
- Use the repository’s existing Python/TypeScript tooling and test conventions; use `apply_patch` for source edits.
- All acceptance criteria use WHO → ACTION → RESULT semantics and must be verified before completion.

## Touchpoints

Source repository:

- `apps/web/src/app/api/assistant/stream/route.ts` and its assistant context/types/tests for the additive drift observation contract.
- `scripts/` for the E2E runner and focused runner tests.
- `apps/web/package.json`, `apps/web/README.md`, and/or the appropriate Phase 2 docs for the operator command.
- Existing coordinator/agent/MCP contract tests as regression surfaces; no Phase 1 pipeline modules.

GitOps repository (`/home/pearspringmind/Studying/FSDS/financial-distress-gitops`):

- `platform/agents/agent-sandbox.yaml` for OTLP egress policy.
- Existing model/gateway and observability manifests for readiness/warm-up integration.
- Existing `Makefile`/runbook conventions for exposing the E2E command without duplicating deployment logic.

## Phases

1. Define and test the additive web→coordinator drift observation contract; preserve the existing no-observation behavior.
2. Implement the E2E runner with service readiness, cold-model warm-up, live coordinator request, and machine-readable evidence output.
3. Integrate the runner with the GitOps operational command and fix the agent telemetry egress policy.
4. Run focused tests, live E2E/manual browser verification, broader applicable gates, code review, and documentation/project sync-back.

## Verification commands

- `.venv/bin/python -m pytest tests -k 'assistant or phase2 or e2e'`
- `pnpm --dir apps/web typecheck && pnpm --dir apps/web lint && pnpm --dir apps/web test`
- GitOps manifest validation plus the new E2E command against the existing GKE context.
- `.venv/bin/python scripts/run_stage1_quality_gates.py` only if touched shared Python contracts require the full repository gate; otherwise run the narrowest applicable Phase 2 gates and record the rationale.

## Risks and rollback

- A cluster hibernation or cold Knative revision can exceed normal readiness time; use bounded waits and diagnostics, never an infinite retry.
- NetworkPolicy changes must be namespace/port scoped to Jaeger OTLP and remain default-deny otherwise; rollback is the single policy rule if telemetry verification exposes an unintended path.
- If the web caller has no real numeric drift observations, the runner/direct coordinator contract remains the authoritative live proof; the web route must not synthesize values.

## Verification result

- Source and GitOps changes are implemented in the working trees; the detailed evidence is recorded in [`plans/reports/e2e-integration-260812-1742-end-to-end-verification.md`](reports/e2e-integration-260812-1742-end-to-end-verification.md).
- The live Phase 2 request path passed against GKE: all required workloads and service endpoints were ready, the model gateway returned HTTP 200, the coordinator returned both specialists and citations, Prometheus reported five healthy targets, and Jaeger exposed spans for coordinator, feature, drift, and MCP services.
- The browser manual test passed on NVL using the new web/source chain: the UI displayed both tool steps and the drift report with `relative_change=0.6` and `passed=True`.
- The remaining Argo `platform-agents` `OutOfSync/Degraded` condition is pre-existing kagent CRD synchronization failure (`agents.kagent.dev` annotation size/resource mapping errors), not a failure of the Phase 2 service path. The new OTLP policy is present in the GitOps working tree and was applied for the telemetry proof; it still needs the normal Git commit/PR/Argo sync to become durable.
