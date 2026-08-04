import { describe, expect, it } from "vitest";
import { MAX_OUTBOX_ATTEMPTS, decideClaim, type OutboxEvent } from "./outbox-event";

const NOW = new Date("2025-05-22T10:00:00Z");
const LEASE_MS = 60_000;

const pending: OutboxEvent = {
  id: "evt-1",
  sessionId: "ev-20250522-1000",
  targetState: "PROVISIONING",
  status: "PENDING",
  claimedBy: null,
  claimedAt: null,
  leaseExpiry: null,
  attempts: 0,
  createdAt: "2025-05-22T09:59:00Z",
};

describe("decideClaim", () => {
  it("claims a pending event and issues a lease", () => {
    const decision = decideClaim(pending, NOW, LEASE_MS);
    expect(decision).toEqual({
      claimable: true,
      leaseExpiry: "2025-05-22T10:01:00.000Z",
      attempts: 1,
    });
  });

  it("refuses an event whose lease another worker still holds", () => {
    const held: OutboxEvent = {
      ...pending,
      status: "CLAIMED",
      claimedBy: "worker-a",
      claimedAt: "2025-05-22T09:59:30Z",
      leaseExpiry: "2025-05-22T10:00:30Z",
      attempts: 1,
    };
    expect(decideClaim(held, NOW, LEASE_MS)).toEqual({
      claimable: false,
      reason: "LEASE_HELD",
    });
  });

  it("reclaims an event whose worker died and let the lease expire", () => {
    const expired: OutboxEvent = {
      ...pending,
      status: "CLAIMED",
      claimedBy: "worker-a",
      claimedAt: "2025-05-22T09:58:00Z",
      leaseExpiry: "2025-05-22T09:59:00Z",
      attempts: 1,
    };
    const decision = decideClaim(expired, NOW, LEASE_MS);
    expect(decision.claimable).toBe(true);
    expect(decision.claimable === true && decision.attempts).toBe(2);
  });

  it("retries a failed event so a transient AWS error is not terminal", () => {
    expect(decideClaim({ ...pending, status: "FAILED", attempts: 2 }, NOW, LEASE_MS).claimable).toBe(
      true,
    );
  });

  it("never re-runs a completed event", () => {
    expect(decideClaim({ ...pending, status: "DONE" }, NOW, LEASE_MS)).toEqual({
      claimable: false,
      reason: "NOT_PENDING",
    });
  });

  it("stops retrying at the attempt ceiling instead of looping against AWS", () => {
    const exhausted = { ...pending, status: "FAILED" as const, attempts: MAX_OUTBOX_ATTEMPTS };
    expect(decideClaim(exhausted, NOW, LEASE_MS)).toEqual({
      claimable: false,
      reason: "ATTEMPTS_EXHAUSTED",
    });
  });
});
