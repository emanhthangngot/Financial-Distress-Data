import { afterEach, describe, expect, it } from "vitest";
import { encodeSseFrame, type AssistantFrame, type ToolTraceEntry } from "@distresslens/contracts";
import { StreamingAssistantTransport } from "./streaming-transport";
import type { AssistantRequest } from "./assistant-transport";

const toolEntry: ToolTraceEntry = {
  id: "call_1",
  toolName: "feature-rag-mcp",
  status: "RUNNING",
  summary: "Đang chạy feature-rag-mcp",
  startedAt: "2026-08-05T09:00:00+07:00",
  durationMs: 0,
};

const REQUEST: AssistantRequest = {
  context: {
    scope: "company",
    route: "/companies/NVL",
    surfaceLabel: "NVL",
    ticker: "NVL",
    selectedTickers: [],
    periodLabel: null,
    filters: [],
    dataVersion: "gold-2025-05-22",
    modelVersion: "DL-Score v2.1",
  },
  question: "Vì sao NVL có nguy cơ cao?",
  history: [],
};

function sseBody(frames: readonly AssistantFrame[], splitAt: number | null = null): string {
  const wire = frames.map(encodeSseFrame).join("");
  if (splitAt === null) return wire;
  return wire.slice(0, splitAt) + wire.slice(splitAt);
}

function streamResponse(
  frames: readonly AssistantFrame[],
  splitAt: number | null = null,
  status = 200,
): Response {
  return new Response(
    new ReadableStream({
      async start(controller) {
        controller.enqueue(new TextEncoder().encode(sseBody(frames, splitAt)));
        controller.close();
      },
    }),
    { status },
  );
}

let lastFetch: {
  url: string;
  init: RequestInit;
  signal: AbortSignal;
  respond: (response: Response) => void;
  reject: (error: unknown) => void;
} | null = null;

function mockFetch(): void {
  globalThis.fetch = ((url: string | URL | Request, init?: RequestInit) =>
    new Promise<Response>((resolve, reject) => {
      lastFetch = {
        url: String(url),
        init: init ?? {},
        signal: (init?.signal ?? new AbortController().signal) as AbortSignal,
        respond: resolve,
        reject,
      };
    })) as typeof fetch;
}

afterEach(() => {
  lastFetch = null;
});

describe("StreamingAssistantTransport", () => {
  it("reduces ordered frames into a complete turn", async () => {
    mockFetch();
    const transport = new StreamingAssistantTransport("/api/assistant/stream");
    const promise = transport.send(REQUEST);
    lastFetch?.respond(
      streamResponse([
        { type: "state", state: "streaming", reason: null },
        { type: "token", text: "NVL " },
        { type: "token", text: "rủi ro thanh khoản" },
        { type: "done", agentVersion: "dl-agent-1", modelVersion: "gpt-4o" },
      ]),
    );
    const turn = await promise;
    expect(turn.state).toBe("complete");
    expect(turn.body).toBe("NVL rủi ro thanh khoản");
    expect(turn.agentVersion).toBe("dl-agent-1");
    expect(turn.modelVersion).toBe("gpt-4o");
    expect(turn.nextAction).toBeNull();
  });

  it("accumulates citations and tool entries from typed frames", async () => {
    mockFetch();
    const transport = new StreamingAssistantTransport("/api/assistant/stream");
    const promise = transport.send(REQUEST);
    lastFetch?.respond(
      streamResponse([
        { type: "state", state: "streaming", reason: null },
        { type: "tool", entry: toolEntry },
        {
          type: "citation",
          citation: {
            ordinal: 1,
            sourceId: "src-1",
            title: "BCTC Q2/2025",
            publisher: "HOSE",
            url: null,
          },
        },
        { type: "token", text: "Kết luận" },
        { type: "done", agentVersion: null, modelVersion: null },
      ]),
    );
    const turn = await promise;
    expect(turn.toolTrace).toEqual([toolEntry]);
    expect(turn.citations).toHaveLength(1);
    expect(turn.citations[0]?.sourceId).toBe("src-1");
    expect(turn.body).toBe("Kết luận");
  });

  it("reassembles a frame split across network packets", async () => {
    mockFetch();
    const transport = new StreamingAssistantTransport("/api/assistant/stream");
    const frames: AssistantFrame[] = [
      { type: "state", state: "streaming", reason: null },
      { type: "token", text: "thanh khoản" },
      { type: "done", agentVersion: null, modelVersion: null },
    ];
    const promise = transport.send(REQUEST);
    const wire = frames.map(encodeSseFrame).join("");
    const splitAt = Math.floor(wire.length / 2);
    const a = wire.slice(0, splitAt);
    const b = wire.slice(splitAt);
    lastFetch?.respond(
      new Response(
        new ReadableStream({
          async start(controller) {
            controller.enqueue(new TextEncoder().encode(a));
            await new Promise((resolve) => setTimeout(resolve, 10));
            controller.enqueue(new TextEncoder().encode(b));
            controller.close();
          },
        }),
        { status: 200 },
      ),
    );
    const turn = await promise;
    expect(turn.state).toBe("complete");
    expect(turn.body).toBe("thanh khoản");
  });

  it("maps a 429 to the quota copy with a reset time", async () => {
    mockFetch();
    const transport = new StreamingAssistantTransport("/api/assistant/stream");
    const promise = transport.send(REQUEST);
    lastFetch?.respond(
      streamResponse(
        [
          { type: "quota", remaining: 0, resetsAt: "2026-08-06T00:00:00Z" },
          { type: "state", state: "policy_blocked", reason: "Bạn đã dùng hết 20 lượt." },
        ],
        null,
        429,
      ),
    );
    const turn = await promise;
    expect(turn.state).toBe("policy_blocked");
    expect(turn.body).toBe("Bạn đã dùng hết 20 lượt.");
    expect(turn.nextAction).toContain("Hạn mức được đặt lại");
  });

  it("maps a 403 to a policy_blocked turn", async () => {
    mockFetch();
    const transport = new StreamingAssistantTransport("/api/assistant/stream");
    const promise = transport.send(REQUEST);
    lastFetch?.respond(
      streamResponse(
        [{ type: "state", state: "policy_blocked", reason: "Không có quyền." }],
        null,
        403,
      ),
    );
    const turn = await promise;
    expect(turn.state).toBe("policy_blocked");
    expect(turn.body).toBe("Không có quyền.");
  });

  it("renders the eks_off state as the unavailable turn", async () => {
    mockFetch();
    const transport = new StreamingAssistantTransport("/api/assistant/stream");
    const promise = transport.send(REQUEST);
    lastFetch?.respond(
      streamResponse([
        { type: "state", state: "eks_off", reason: null },
        { type: "done", agentVersion: null, modelVersion: null },
      ]),
    );
    const turn = await promise;
    expect(turn.state).toBe("unavailable");
    expect(turn.body).toContain("phân tích AI trực tiếp tạm chưa bật");
    expect(turn.nextAction).toContain("Xem số liệu");
  });

  it("aborting mid-stream aborts the upstream request", async () => {
    mockFetch();
    const transport = new StreamingAssistantTransport("/api/assistant/stream");
    const promise = transport.send(REQUEST);
    const signal = lastFetch?.signal;
    // A stream that never finishes: abort() must cancel the fetch signal.
    lastFetch?.respond(
      new Response(
        new ReadableStream({
          start() {
            signal?.addEventListener("abort", () => undefined);
          },
        }),
        { status: 200 },
      ),
    );
    transport.abort();
    const turn = await promise;
    expect(signal?.aborted).toBe(true);
    expect(turn.state).toBe("timeout");
  });

  it("never sends a credential in the request body", async () => {
    mockFetch();
    const transport = new StreamingAssistantTransport("/api/assistant/stream");
    const promise = transport.send(REQUEST);
    const body = lastFetch?.init.body;
    expect(String(body)).toContain("Vì sao NVL có nguy cơ cao?");
    expect(String(body)).not.toMatch(/sk-[a-z0-9]|bearer|api[_-]?key|token/i);
    lastFetch?.respond(
      streamResponse([
        { type: "state", state: "streaming", reason: null },
        { type: "done", agentVersion: null, modelVersion: null },
      ]),
    );
    await promise;
  });

  it("returns an error turn when the route cannot be reached", async () => {
    mockFetch();
    const transport = new StreamingAssistantTransport("/api/assistant/stream");
    const promise = transport.send(REQUEST);
    lastFetch?.reject(new TypeError("Failed to fetch"));
    const turn = await promise;
    expect(turn.state).toBe("error");
    expect(turn.body).toContain("Không gửi được");
  });
});