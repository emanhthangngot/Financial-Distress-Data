---
title: "platform .tage 2 Completion"
description: "Close every open requirement of unified-phase2 phase-02: AI request path with persisted quota/rate-limit/audit, an outbox worker runtime, a >90% coverage gate on changed code, axe accessibility proof, and committed deterministic evidence."
status: done
priority: P1
effort: "6-9 focused workdays"
branch: dev
tags: [phase2, product-shell, supabase, rbac, evidence]
blockedBy: []
blocks: [260802-1037-unified-phase2-ml-llm-gitops]
created: 2026-08-05
---

# platform .tage 2 Completion

## Overview

`plans/260802-1037-unified-phase2-ml-llm-gitops/phase-02-build-product-shell-supabase-rbac-and-ux-states.md`
is the ground truth for the DistressLens product plane. Its UI half is built and
verified (33 analyst + 16 platform Playwright assertions, 112 unit tests,
typecheck and lint clean on `dev` at `e638b95`). Its server half is not: there is
no AI request path, no persisted quota or rate limit, no audit write at the
product boundary, no worker process behind the outbox, no coverage gate, no
accessibility assertion, and no committed evidence frames.

This plan closes exactly those gaps. It adds nothing the parent phase did not
already require, and it does not touch platform .ode, the GitOps repo, or any
phase-03..08 surface.

**Boundary with Phase 6.** The LLM serving chain (kagent -> agentgateway ->
Envoy AI Gateway -> KServe) belongs to phase-06. This plan builds only the
product boundary in front of it: authorize, rate limit, consume quota, audit,
then stream from whatever OpenAI-compatible endpoint the environment names. When
the endpoint is absent or the evidence plane is off, the surface reports that
honestly. Phase 6 lands by pointing an environment variable at a real endpoint,
with no change to `apps/web` code.

## Accepted Decisions (2026-08-05, product owner)

1. **AI backend: plane-gated proxy, env-configured.** `DISTRESSLENS_INFERENCE_URL`
   + `DISTRESSLENS_INFERENCE_TOKEN` name an OpenAI-compatible streaming endpoint.
   Unset, or `planeReady === false`, means the route returns the `eks_off` /
   `unavailable` assistant state. The route never fabricates an analysis.
2. **Quota and rate limit: Supabase table + atomic RPC.** One `ai_request_usage`
   row per user per window, incremented inside `consume_ai_quota()` so two
   concurrent streams cannot both pass a limit of one. No external Redis.
3. **Evidence: curated PNG subset + full manifest.** Every capture's JSON
   manifest is committed; PNGs are committed only for the rubric-named frames
   (three approved routes x three viewports, plus degraded, forbidden,
   cost-cap-denied, stale-fencing, quota-exhausted, streaming).
4. **Coverage: >90% on changed code, gated.** v8 thresholds over
   `apps/web/src/lib`, `apps/web/src/components`, and `packages/contracts/src`,
   with component tests supplying the missing component coverage. Server page
   components stay covered by Playwright, not by render tests.

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | An analyst AI request is authorized, rate limited, quota-consumed, audited and streamed — or truthfully refused — entirely server-side | P0 |
| 2 | Outbox intents become executed work through a real worker process with leases and fencing | P0 |
| 3 | Every phase-02 validation line (coverage, RLS pairs, Playwright flows, screenshots, axe) has an executable command and a stored artifact | P0 |
| 4 | The parent phase-02 checklist can be ticked against evidence, not assertion | P1 |

## Phases

| # | Phase | Estimate | Status |
|---|-------|----------|--------|
| 1 | [Quota, rate limit and audit persistence](./phase-01-quota-rate-limit-and-audit-persistence.md) | 1-2 days | Done |
| 2 | [AI request path and SSE transport](./phase-02-ai-request-path-and-sse-transport.md) | 2-3 days | Done |
| 3 | [Outbox worker runtime](./phase-03-outbox-worker-runtime.md) | 1-2 days | Done |
| 4 | [Coverage gate and component tests](./phase-04-coverage-gate-and-component-tests.md) | 1-2 days | Done |
| 5 | [Accessibility proof and evidence publication](./phase-05-accessibility-and-evidence-publication.md) | 1 day | Done |

Dependencies: 2 depends on 1. 4 depends on 2 and 3, because it gates the code
they add. 5 depends on 2, because it captures the assistant's streaming and
quota frames. 3 is independent of 1 and 2 and owns different files, so it may
run in parallel.

## Task-Level Execution Plan

Each phase file carries a `## Task-Level Breakdown` section with per-task
specs: files touched, the exact function/signature to add, the test that proves
it, and the gate command. This board is the ordering view over them.

### platform . Quota, rate limit and audit persistence (1-2d)

| # | Task | Deliverable | Tests | Depends |
|---|------|-------------|-------|---------|
| 1.1 | Contracts budget module | `packages/contracts/src/ai-budget.ts` + export in `index.ts` | `ai-budget.test.ts` (window math, `RateLimitState`, resetsAt) | — |
| 1.2 | Migration + rollback | `supabase/migrations/20260805TNNNNN_phase2_ai_usage_audit.sql` + `rollback/…_down.sql` | RLS pytest cases | — |
| 1.3 | RLS/atomicity pytest suite | cases in `tests/platform/product/test_rbac_rls.py` | `.venv/bin/python -m pytest tests/platform/product -q` | 1.2 |
| 1.4 | Server RPC wrappers | `apps/web/src/lib/server/ai-budget.ts` | `ai-budget.test.ts` (server) | 1.1, 1.3 |
| 1.5 | Data port read | `readAiBudget` in `port.ts` + both adapters | vitest adapter tests | 1.4 |
| 1.6 | Docs + gates | `docs/platform/security/rbac.md` | full gate set | 1.1-1.5 |
### platform . AI request path and SSE transport (2-3d)

| # | Task | Deliverable | Tests | Depends |
|---|------|-------------|-------|---------|
| 2.1 | Frame contract + codec | `packages/contracts/src/assistant-stream.ts` + export | codec round-trip, split/malformed frames | 1.1 |
| 2.2 | Inference config | `apps/web/src/lib/server/inference-config.ts` | env redaction predicate | — |
| 2.3 | Chunk -> frame translator | `apps/web/src/lib/server/inference-stream.ts` | token/tool/refusal/malformed/timeout/abort | — |
| 2.4 | Route handler | `apps/web/src/app/api/assistant/stream/route.ts` | one audit row per branch | 2.2, 2.3, 1.4 |
| 2.5 | Streaming transport | `apps/web/src/lib/assistant/streaming-transport.ts` | SSE parse, frame -> turn, abort | 2.1 |
| 2.6 | Provider + panel wiring | `assistant-provider.tsx`, `assistant-panel.tsx`, `assistant-message.tsx` | component tests (phase 4) + e2e | 2.5 |
| 2.7 | Playwright evidence additions | `apps/web/e2e/analyst-surfaces.spec.ts` + fixture upstream | `pnpm --filter @distresslens/web e2e` | 2.4-2.6 |
| 2.8 | Docs + gates | `docs/platform/product.md` | full gate set + e2e | 2.7 |

### Phase 3 — Outbox worker runtime (1-2d, parallel to 1/2)

| # | Task | Deliverable | Tests | Depends |
|---|------|-------------|-------|---------|
| 3.1 | Handler registry | `apps/web/src/lib/server/outbox-handlers.ts` | `outbox-handlers.test.ts` | — |
| 3.2 | Worker entrypoint | `scripts/phase2/outbox-worker.ts` | signal/backoff (unit-ish, manual) | 3.1 |
| 3.3 | Lease/fencing integration | pytest `tests/platform/product/test_outbox_worker.py` | two workers, lease expiry, stale fencing, maxAttempts | 3.2 |
| 3.4 | Package script + docs + gates | `apps/web/package.json`, `docs/platform/product.md` | full gate set | 3.3 |

### Phase 4 — Coverage gate and component tests (1-2d)

| # | Task | Deliverable | Tests | Depends |
|---|------|-------------|-------|---------|
| 4.1 | Coverage on, baseline | `apps/web/vitest.config.ts` | record baseline | 2.6, 3.1 |
| 4.2 | jsdom project + Testing Library | vitest config projects, `package.json` dev deps | — | 4.1 |
| 4.3 | Component tests x4 | panel, role button, disclaimer, nav rail `.test.tsx` | `pnpm test` at 90/90 | 4.2 |
| 4.4 | Contracts thresholds | `packages/contracts/vitest.config.ts` | `pnpm test` | — |
| 4.5 | Close lib gaps honestly | delete unreachable branches, behavior tests | `pnpm test` | 4.3 |
| 4.6 | CI + docs + gates | `.github/workflows/ci.yml`, `docs/platform/product.md` | full gate set + both e2e suites | 4.4, 4.5 |

### Phase 5 — Accessibility proof and evidence publication (1d)

| # | Task | Deliverable | Tests | Depends |
|---|------|-------------|-------|---------|
| 5.1 | axe suite + config | `e2e/a11y.spec.ts`, `playwright.a11y.config.ts`, `@axe-core/playwright` | `pnpm --filter @distresslens/web e2e:a11y` | 2.6 |
| 5.2 | Fix violations + motion/focus | component fixes, reduced-motion + focus-visible assertions | e2e:a11y green | 5.1 |
| 5.3 | Evidence publication script | `scripts/phase2/publish-evidence.ts` + allowlist | run both evidence suites + publish | 2.7 |
| 5.4 | Evidence README + a11y doc | `docs/platform/evidence/product/README.md`, `accessibility.md` | manual review | 5.3 |
| 5.5 | Reconcile parent phase-02 | tick boxes / defer in parent file + plan status | manual diff | 5.4 |
| 5.6 | Full gates incl. platform . n/a | all gates + `run_stage1_quality_gates.py` | 5.5 |

### Critical path

```
1.1 -> 1.2 -> 1.3 -> 1.4 -> 1.5 -> 1.6
                     \-> 2.1 -> 2.2 -> 2.3 -> 2.4 -> 2.5 -> 2.6 -> 2.7 -> 2.8
                                                                     \-> 4.1 -> 4.2 -> 4.3 -> 4.4 -> 4.5 -> 4.6
                                                                     \-> 5.1 -> 5.2 -> 5.3 -> 5.4 -> 5.5 -> 5.6
3.1 -> 3.2 -> 3.3 -> 3.4 (parallel track, merges at 4.1)
```

### Sequencing notes

- Phase 3 is a separate parallel track: its files (`scripts/`, `outbox-handlers.ts`)
  do not collide with phases 1/2, so it can be picked up in any order after phase
  4.1's coverage baseline exists.
- Tasks that land in `apps/web/src` after phase 4.1 must keep the 90/90 gate
  green; write the component test in the same commit as the component change.
- Evidence frames (2.7, 5.3) are generated and then published with an explicit
  command; never edit `docs/platform/evidence/` by hand.

## Non-Goals

- Model serving, RAG retrieval, MCP tool execution, agent sandboxing — phase-06.
- EKS, Terraform, Argo CD, any AWS resource — the separate `financial-distress-gitops` repo.
- Any change to platform .ollectors, DAGs, transforms, quality gates or `warehouse.db`.
- Redesigning approved UI hierarchy. Visual work is limited to states the parent phase already requires.
- Auth UI (sign-in/sign-up pages). Session resolution already exists in `apps/web/src/lib/server/session.ts`.

## Architecture Delta

```
browser (assistant panel)
  |
  |  POST /api/assistant/stream   (fetch + ReadableStream, not EventSource:
  |                                the request needs a body and an Origin check)
  v
Next.js route handler  [apps/web/src/app/api/assistant/stream/route.ts]
  1 resolveSession()            -> role, aal, userId, planeReady
  2 guardRequest()              -> role/AAL, origin, rate limit, quota
  3 consume_ai_quota() RPC      -> atomic increment, returns remaining
  4 record_audit_event() RPC    -> action, actor, outcome; no prompt, no token
  5 planeReady && INFERENCE_URL -> stream proxy; else emit `eks_off`
  v
SSE frames: `state`, `token`, `tool`, `citation`, `done` | `error`
  v
StreamingAssistantTransport   [apps/web/src/lib/assistant/streaming-transport.ts]
  v
AssistantProvider (existing component tree, unchanged)

outbox_events --claim_outbox_events()--> worker process
  [scripts/phase2/outbox-worker.ts, service-role, long-running]
  handler registry -> phase-03 GitOps dispatch lands behind the same interface
  --complete_outbox_event() / fail_outbox_event()--> transition + audit
```

## Success Criteria

- [ ] Analyst with quota left -> asks the assistant while the plane is READY -> receives a streamed answer, one `ai_request_usage` increment and one `audit_log` row containing no prompt text.
- [ ] Analyst at the quota limit -> asks again -> receives `QUOTA_EXHAUSTED` copy with the reset time, no stream opens, and no second increment.
- [ ] Two concurrent requests with one remaining quota unit -> exactly one succeeds -> the RPC serializes and the other is refused.
- [ ] Analyst with the plane OFF -> asks the assistant -> receives the `eks_off` state naming what is cached and what is unavailable, never a fabricated analysis.
- [ ] Operator -> requests a provision -> the worker claims the event under a lease, completes it, the session state advances, and a second worker claims nothing.
- [ ] Operator -> a transition supersedes an in-flight event -> the worker's completion is refused as stale fencing and the event is marked FAILED without mutating the session.
- [ ] CI -> runs `pnpm test` -> fails when line or branch coverage on `apps/web/src/lib`, `apps/web/src/components` or `packages/contracts/src` drops below 90%.
- [ ] Accessibility reviewer -> runs the axe suite at 1440/1024/390 -> finds zero serious or critical violations on every route in the inventory.
- [ ] Reviewer -> opens `docs/platform/evidence/product/` -> finds a manifest for every captured frame and committed PNGs for the rubric-named states.
- [ ] Maintainer -> reads parent `phase-02` -> finds every requirement and success-criterion box ticked with a named artifact or command.

## Verify Commands

```bash
pnpm test                 # vitest (contracts + web) with coverage thresholds
pnpm typecheck
pnpm lint
pnpm --filter @distresslens/web e2e         # analyst evidence run, 3 viewports
pnpm --filter @distresslens/web e2e:roles   # operator/viewer evidence run
pnpm --filter @distresslens/web e2e:a11y    # axe pass (added in phase 5)
.venv/bin/python -m pytest tests/platform/product -q   # RLS role/action pairs
```

platform .ate stays untouched and must still pass:
`.venv/bin/python scripts/run_stage1_quality_gates.py`.

## Risks

| Risk | Mitigation |
|---|---|
| Streaming through a serverless function hits the response timeout | Stream with Web Streams API, cap the request below the platform limit, and emit the `timeout` frame the UI already renders |
| Quota RPC becomes a hot row and serializes analyst traffic | Coursework scale is 2 concurrent AI streams; the counter is per user per window, never global |
| Audit rows leak prompt text | The RPC accepts no free-text prompt parameter — only action, outcome, context id and counters; the signature removes the possibility rather than relying on review |
| Committed PNGs churn the repo on every regeneration | Only rubric-named frames are committed, regenerated deliberately; CI compares manifests, not bytes |
| A coverage threshold pushes toward tests that assert implementation detail | Thresholds cover lib/components where behavior is testable; server pages stay Playwright-covered by design, recorded in the vitest config comment |

## Open Questions

- None. The four material decisions were resolved with the product owner on 2026-08-05 and are recorded above.

<!-- slug: phase2-stage2-completion -->
