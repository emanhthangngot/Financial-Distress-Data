---
phase: 2
title: "AI request path and SSE transport"
status: pending
priority: P1
effort: "2-3d"
dependencies: [1]
---

# Phase 2: AI request path and SSE transport

## Overview

`apps/web/src/lib/assistant/assistant-transport.ts` currently ships
`UNAVAILABLE_TRANSPORT` and states plainly that the agent request path does not
exist. This phase builds it: one authenticated, guarded, audited streaming route
handler, and a transport that renders its frames through the assistant states the
UI already implements. The model itself stays behind an environment-named
endpoint that phase-06 fills in.

## Requirements

Functional:

- `POST /api/assistant/stream` authorizes `analyst.run_ai_request` server-side,
  checks origin, consumes budget atomically, and audits every outcome.
- The response is an SSE stream whose frames map one-to-one onto the existing
  `AgentMessageState` values: `streaming`, `tool_running`, `complete`, `timeout`,
  `policy_blocked`, `error`, plus the assistant-only `eks_off`/`unavailable`.
- When the plane is off or no inference endpoint is configured, the route returns
  the `eks_off` frame — never a generated answer, never an empty success.
- Citations and tool-trace entries stream as typed frames using the existing
  `Citation` and `ToolTraceEntry` contracts; the response carries model and agent
  version so the UI can label provenance.
- The client aborts cleanly (navigation, cancel button) and the server stops
  consuming upstream on abort.
- Remaining quota is visible in the assistant before the analyst spends it.

Non-functional:

- No prompt text, upstream token, or endpoint URL appears in any audit row, log
  line, error message or rendered surface.
- The whole path is typed end to end: the frame union lives in
  `packages/contracts` and both the route and the transport use it.
- Timeout is bounded below the hosting platform's response limit and produces the
  `timeout` frame rather than a dead connection.

## Architecture

**Why POST + fetch streams, not `EventSource`.** `EventSource` cannot send a
request body and cannot set headers, so the question would have to travel in the
query string — into access logs — and the CSRF-relevant `Origin` check that
`guardRequest` performs on mutations would lose its meaning. The client reads
`response.body` as a stream and parses SSE framing itself.

Frame union (`packages/contracts/src/assistant-stream.ts`):

```ts
export type AssistantFrame =
  | { type: "state"; state: AgentMessageState | "eks_off"; reason: string | null }
  | { type: "token"; text: string }
  | { type: "tool"; entry: ToolTraceEntry }
  | { type: "citation"; citation: Citation }
  | { type: "quota"; remaining: number; resetsAt: string }
  | { type: "done"; agentVersion: string | null; modelVersion: string | null }
  | { type: "error"; code: AssistantErrorCode; reason: string };
```

Route handler order — deliberately identical to the order `guardRequest`
documents, so a reader sees one policy, not two:

1. `resolveSession()` — role, aal, userId, planeReady.
2. `guardRequest({ action: "analyst.run_ai_request", mutating: true })` — role and
   AAL, then origin. Denial: audit `FORBIDDEN`, return 403 with a `state` frame.
3. `consumeAiBudget()` (phase 1) — atomic. Denial: audit `RATE_LIMITED` or
   `QUOTA_EXHAUSTED`, return 429 with the reset time.
4. Plane gate: `planeReady && DISTRESSLENS_INFERENCE_URL` — otherwise audit
   `PLANE_OFF` and return a 200 stream containing exactly the `eks_off` state
   frame and `done`. A 200 is correct: the request was handled, the plane's
   absence is product state, not a client error.
5. Proxy: open the upstream OpenAI-compatible stream with
   `DISTRESSLENS_INFERENCE_TOKEN`, translate its chunks into `AssistantFrame`s,
   forward the abort signal both ways, and enforce `ASSISTANT_TIMEOUT_MS`.
6. Terminate: audit `ALLOWED` (or `FAILED` with an error class, never an upstream
   message) and close the stream.

The upstream translation lives in a separate pure module
(`inference-stream.ts`) that takes an async iterable of upstream chunks and
yields `AssistantFrame`s, so every branch — token, tool call, refusal, malformed
chunk, early close — is unit-testable without a network or a Next.js request.

`StreamingAssistantTransport` implements the existing `AssistantTransport`
interface, so no component changes: `AssistantProvider` keeps its current API and
`UNAVAILABLE_TRANSPORT` stays as the explicit fallback when the route is absent.

## Related Code Files

- Create: `packages/contracts/src/assistant-stream.ts` + test — the frame union, error codes, SSE encode/decode helpers
- Modify: `packages/contracts/src/index.ts`
- Create: `apps/web/src/app/api/assistant/stream/route.ts` — the handler
- Create: `apps/web/src/lib/server/inference-stream.ts` + test — upstream chunk -> frame translation, timeout, abort, malformed input
- Create: `apps/web/src/lib/server/inference-config.ts` + test — env resolution, redaction, "configured?" predicate
- Create: `apps/web/src/lib/assistant/streaming-transport.ts` + test — fetch, SSE parse, frame -> `AssistantTurn` reduction, abort
- Modify: `apps/web/src/lib/assistant/assistant-transport.ts` — keep `UNAVAILABLE_TRANSPORT`, document when each is used
- Modify: `apps/web/src/components/assistant/assistant-provider.tsx` — select the transport, expose `cancel()`
- Modify: `apps/web/src/components/assistant/assistant-panel.tsx` — remaining-quota line, cancel affordance, tool-trace and citation rendering fed by streamed frames
- Modify: `apps/web/e2e/analyst-surfaces.spec.ts` — streaming, quota-exhausted, plane-off, timeout, policy-blocked assertions
- Modify: `docs/phase2/product.md` — the assistant request contract and its states

## Implementation Steps

1. Write the frame union and its SSE codec in contracts, with round-trip tests
   including a chunk split across packet boundaries and an unknown frame type
   (which must be ignored, not fatal).
2. Write `inference-stream.ts` tests first: token passthrough, tool-call
   translation, upstream refusal -> `policy_blocked`, malformed JSON chunk ->
   `error` without leaking the chunk, timeout -> `timeout` frame then close,
   client abort -> upstream aborted.
3. Implement `inference-stream.ts` and `inference-config.ts`.
4. Implement the route handler in the documented order; every branch writes
   exactly one audit row, asserted by test.
5. Implement `StreamingAssistantTransport` and wire the provider; keep the
   unavailable transport as the fallback when the route is not configured.
6. Add the remaining-quota line and cancel control to the panel, using the copy
   already established in `guards.ts`/`ASSISTANT_STATE_COPY`.
7. Extend the Playwright analyst suite: a fixture-mode fake upstream (a local
   route the test server points `DISTRESSLENS_INFERENCE_URL` at) proves streaming
   and timeout deterministically; plane-off and quota-exhausted come from fixture
   session env vars.
8. Run the gates plus `pnpm --filter @distresslens/web e2e`.

## Success Criteria

- [x] Analyst with `analyst.run_ai_request` and quota left -> posts a question with the plane READY -> receives ordered `state:streaming` -> `token`* -> `done` frames and one `audit_log` row with outcome `ALLOWED`.
- [x] Caller without the permission -> posts -> 403, one audit row `FORBIDDEN`, no budget consumed, and no indication whether the ticker exists.
- [x] Caller with a foreign `Origin` -> posts -> refused by `checkOrigin` before any budget or upstream call.
- [x] Analyst at the quota limit -> posts -> 429 carrying `resetsAt`, UI renders the quota copy, no stream opens.
- [x] Plane OFF or `DISTRESSLENS_INFERENCE_URL` unset -> posts -> 200 with exactly `state:eks_off` + `done`, audit `PLANE_OFF`, and the panel shows what is cached instead.
- [x] Upstream exceeds `ASSISTANT_TIMEOUT_MS` -> a `timeout` frame is emitted and the connection closes; the upstream request is aborted.
- [x] Client navigates away mid-stream -> the server observes the abort and stops reading upstream.
- [x] Grep of audit rows, server logs and rendered HTML after a full run -> contains no prompt text, no bearer token, and no inference URL.
- [x] `pnpm test`, `pnpm typecheck`, `pnpm lint`, `pnpm --filter @distresslens/web e2e` -> pass.

## Risk Assessment

- **Risk:** an upstream error message reaches the user or the audit row and leaks endpoint detail. **Mitigation:** the route maps upstream failures to a closed `AssistantErrorCode` set; the raw message never crosses the module boundary, and a test asserts it.
- **Risk:** budget is consumed for a request that then fails upstream. **Mitigation:** deliberate and documented — the unit is consumed at admission, and a failed request records `FAILED` in the audit row so a refund is a manual, auditable decision rather than an automatic path an attacker can drive.
- **Risk:** SSE parsing bugs surface as a hung UI. **Mitigation:** the codec is unit-tested against split and malformed frames, and the transport applies a client-side deadline independent of the server's.
- **Risk:** the fake upstream used in tests is mistaken for a product feature. **Mitigation:** it lives under `e2e/` only, is never imported by `src/`, and the evidence manifest labels those frames `REFERENCE_FIXTURE`.

## Task-Level Breakdown

> Grounded against `dev` at `e638b95`. Verified: `assistant-transport.ts` ships
> `UNAVAILABLE_TRANSPORT` and the `AssistantTransport.send(request)` interface
> (assistant-transport.ts:38); `AssistantProvider` takes a `transport` prop
> defaulting to `UNAVAILABLE_TRANSPORT` (assistant-provider.tsx:63); `SessionAction`
> already includes `analyst.run_ai_request` for `analyst` (role.ts:44);
> `session.ts` exposes `context.planeReady`, `context.role`, `context.aal`,
> `context.userId`. The frame union below adds an assistant-only `"eks_off"` value
> alongside the existing `AgentMessageState` from contracts.

### T2.1 — Contracts frame contract + SSE codec

- **Files:** Create `packages/contracts/src/assistant-stream.ts`, `assistant-stream.test.ts`; Modify `packages/contracts/src/index.ts`.
- **Spec:** add `ASSISTANT_ERROR_CODES = ["UPSTREAM_UNAVAILABLE","UPSTREAM_TIMEOUT","MALFORMED_RESPONSE","UPSTREAM_REFUSED","ABORTED"] as const` and the `AssistantFrame` union exactly as in the Architecture section (`state|token|tool|quota|done|error`), where `state.type.state` is `AgentMessageState | "eks_off"`. Add `encodeSseFrame(frame): string` and `decodeSseChunk(buffer: string): { frames: AssistantFrame[]; rest: string }` — a tolerant line-based parser that ignores unknown/empty lines and requires the `data:` prefix.
- **Tests (write first):** encode/decode round-trip for every frame kind; a frame split across two `data:` packet boundaries reassembles; an unknown `"type"` is ignored, not fatal; malformed JSON in a `data:` line is skipped without throwing; each frame's `data` is valid JSON after decode.
- **Verify:** `pnpm --filter @distresslens/contracts test && pnpm typecheck`.

### T2.2 — Inference config

- **Files:** Create `apps/web/src/lib/server/inference-config.ts`, `inference-config.test.ts`.
- **Spec:** `readInferenceConfig()` reads `DISTRESSLENS_INFERENCE_URL` + `DISTRESSLENS_INFERENCE_TOKEN` + `ASSISTANT_TIMEOUT_MS` (default 55_000, bounded below 60s) and returns `{ url: string | null; token: string | null; timeoutMs: number; isConfigured: boolean }`. `redactUrl(url)` returns a URL that strips any userinfo query/token for logging. `import "server-only"`.
- **Tests:** configured vs unset URL/token combos; default timeout; `redactUrl` never returns a host with `:token@`; an injected token never appears in any returned string.
- **Verify:** `pnpm --filter @distresslens/web test`.

### T2.3 — Chunk -> frame translator (TDD)

- **Files:** Create `apps/web/src/lib/server/inference-stream.ts`, `inference-stream.test.ts`.
- **Spec:** `translateInferenceChunks(chunks: AsyncIterable<OpenAIChunkLike>, opts: { timeoutMs: number; signal: AbortSignal }): AsyncIterable<AssistantFrame>`. Maps OpenAI SSE chunk fields: `choices[0].delta.content` -> `token`; `delta.tool_calls` -> `tool` (via `ToolTraceEntry`); refusal content -> `policy_blocked` state; `choices[0].finish_reason` -> done. Emits `timeout` state then closes when the deadline passes, and aborts the upstream reader when `signal` fires. A malformed chunk yields `error` (`MALFORMED_RESPONSE`) without leaking the raw chunk text.
- **Tests (write first):** token passthrough in order; tool-call translation to `ToolTraceEntry`; upstream refusal -> `policy_blocked`; malformed JSON chunk -> `error` with no raw chunk in the reason; timeout -> `timeout` frame; signal abort stops the reader.
- **Verify:** `pnpm --filter @distresslens/web test`.

### T2.4 — Route handler

- **Files:** Create `apps/web/src/app/api/assistant/stream/route.ts`.
- **Spec:** `export async function POST(req: NextRequest): Promise<Response>` implementing the six documented steps in order. Reads `resolveSession()`, `guardRequest({ context, action: "analyst.run_ai_request", mutating: true, rateLimit, quota })`, then `consumeAiBudget(client, context)`; on denial returns `403` + `state` frame (`FORBIDDEN`) or `429` + `state` frame + `quota_resets_at`; plane gate returns `200` + exactly `state:eks_off` + `done`; proxy path builds `fetch` to the OpenAI-compatible endpoint, pipes through `translateInferenceChunks`, forwards abort both ways, enforces `ASSISTANT_TIMEOUT_MS`. Every branch ends in exactly one `recordAuditEvent` call with outcome `ALLOWED|RATE_LIMITED|QUOTA_EXHAUSTED|FORBIDDEN|PLANE_OFF|FAILED`. Returns `text/event-stream` with `Cache-Control: no-store`.
- **Tests:** route-harness test calling the handler with stubbed `resolveSession`, `guardRequest`, `consumeAiBudget`, `recordAuditEvent`, and a mock `fetch`; assert each branch's status + frame sequence + exactly-one audit row.
- **Verify:** `pnpm --filter @distresslens/web test && pnpm typecheck`.

### T2.5 — Streaming transport

- **Files:** Create `apps/web/src/lib/assistant/streaming-transport.ts`, `streaming-transport.test.ts`.
- **Spec:** `class StreamingAssistantTransport implements AssistantTransport`, constructed with `(endpoint: string)`. `send(request)` does `fetch(endpoint, { method: "POST", body: JSON.stringify({ question, history, context }) })`, streams `response.body` through `decodeSseChunk`, and reduces frames into the final `AssistantTurn` (accumulating `token` text into `body`, `tool` into `toolTrace`, `citation` into `citations`, carrying `state`/`done`/`error`). Applies a client-side deadline independent of the server's. Exposes `abort()` that calls the underlying `AbortController`. A non-OK response maps `429` -> `state: QUOTA_EXHAUSTED` with `nextAction` reset copy, `403` -> `policy_blocked`.
- **Tests:** a `fetch` mock returning a Web-ReadableStream of SSE bytes; assert ordered frame reduction, quota-exhausted mapping, abort mid-stream, and that the endpoint body never contains a token.
- **Verify:** `pnpm --filter @distresslens/web test`.

### T2.6 — Provider + panel wiring

- **Files:** Modify `apps/web/src/components/assistant/assistant-provider.tsx`, `assistant-panel.tsx`, `assistant-message.tsx`.
- **Spec:** Provider selects `StreamingAssistantTransport` when the route is configured and keeps `UNAVAILABLE_TRANSPORT` as the fallback; expose `cancel()` on the store calling `transport.abort()`. Panel: render an `eks_off` nextAction line ("Các chỉ số và nguồn dữ liệu vẫn khả dụng, phân tích AI trực tiếp tạm chưa bật") using `ASSISTANT_STATE_COPY`; render the remaining-quota line fed by `readAiBudget`; render streamed citations and tool-trace entries per `AssistantMessage`; add a cancel affordance shown while `pending`.
- **Tests:** component coverage lands in phase 4; here verify with `pnpm typecheck` + Playwright additions in T2.7.
- **Verify:** `pnpm --filter @distresslens/web typecheck && pnpm lint`.

### T2.7 — Playwright evidence additions

- **Files:** Modify `apps/web/e2e/analyst-surfaces.spec.ts`; add a fixture-mode fake upstream under `apps/web/e2e/` only (never imported by `src/`).
- **Spec:** a local route the test server points `DISTRESSLENS_INFERENCE_URL` at streams a canned token sequence so streaming and timeout are deterministic. Assert: streaming success (frames ordered), quota-exhausted copy + 429, plane-off `eks_off` + cached content, timeout frame, policy-blocked. Fixture session env vars drive quota/plane states.
- **Verify:** `pnpm --filter @distresslens/web e2e`.

### T2.8 — Docs + full gates

- **Files:** Modify `docs/phase2/product.md` (assistant request contract, states, redaction rule).
- **Verify:** `pnpm test && pnpm typecheck && pnpm lint && pnpm --filter @distresslens/web e2e`.
