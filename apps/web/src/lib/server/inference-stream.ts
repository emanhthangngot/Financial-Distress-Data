import "server-only";
import type { AssistantFrame, ToolTraceEntry } from "@distresslens/contracts";

/**
 * Upstream chunk -> AssistantFrame translator.
 *
 * Pure and network-free: it consumes an async iterable of raw OpenAI SSE JSON
 * payload strings and yields the typed frames the route streams to the client.
 * Every upstream failure maps to a closed error code; the raw chunk text and
 * any upstream message never cross this module's boundary.
 */

export interface OpenAIChunkLike {
  choices?: readonly (
    | {
        delta?: {
          content?: string | null;
          refusal?: string | null;
          tool_calls?: readonly (
            | { id?: string | null; function?: { name?: string; arguments?: string } | null }
            | null
          )[];
        } | null;
        finish_reason?: string | null;
      }
    | null
  )[];
}

const MALFORMED_COPY = "Định dạng phản hồi không hợp lệ";

/**
 * Translate one raw payload string into frames. A chunk that is not valid JSON
 * produces a single `error` frame; `finished` reports whether the stream should
 * stop after this chunk (error or finish_reason seen).
 */
function translateChunk(
  raw: string,
  seenToolCalls: Set<string>,
  startedAtBase: number,
): { frames: AssistantFrame[]; finished: boolean } {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw) as unknown;
  } catch {
    return { frames: [{ type: "error", code: "MALFORMED_RESPONSE", reason: MALFORMED_COPY }], finished: true };
  }

  const chunk = parsed as OpenAIChunkLike;
  const frames: AssistantFrame[] = [];
  const choices = chunk.choices ?? [];
  let finished = false;

  for (let ci = 0; ci < choices.length; ci += 1) {
    const choice = choices[ci];
    if (choice === null || choice === undefined) continue;

    if (choice.finish_reason !== null && choice.finish_reason !== undefined) {
      frames.push({ type: "done", agentVersion: null, modelVersion: null });
      finished = true;
    }

    const delta = choice.delta;
    if (delta === null || delta === undefined) continue;

    if (typeof delta.content === "string" && delta.content.length > 0) {
      frames.push({ type: "token", text: delta.content });
    }

    if (typeof delta.refusal === "string" && delta.refusal.length > 0) {
      frames.push({ type: "state", state: "policy_blocked", reason: null });
    }

    if (Array.isArray(delta.tool_calls)) {
      for (let ti = 0; ti < delta.tool_calls.length; ti += 1) {
        const call = delta.tool_calls[ti];
        if (call === null || call === undefined) continue;
        // Argument fragments arrive across chunks with the same position and
        // id; only the first fragment yields a tool entry.
        const key = `${ci}:${ti}`;
        if (seenToolCalls.has(key)) continue;
        seenToolCalls.add(key);

        const toolName = call.function?.name ?? "unknown-tool";
        const entry: ToolTraceEntry = {
          id: call.id ?? `tool-${ci}-${ti}`,
          toolName,
          status: "RUNNING",
          summary: `Đang chạy ${toolName}`,
          startedAt: new Date(startedAtBase).toISOString(),
          durationMs: 0,
        };
        frames.push({ type: "tool", entry });
      }
    }
  }

  return { frames, finished };
}

/**
 * Stream translated frames from the upstream iterable, enforcing a deadline
 * that races the next upstream read (so a silent upstream cannot hang the
 * route) and honoring the caller's abort signal by stopping the reader.
 */
export async function* translateInferenceChunks(
  chunks: AsyncIterable<string>,
  opts: { timeoutMs: number; signal: AbortSignal },
): AsyncGenerator<AssistantFrame> {
  const deadline = Date.now() + opts.timeoutMs;
  const seenToolCalls = new Set<string>();
  const iterator = chunks[Symbol.asyncIterator]();

  while (true) {
    if (opts.signal.aborted) return;

    const remaining = deadline - Date.now();
    if (remaining <= 0) {
      yield { type: "state", state: "timeout", reason: null };
      return;
    }

    const next = await raceNext(iterator, remaining);
    if (next === "timeout") {
      yield { type: "state", state: "timeout", reason: null };
      return;
    }
    if (next.done) return;

    const { frames, finished } = translateChunk(next.value as string, seenToolCalls, Date.now());
    for (const frame of frames) {
      yield frame;
    }
    if (finished) return;
  }
}

type RaceResult = { done?: boolean | undefined; value?: unknown } | "timeout";

async function raceNext(
  iterator: AsyncIterator<string>,
  ms: number,
): Promise<RaceResult> {
  return await new Promise((resolve) => {
    const timer = setTimeout(() => resolve("timeout"), ms);
    Promise.resolve(iterator.next()).then(
      (result) => {
        clearTimeout(timer);
        resolve(result);
      },
      () => {
        // An upstream read error is treated as stream end; the route reports
        // it as UPSTREAM_UNAVAILABLE rather than leaking the raw error.
        clearTimeout(timer);
        resolve({ done: true });
      },
    );
  });
}