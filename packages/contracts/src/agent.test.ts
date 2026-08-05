import { describe, expect, it } from "vitest";
import { AGENT_MESSAGE_STATES, isQuotaExhausted, quotaRemaining, type QuotaState } from "./agent";

describe("quotaRemaining", () => {
  it("returns the unused budget", () => {
    const quota: QuotaState = { used: 3, limit: 20, resetsAt: "2026-08-06T00:00:00Z" };
    expect(quotaRemaining(quota)).toBe(17);
  });

  it("never goes negative when usage exceeds the limit", () => {
    const quota: QuotaState = { used: 25, limit: 20, resetsAt: "2026-08-06T00:00:00Z" };
    expect(quotaRemaining(quota)).toBe(0);
  });
});

describe("isQuotaExhausted", () => {
  it("is false while budget remains", () => {
    expect(isQuotaExhausted({ used: 1, limit: 20, resetsAt: "x" })).toBe(false);
  });

  it("is true exactly at the limit", () => {
    expect(isQuotaExhausted({ used: 20, limit: 20, resetsAt: "x" })).toBe(true);
  });
});

describe("AGENT_MESSAGE_STATES", () => {
  it("carries the closed set of message states a turn can be in", () => {
    expect([...AGENT_MESSAGE_STATES]).toEqual([
      "complete",
      "streaming",
      "tool_running",
      "timeout",
      "policy_blocked",
      "error",
    ]);
  });
});
