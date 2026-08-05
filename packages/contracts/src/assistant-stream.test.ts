import { describe, expect, it } from "vitest";
import type { ToolTraceEntry } from "./agent";
import {
  ASSISTANT_ERROR_CODES,
  decodeSseChunk,
  encodeSseFrame,
  isAssistantFrame,
  type AssistantFrame,
} from "./assistant-stream";

const toolEntry: ToolTraceEntry = {
  id: "tool-1",
  toolName: "feature-rag-mcp",
  status: "SUCCEEDED",
  summary: "Truy xuất 3 hồ sơ",
  startedAt: "2026-08-05T09:00:00+07:00",
  durationMs: 812,
};

const frames: AssistantFrame[] = [
  { type: "state", state: "streaming", reason: null },
  { type: "token", text: "NVL" },
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
  { type: "quota", remaining: 18, resetsAt: "2026-08-06T00:00:00Z" },
  { type: "done", agentVersion: "dl-agent-1", modelVersion: "gpt-4o" },
  { type: "error", code: "MALFORMED_RESPONSE", reason: "Định dạng phản hồi không hợp lệ" },
  { type: "state", state: "eks_off", reason: "Plane offline" },
];

describe("encodeSseFrame", () => {
  it("serializes every frame kind as a single data: event", () => {
    for (const frame of frames) {
      const line = encodeSseFrame(frame);
      expect(line.startsWith("data: ")).toBe(true);
      expect(line.endsWith("\n\n")).toBe(true);
      const payload = JSON.parse(line.slice("data: ".length));
      expect(payload.type).toBe(frame.type);
      expect(JSON.stringify(payload)).toBe(JSON.stringify(frame));
    }
  });
});

describe("decodeSseChunk round-trip", () => {
  it("round-trips every frame kind through the codec", () => {
    const { frames: decoded, rest } = decodeSseChunk(frames.map(encodeSseFrame).join(""));
    expect(rest).toBe("");
    expect(decoded).toEqual(frames);
  });

  it("reassembles a frame split across two packet boundaries", () => {
    const wire = encodeSseFrame({ type: "token", text: "rủi ro thanh khoản" });
    const splitAt = wire.indexOf("thanh");
    const first = wire.slice(0, splitAt);
    const second = wire.slice(splitAt);

    const a = decodeSseChunk(first);
    expect(a.frames).toEqual([]);
    expect(a.rest).not.toBe("");

    const b = decodeSseChunk(a.rest + second);
    expect(b.frames).toEqual([{ type: "token", text: "rủi ro thanh khoản" }]);
    expect(b.rest).toBe("");
  });

  it("assembles multiple frames arriving in one buffer", () => {
    const wire = encodeSseFrame({ type: "state", state: "streaming", reason: null }) +
      encodeSseFrame({ type: "done", agentVersion: null, modelVersion: null });
    const { frames: decoded, rest } = decodeSseChunk(wire);
    expect(decoded).toHaveLength(2);
    expect(rest).toBe("");
  });
});

describe("decodeSseChunk tolerance", () => {
  it("ignores an unknown frame type instead of failing", () => {
    const { frames, rest } = decodeSseChunk(
      `data: ${JSON.stringify({ type: "future_frame", foo: 1 })}\n\n`,
    );
    expect(frames).toEqual([]);
    expect(rest).toBe("");
  });

  it("skips malformed JSON in a data: line without throwing", () => {
    const { frames, rest } = decodeSseChunk(
      "data: {not json\n\ndata: {\"type\":\"token\",\"text\":\"ok\"}\n\n",
    );
    expect(frames).toEqual([{ type: "token", text: "ok" }]);
    expect(rest).toBe("");
  });

  it("ignores blank lines, comments and non-data lines", () => {
    const { frames, rest } = decodeSseChunk(
      "\n: comment line\nid: 42\n\ndata: {\"type\":\"quota\",\"remaining\":18,\"resetsAt\":\"x\"}\n\n",
    );
    expect(frames).toEqual([{ type: "quota", remaining: 18, resetsAt: "x" }]);
    expect(rest).toBe("");
  });

  it("keeps a trailing line without a newline as rest", () => {
    const { frames, rest } = decodeSseChunk("data: {\"type\":\"tool\",");
    expect(frames).toEqual([]);
    expect(rest).toBe("data: {\"type\":\"tool\",");
  });
});

describe("isAssistantFrame", () => {
  it("accepts every documented frame type", () => {
    for (const frame of frames) expect(isAssistantFrame(frame)).toBe(true);
  });

  it("rejects non-objects and unknown types", () => {
    expect(isAssistantFrame(null)).toBe(false);
    expect(isAssistantFrame("data")).toBe(false);
    expect(isAssistantFrame({ type: "nope" })).toBe(false);
  });
});

describe("ASSISTANT_ERROR_CODES", () => {
  it("exposes the closed set of upstream error codes", () => {
    expect(ASSISTANT_ERROR_CODES).toEqual([
      "UPSTREAM_UNAVAILABLE",
      "UPSTREAM_TIMEOUT",
      "MALFORMED_RESPONSE",
      "UPSTREAM_REFUSED",
      "ABORTED",
    ]);
  });
});