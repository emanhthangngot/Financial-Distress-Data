import { describe, expect, it } from "vitest";
import {
  AI_BUDGET_DEFAULTS,
  AI_QUOTA_LIMIT,
  AI_QUOTA_WINDOW_MS,
  AI_RATE_LIMIT,
  AI_RATE_WINDOW_MS,
  resetsAtTime,
  windowStartAt,
} from "./ai-budget";

describe("AI_BUDGET_DEFAULTS", () => {
  it("defaults to 20 requests per 24h quota", () => {
    expect(AI_QUOTA_LIMIT).toBe(20);
    expect(AI_QUOTA_WINDOW_MS).toBe(24 * 60 * 60 * 1000);
  });

  it("defaults to 5 requests per 60s rate limit", () => {
    expect(AI_RATE_LIMIT).toBe(5);
    expect(AI_RATE_WINDOW_MS).toBe(60 * 1000);
  });

  it("exposes one object carrying all four numbers", () => {
    expect(AI_BUDGET_DEFAULTS).toEqual({
      quotaLimit: 20,
      quotaWindowMs: 24 * 60 * 60 * 1000,
      rateLimit: 5,
      rateWindowMs: 60 * 1000,
    });
  });
});

describe("windowStartAt", () => {
  it("maps a time exactly on a window boundary to that boundary", () => {
    const boundary = new Date("2025-05-22T12:00:00.000Z");
    expect(windowStartAt(boundary, 60_000).toISOString()).toBe("2025-05-22T12:00:00.000Z");
  });

  it("floors a time inside a window to the window start", () => {
    const inside = new Date("2025-05-22T12:00:59.999Z");
    expect(windowStartAt(inside, 60_000).toISOString()).toBe("2025-05-22T12:00:00.000Z");
  });

  it("rolls across the boundary for the next window", () => {
    const justAfter = new Date("2025-05-22T12:01:00.001Z");
    expect(windowStartAt(justAfter, 60_000).toISOString()).toBe("2025-05-22T12:01:00.000Z");
  });

  it("buckets a 24h window to UTC midnight", () => {
    const noon = new Date("2025-05-22T12:00:00.000Z");
    expect(windowStartAt(noon, AI_QUOTA_WINDOW_MS).toISOString()).toBe(
      "2025-05-22T00:00:00.000Z",
    );
  });
});

describe("resetsAtTime", () => {
  it("returns the end of the window holding the start", () => {
    const start = new Date("2025-05-22T12:00:00.000Z");
    expect(resetsAtTime(start, 60_000).toISOString()).toBe("2025-05-22T12:01:00.000Z");
  });
});