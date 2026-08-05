import { describe, expect, it } from "vitest";
import type { AssistantFrame } from "@distresslens/contracts";
import { translateInferenceChunks } from "./inference-stream";

async function collect(
  chunks: AsyncIterable<string>,
  opts: { timeoutMs: number; signal: AbortSignal },
): Promise<AssistantFrame[]> {
  const frames: AssistantFrame[] = [];
  for await (const frame of translateInferenceChunks(chunks, opts)) {
    frames.push(frame);
  }
  return frames;
}

function controller(): { signal: AbortSignal; abort: () => void } {
  const c = new AbortController();
  return { signal: c.signal, abort: () => c.abort() };
}

const tokenChunk = (text: string) =>
  JSON.stringify({ choices: [{ delta: { content: text } }] });

describe("translateInferenceChunks", () => {
  it("passes token content through in order", async () => {
    const c = controller();
    const frames = await collect(
      (async function* () {
        yield tokenChunk("NVL ");
        yield tokenChunk("rủi ro ");
        yield tokenChunk("thanh khoản");
      })(),
      { timeoutMs: 5_000, signal: c.signal },
    );
    expect(frames).toEqual([
      { type: "token", text: "NVL " },
      { type: "token", text: "rủi ro " },
      { type: "token", text: "thanh khoản" },
    ]);
  });

  it("translates a tool-call start into a RUNNING ToolTraceEntry", async () => {
    const c = controller();
    const frames = await collect(
      (async function* () {
        yield JSON.stringify({
          choices: [
            {
              delta: {
                tool_calls: [
                  { id: "call_1", function: { name: "feature-rag-mcp", arguments: "" } },
                ],
              },
            },
          ],
        });
      })(),
      { timeoutMs: 5_000, signal: c.signal },
    );
    expect(frames).toHaveLength(1);
    const frame = frames[0];
    if (frame.type !== "tool") throw new Error("expected tool frame");
    expect(frame.entry.id).toBe("call_1");
    expect(frame.entry.toolName).toBe("feature-rag-mcp");
    expect(frame.entry.status).toBe("RUNNING");
  });

  it("does not re-emit the same tool call across argument fragments", async () => {
    const c = controller();
    const frames = await collect(
      (async function* () {
        yield JSON.stringify({
          choices: [{ delta: { tool_calls: [{ id: "call_1", function: { name: "rag" } }] } }],
        });
        yield JSON.stringify({
          choices: [{ delta: { tool_calls: [{ id: "call_1", function: { arguments: "{\"q\":" } }] } }],
        });
        yield JSON.stringify({
          choices: [{ delta: { tool_calls: [{ id: "call_1", function: { arguments: "\"NVL\"}" } }] } }],
        });
      })(),
      { timeoutMs: 5_000, signal: c.signal },
    );
    const tools = frames.filter((frame) => frame.type === "tool");
    expect(tools).toHaveLength(1);
  });

  it("maps an upstream refusal to the policy_blocked state", async () => {
    const c = controller();
    const frames = await collect(
      (async function* () {
        yield JSON.stringify({
          choices: [{ delta: { refusal: "Tôi không trả lời câu hỏi này." } }],
        });
      })(),
      { timeoutMs: 5_000, signal: c.signal },
    );
    expect(frames[0]).toEqual({ type: "state", state: "policy_blocked", reason: null });
  });

  it("emits done when the finish_reason arrives", async () => {
    const c = controller();
    const frames = await collect(
      (async function* () {
        yield tokenChunk("xong");
        yield JSON.stringify({ choices: [{ delta: {}, finish_reason: "stop" }] });
      })(),
      { timeoutMs: 5_000, signal: c.signal },
    );
    expect(frames.at(-1)).toEqual({ type: "done", agentVersion: null, modelVersion: null });
  });

  it("yields a MALFORMED_RESPONSE error without leaking the raw chunk", async () => {
    const c = controller();
    const raw = `{"choices":[{"delta":{"content":"boom`; // deliberately broken JSON
    const frames = await collect(
      (async function* () {
        yield raw;
      })(),
      { timeoutMs: 5_000, signal: c.signal },
    );
    const error = frames[0];
    if (error.type !== "error") throw new Error("expected error frame");
    expect(error.code).toBe("MALFORMED_RESPONSE");
    expect(error.reason).not.toContain("boom");
  });

  it("emits a timeout state and closes when the deadline passes", async () => {
    const c = controller();
    const frames = await collect(
      (async function* () {
        yield tokenChunk("trước");
        await new Promise((resolve) => setTimeout(resolve, 120));
      })(),
      { timeoutMs: 40, signal: c.signal },
    );
    expect(frames).toEqual([
      { type: "token", text: "trước" },
      { type: "state", state: "timeout", reason: null },
    ]);
  });

  it("stops reading upstream when the signal aborts", async () => {
    const c = controller();
    let yielded = 0;
    const source = (async function* () {
      while (true) {
        yielded += 1;
        yield tokenChunk("x");
        await new Promise((resolve) => setTimeout(resolve, 10));
      }
    })();

    const frames: AssistantFrame[] = [];
    for await (const frame of translateInferenceChunks(source, { timeoutMs: 5_000, signal: c.signal })) {
      frames.push(frame);
      if (frames.length === 2) c.abort();
    }
    const beforeAbort = yielded;
    await new Promise((resolve) => setTimeout(resolve, 30));
    expect(yielded).toBe(beforeAbort);
  });
});