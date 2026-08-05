import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";
import { decodeSseChunk, type AssistantFrame } from "@distresslens/contracts";
import { handleAssistantStream, type AssistantStreamDeps } from "./route";
import type { AIAuditOutcome, AuditEventInput } from "@/lib/server/ai-budget";

const analystContext = {
  userId: "user-analyst",
  role: "analyst" as const,
  aal: "aal1" as const,
  planeReady: true,
};

const signedOutContext = {
  userId: null,
  role: null,
  aal: "aal1" as const,
  planeReady: true,
};

const AUDITS: AuditEventInput[] = [];

interface Harness {
  deps: AssistantStreamDeps;
  consumeCalls: () => number;
}

function harness(overrides: Partial<AssistantStreamDeps> = {}): Harness {
  const consumeCalls = { count: 0 };
  const deps: AssistantStreamDeps = {
    resolveSession: async () => ({
      context: analystContext,
      user: { displayName: "Analyst", role: "analyst" },
      accessToken: "token",
    }),
    clientFor: () => ({}) as never,
    consumeBudget: async () => {
      consumeCalls.count += 1;
      return {
        ok: true,
        quotaState: { used: 1, limit: 20, resetsAt: "2026-08-06T00:00:00Z" },
        rateState: { used: 1, limit: 5, resetsAt: "2026-08-05T00:01:00Z" },
      };
    },
    recordAudit: async (_, event) => {
      AUDITS.push(event);
      return "audit-id";
    },
    readConfig: () => ({
      url: "https://infer.example.com/v1",
      token: "sk-secret",
      timeoutMs: 55_000,
      isConfigured: true,
    }),
    fetchImpl: async () =>
      new Response(
        streamOf(
          [
            JSON.stringify({ choices: [{ delta: { content: "NVL rủi ro cao" } }] }),
            JSON.stringify({ choices: [{ delta: {}, finish_reason: "stop" }] }),
          ],
          (text) => `data: ${text}\n\n`,
        ),
        { status: 200 },
      ),
    ...overrides,
  };
  return { deps, consumeCalls: () => consumeCalls.count };
}

function streamOf(
  chunks: string[],
  wrap: (text: string) => string,
): ReadableStream<Uint8Array> {
  return new ReadableStream({
    async start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(new TextEncoder().encode(wrap(chunk)));
      }
      controller.close();
    },
  });
}

function request(overrides: Record<string, unknown> = {}): NextRequest {
  return new NextRequest("http://localhost:3000/api/assistant/stream", {
    method: "POST",
    headers: {
      origin: "http://localhost:3000",
      host: "localhost:3000",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      question: "Vì sao NVL có nguy cơ cao?",
      history: [],
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
      ...overrides,
    }),
  });
}

async function readFrames(response: Response): Promise<AssistantFrame[]> {
  const buffer = await new Response(response.body).text();
  const { frames } = decodeSseChunk(buffer);
  return frames;
}

function clearAudits(): void {
  AUDITS.length = 0;
}

describe("assistant stream route", () => {
  it("forbids a signed-out caller before parsing body or consuming budget", async () => {
    clearAudits();
    const { deps, consumeCalls } = harness({
      resolveSession: async () => ({
        context: signedOutContext,
        user: { displayName: "Khách", role: "analyst" },
        accessToken: null,
      }),
    });
    const response = await handleAssistantStream(request(), deps);
    expect(response.status).toBe(403);
    const frames = await readFrames(response);
    expect(frames[0]).toMatchObject({ type: "state", state: "policy_blocked" });
    expect(consumeCalls()).toBe(0);
    expect(AUDITS.map((event) => event.outcome)).toEqual(["FORBIDDEN"]);
  });

  it("refuses a foreign origin before touching budget or upstream", async () => {
    clearAudits();
    const { deps, consumeCalls } = harness();
    const foreign = new NextRequest("http://localhost:3000/api/assistant/stream", {
      method: "POST",
      headers: {
        origin: "https://evil.example",
        host: "localhost:3000",
        "content-type": "application/json",
      },
      body: JSON.stringify({ question: "hi", history: [], context: null }),
    });
    const refused = await handleAssistantStream(foreign, deps);
    expect(refused.status).toBe(403);
    expect(consumeCalls()).toBe(0);
    expect(AUDITS.map((event) => event.outcome)).toEqual(["FORBIDDEN"]);
  });

  it("returns 429 with the reset time when the quota is exhausted", async () => {
    clearAudits();
    const { deps } = harness({
      consumeBudget: async () => ({
        ok: false,
        denial: "QUOTA_EXHAUSTED",
        reason: "Hết hạn mức.",
        resetsAt: "2026-08-06T00:00:00Z",
      }),
    });
    const response = await handleAssistantStream(request(), deps);
    expect(response.status).toBe(429);
    const frames = await readFrames(response);
    expect(frames).toEqual([
      { type: "quota", remaining: 0, resetsAt: "2026-08-06T00:00:00Z" },
      { type: "state", state: "policy_blocked", reason: "Hết hạn mức." },
    ]);
    expect(AUDITS.map((event) => event.outcome)).toEqual(["QUOTA_EXHAUSTED"]);
  });

  it("returns 429 with a state frame when rate limited", async () => {
    clearAudits();
    const { deps } = harness({
      consumeBudget: async () => ({
        ok: false,
        denial: "RATE_LIMITED",
        reason: "Quá nhanh.",
        resetsAt: "2026-08-05T00:01:00Z",
      }),
    });
    const response = await handleAssistantStream(request(), deps);
    expect(response.status).toBe(429);
    const frames = await readFrames(response);
    expect(frames).toEqual([{ type: "state", state: "policy_blocked", reason: "Quá nhanh." }]);
    expect(AUDITS.map((event) => event.outcome)).toEqual(["RATE_LIMITED"]);
  });

  it("returns a 200 eks_off stream when the plane is off", async () => {
    clearAudits();
    const { deps, consumeCalls } = harness({
      resolveSession: async () => ({
        context: { ...analystContext, planeReady: false },
        user: { displayName: "Analyst", role: "analyst" },
        accessToken: "token",
      }),
    });
    const response = await handleAssistantStream(request(), deps);
    expect(response.status).toBe(200);
    const frames = await readFrames(response);
    expect(frames).toEqual([
      { type: "state", state: "eks_off", reason: null },
      { type: "done", agentVersion: null, modelVersion: null },
    ]);
    expect(consumeCalls()).toBe(1);
    expect(AUDITS.map((event) => event.outcome)).toEqual(["PLANE_OFF"]);
  });

  it("returns a 200 eks_off stream when the inference url is unset", async () => {
    clearAudits();
    const { deps } = harness({
      readConfig: () => ({ url: null, token: null, timeoutMs: 55_000, isConfigured: false }),
    });
    const response = await handleAssistantStream(request(), deps);
    expect(response.status).toBe(200);
    const frames = await readFrames(response);
    expect(frames.map((frame) => frame.type)).toEqual(["state", "done"]);
    expect(frames[0]).toMatchObject({ type: "state", state: "eks_off" });
    expect(AUDITS.map((event) => event.outcome)).toEqual(["PLANE_OFF"]);
  });

  it("streams translated frames and audits ALLOWED exactly once", async () => {
    clearAudits();
    const { deps, consumeCalls } = harness();
    const response = await handleAssistantStream(request(), deps);
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("text/event-stream");
    const frames = await readFrames(response);
    expect(frames).toEqual([
      { type: "state", state: "streaming", reason: null },
      { type: "token", text: "NVL rủi ro cao" },
      { type: "done", agentVersion: null, modelVersion: null },
    ]);
    expect(consumeCalls()).toBe(1);
    expect(AUDITS).toHaveLength(1);
    expect(AUDITS[0]).toMatchObject({ action: "ai.request", outcome: "ALLOWED", contextId: "NVL" });
  });

  it("audits FAILED and streams an error frame when the upstream request fails", async () => {
    clearAudits();
    const { deps } = harness({
      fetchImpl: async () => {
        throw new Error("upstream refused");
      },
    });
    const response = await handleAssistantStream(request(), deps);
    expect(response.status).toBe(200);
    const frames = await readFrames(response);
    const error = frames.find((frame) => frame.type === "error");
    expect(error).toMatchObject({ type: "error", code: "UPSTREAM_UNAVAILABLE" });
    expect(error?.type === "error" && error.reason).not.toContain("upstream refused");
    expect(AUDITS.map((event) => event.outcome)).toEqual(["FAILED"]);
  });

  it("streams a timeout state frame when the upstream never flushes its headers", async () => {
    clearAudits();
    const { deps } = harness({
      readConfig: () => ({
        url: "https://infer.example.com/v1",
        token: "sk-secret",
        timeoutMs: 25,
        isConfigured: true,
      }),
      fetchImpl: () => new Promise<Response>(() => {}),
    });
    const response = await handleAssistantStream(request(), deps);
    expect(response.status).toBe(200);
    const frames = await readFrames(response);
    expect(frames).toEqual([
      { type: "state", state: "streaming", reason: null },
      { type: "state", state: "timeout", reason: null },
    ]);
    expect(AUDITS.map((event) => event.outcome)).toEqual(["FAILED"]);
  });

  it("rejects a malformed body with 400 without spending budget", async () => {
    clearAudits();
    const { deps, consumeCalls } = harness();
    const response = await handleAssistantStream(
      new NextRequest("http://localhost:3000/api/assistant/stream", {
        method: "POST",
        headers: {
          origin: "http://localhost:3000",
          host: "localhost:3000",
          "content-type": "application/json",
        },
        body: JSON.stringify({ question: "   ", history: [], context: null }),
      }),
      deps,
    );
    expect(response.status).toBe(400);
    expect(consumeCalls()).toBe(0);
    expect(AUDITS.map((event) => event.outcome)).toEqual(["FAILED"]);
  });

  it("never leaks the upstream url or token into the response", async () => {
    clearAudits();
    const { deps } = harness();
    const response = await handleAssistantStream(request(), deps);
    const text = await new Response(response.body).text();
    expect(text).not.toContain("infer.example.com");
    expect(text).not.toContain("sk-secret");
    expect(AUDITS.map((event) => event.outcome as AIAuditOutcome).join(",")).not.toContain(
      "infer.example.com",
    );
  });
});