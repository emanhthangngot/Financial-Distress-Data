import "server-only";
import { NextRequest } from "next/server";
import type { SupabaseClient } from "@supabase/supabase-js";
import { encodeSseFrame, type AssistantFrame } from "@distresslens/contracts";
import {
  assistantThreadKey,
  type AssistantContext,
} from "@/lib/assistant/assistant-context";
import type { AssistantTurn } from "@/lib/assistant/assistant-transport";
import {
  consumeAiBudget,
  recordAuditEvent,
  type AIAuditOutcome,
  type AiBudgetDecision,
  type AuditEventInput,
} from "@/lib/server/ai-budget";
import { guardRequest, type GuardContext } from "@/lib/server/guards";
import { readInferenceConfig, type InferenceConfig } from "@/lib/server/inference-config";
import { translateInferenceChunks } from "@/lib/server/inference-stream";
import { resolveSession, type ResolvedSession } from "@/lib/server/session";
import { createRequestClient } from "@/lib/server/supabase";

/**
 * `POST /api/assistant/stream`
 *
 * The single authenticated, guarded, audited AI request path. Every branch is
 * exercised by the route-harness test, and every branch writes exactly one
 * audit row. The dependency surface is injected so the test can stub identity,
 * budget and the upstream without a network or a Supabase project; `POST` wires
 * the production implementations.
 */

const FAILED_COPY = "Không thể hoàn tất yêu cầu, vui lòng thử lại sau.";
const UPSTREAM_UNAVAILABLE_COPY = "Mô hình phân tích tạm không khả dụng, vui lòng thử lại sau.";

interface AssistantRequestBody {
  question: string;
  history: readonly AssistantTurn[];
  context: AssistantContext | null;
}

export interface AssistantStreamDeps {
  resolveSession: () => Promise<ResolvedSession>;
  clientFor: (accessToken: string | null) => SupabaseClient;
  consumeBudget: (client: SupabaseClient) => Promise<AiBudgetDecision>;
  recordAudit: (client: SupabaseClient, event: AuditEventInput) => Promise<string | null>;
  readConfig: () => InferenceConfig;
  fetchImpl: typeof fetch;
}

export async function handleAssistantStream(
  req: NextRequest,
  deps: AssistantStreamDeps,
): Promise<Response> {
  const session = await deps.resolveSession();
  const { context } = session;
  const client = deps.clientFor(session.accessToken);

  const guardContext: GuardContext = {
    role: context.role,
    aal: context.aal,
    userId: context.userId,
    origin: req.headers.get("origin"),
    host: req.headers.get("host"),
  };

  // 2. Identity and role, then origin — cheapest and most decisive first.
  const gated = guardRequest({
    context: guardContext,
    action: "analyst.run_ai_request",
    mutating: true,
  });
  if (!gated.allowed) {
    await deps.recordAudit(client, {
      action: "ai.request",
      outcome: "FORBIDDEN",
      contextId: "assistant",
      metadata: { reason: gated.denial.reason },
    });
    return sseResponse(403, [
      { type: "state", state: "policy_blocked", reason: gated.denial.reason },
    ]);
  }

  // Body is parsed after authorization so a forbidden caller cannot probe the
  // handler with arbitrary payloads, but before budget so garbage does not
  // spend the analyst's quota.
  let request: AssistantRequestBody;
  try {
    request = await parseBody(req);
  } catch {
    await deps.recordAudit(client, {
      action: "ai.request",
      outcome: "FAILED",
      contextId: "assistant",
    });
    return sseResponse(400, [{ type: "error", code: "MALFORMED_RESPONSE", reason: FAILED_COPY }]);
  }
  const contextId = request.context === null
    ? "assistant"
    : (request.context.ticker ?? assistantThreadKey(request.context));

  // 3. Atomic budget consumption.
  let decision: AiBudgetDecision;
  try {
    decision = await deps.consumeBudget(client);
  } catch {
    await deps.recordAudit(client, {
      action: "ai.request",
      outcome: "FAILED",
      contextId,
    });
    return sseResponse(500, [
      { type: "error", code: "UPSTREAM_UNAVAILABLE", reason: FAILED_COPY },
    ]);
  }
  if (!decision.ok) {
    const rateLimited = decision.denial === "RATE_LIMITED";
    await deps.recordAudit(client, {
      action: "ai.request",
      outcome: decision.denial,
      contextId,
      metadata: rateLimited ? { rate_remaining: 0 } : { quota_remaining: 0 },
    });
    const frames: AssistantFrame[] = rateLimited
      ? [{ type: "state", state: "policy_blocked", reason: decision.reason }]
      : [
          { type: "quota", remaining: 0, resetsAt: decision.resetsAt },
          { type: "state", state: "policy_blocked", reason: decision.reason },
        ];
    return sseResponse(429, frames);
  }

  // 4. Plane gate: an absent plane is product state, not a client error, so it
  // is a 200 stream of exactly the eks_off state and done frames.
  const config = deps.readConfig();
  if (!context.planeReady || !config.isConfigured) {
    await deps.recordAudit(client, {
      action: "ai.request",
      outcome: "PLANE_OFF",
      contextId,
    });
    return sseResponse(200, [
      { type: "state", state: "eks_off", reason: null },
      { type: "done", agentVersion: null, modelVersion: null },
    ]);
  }

  // 5. Proxy and translate. The upstream request aborts when the client does,
  // and the translator enforces the deadline so a silent upstream cannot hang
  // the route past the hosting limit.
  const upstreamController = new AbortController();
  const onClientAbort = () => upstreamController.abort();
  req.signal.addEventListener("abort", onClientAbort, { once: true });

  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      let outcome: AIAuditOutcome = "ALLOWED";
      const send = (frame: AssistantFrame) =>
        controller.enqueue(encoder.encode(encodeSseFrame(frame)));

      try {
        send({ type: "state", state: "streaming", reason: null });
        const upstreamOrTimeout = await withDeadline(
          deps.fetchImpl(config.url as string, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(config.token === null ? {} : { Authorization: `Bearer ${config.token}` }),
            },
            body: JSON.stringify(upstreamBody(request)),
            signal: upstreamController.signal,
          }),
          config.timeoutMs,
        );
        if (upstreamOrTimeout === "timeout") {
          outcome = "FAILED";
          upstreamController.abort();
          send({ type: "state", state: "timeout", reason: null });
          return;
        }
        const upstream = upstreamOrTimeout;
        if (!upstream.ok || upstream.body === null) {
          outcome = "FAILED";
          send({ type: "error", code: "UPSTREAM_UNAVAILABLE", reason: UPSTREAM_UNAVAILABLE_COPY });
          return;
        }

        const frames = translateInferenceChunks(ssePayloads(upstream.body), {
          timeoutMs: config.timeoutMs,
          signal: upstreamController.signal,
        });
        for await (const frame of frames) {
          send(frame);
          if (frame.type === "error" || (frame.type === "state" && frame.state === "timeout")) {
            outcome = "FAILED";
          }
        }
      } catch {
        outcome = "FAILED";
        if (!upstreamController.signal.aborted) {
          send({ type: "error", code: "UPSTREAM_UNAVAILABLE", reason: UPSTREAM_UNAVAILABLE_COPY });
        }
      } finally {
        req.signal.removeEventListener("abort", onClientAbort);
        if (outcome === "FAILED") upstreamController.abort();
        try {
          await deps.recordAudit(client, { action: "ai.request", outcome, contextId });
        } catch {
          // An audit write failure must not crash an already-answered request.
        }
        controller.close();
      }
    },
  });

  return new Response(stream, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-store",
    },
  });
}

export async function POST(req: NextRequest): Promise<Response> {
  // Fixture mode (evidence/Playwright runs, gated exactly like the session
  // fixture) resolves the budget and audit from the environment instead of
  // Postgres. It is never active in a production deployment because
  // resolveSession fails closed there when fixture mode is requested.
  const fixture = process.env.DISTRESSLENS_DATA_SOURCE === "fixture";
  return handleAssistantStream(req, {
    resolveSession,
    clientFor: fixture ? () => FIXTURE_STUB_CLIENT : createRequestClient,
    consumeBudget: fixture ? (() => fixtureConsumeBudget()) : consumeAiBudget,
    recordAudit: fixture ? (() => fixtureRecordAudit()) : recordAuditEvent,
    readConfig: readInferenceConfig,
    fetchImpl: fetch,
  });
}

const FIXTURE_STUB_CLIENT = {} as unknown as SupabaseClient;

function fixtureConsumeBudget(): Promise<AiBudgetDecision> {
  const raw = process.env.DISTRESSLENS_FIXTURE_QUOTA_LEFT;
  const parsed = raw === undefined ? null : Number.parseInt(raw, 10);
  const remaining = parsed !== null && Number.isFinite(parsed) ? Math.max(0, parsed) : 18;
  const resetsAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
  if (remaining === 0) {
    return Promise.resolve({
      ok: false,
      denial: "QUOTA_EXHAUSTED",
      reason: "Bạn đã dùng hết lượt phân tích AI của kỳ này.",
      resetsAt,
    });
  }
  return Promise.resolve({
    ok: true,
    quotaState: { used: 20 - remaining, limit: 20, resetsAt },
    rateState: { used: 0, limit: 5, resetsAt: new Date(Date.now() + 60_000).toISOString() },
  });
}

function fixtureRecordAudit(): Promise<string | null> {
  return Promise.resolve(null);
}

function sseResponse(status: number, frames: readonly AssistantFrame[]): Response {
  return new Response(frames.map(encodeSseFrame).join(""), {
    status,
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-store" },
  });
}

/**
 * Race a promise against a deadline. An upstream that never flushes its
 * response headers must not hold the route open past the configured timeout:
 * undici does not resolve `fetch` until the peer actually sends bytes, so the
 * translator's per-read deadline below cannot cover the initial handshake.
 */
async function withDeadline<T>(promise: Promise<T>, ms: number): Promise<T | "timeout"> {
  return await new Promise((resolve, reject) => {
    const timer = setTimeout(() => resolve("timeout"), ms);
    Promise.resolve(promise).then(
      (value) => {
        clearTimeout(timer);
        resolve(value);
      },
      (error: unknown) => {
        clearTimeout(timer);
        reject(error);
      },
    );
  });
}

async function parseBody(req: NextRequest): Promise<AssistantRequestBody> {
  const json: unknown = await req.json();
  const body = json as Partial<AssistantRequestBody>;
  const question = typeof body.question === "string" ? body.question.trim() : "";
  if (question === "") {
    throw new Error("empty question");
  }
  return {
    question,
    history: Array.isArray(body.history) ? body.history : [],
    context: body.context && typeof body.context === "object" ? (body.context as AssistantContext) : null,
  };
}

/** The OpenAI-compatible request; only turn text travels upstream. */
function upstreamBody(request: AssistantRequestBody): Record<string, unknown> {
  const messages: readonly { role: "user" | "assistant"; content: string }[] = [
    ...request.history.map((turn) => ({
      role: turn.role === "user" ? ("user" as const) : ("assistant" as const),
      content: turn.body,
    })),
    { role: "user" as const, content: request.question },
  ];
  return { stream: true, messages };
}

/**
 * Split an upstream SSE byte stream into its `data:` payloads. Tolerates `data:
 * [DONE]` sentinels and non-data lines; a read error or abort ends the stream
 * rather than throwing into the translator.
 */
async function* ssePayloads(stream: ReadableStream<Uint8Array>): AsyncGenerator<string> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      let read;
      try {
        read = await reader.read();
      } catch {
        return;
      }
      if (read.done) return;
      buffer += decoder.decode(read.value, { stream: true });
      let newline = buffer.indexOf("\n");
      while (newline !== -1) {
        const line = buffer.slice(0, newline);
        buffer = buffer.slice(newline + 1);
        const trimmed = line.trim();
        if (trimmed.startsWith("data:")) {
          const payload = trimmed.slice("data:".length).trim();
          if (payload !== "" && payload !== "[DONE]") {
            yield payload;
          }
        }
        newline = buffer.indexOf("\n");
      }
    }
  } finally {
    reader.releaseLock();
  }
}