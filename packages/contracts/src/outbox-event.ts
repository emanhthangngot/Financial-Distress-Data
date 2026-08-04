import type { SessionState } from "./session-state";

export const OUTBOX_EVENT_STATUSES = ["PENDING", "CLAIMED", "DONE", "FAILED"] as const;
export type OutboxEventStatus = (typeof OUTBOX_EVENT_STATUSES)[number];

export interface OutboxEvent {
  id: string;
  sessionId: string;
  targetState: SessionState;
  status: OutboxEventStatus;
  claimedBy: string | null;
  claimedAt: string | null;
  leaseExpiry: string | null;
  attempts: number;
  createdAt: string;
}

/**
 * Attempts beyond this are left FAILED for an operator rather than retried
 * forever: a lifecycle action that has failed this often is a real problem, and
 * silent infinite retry against AWS is how a cost cap gets bypassed.
 */
export const MAX_OUTBOX_ATTEMPTS = 5;

export type ClaimDecision =
  | { claimable: true; leaseExpiry: string; attempts: number }
  | { claimable: false; reason: ClaimRejection };

export const CLAIM_REJECTIONS = [
  "NOT_PENDING",
  "LEASE_HELD",
  "ATTEMPTS_EXHAUSTED",
] as const;
export type ClaimRejection = (typeof CLAIM_REJECTIONS)[number];

/**
 * Pure lease decision for the outbox worker. The database `select ... for
 * update skip locked` is what actually makes the claim atomic; this function
 * decides whether a claim is legitimate at all, so the rule is unit-testable
 * without a Postgres round trip.
 *
 * A CLAIMED event whose lease has expired is reclaimable: the previous worker
 * died mid-flight, and leaving the event stranded would wedge the session.
 */
export function decideClaim(
  event: OutboxEvent,
  now: Date,
  leaseDurationMs: number,
): ClaimDecision {
  if (event.status === "DONE") {
    return { claimable: false, reason: "NOT_PENDING" };
  }

  if (event.attempts >= MAX_OUTBOX_ATTEMPTS) {
    return { claimable: false, reason: "ATTEMPTS_EXHAUSTED" };
  }

  if (event.status === "CLAIMED") {
    const leaseHeld =
      event.leaseExpiry !== null && Date.parse(event.leaseExpiry) > now.getTime();
    if (leaseHeld) {
      return { claimable: false, reason: "LEASE_HELD" };
    }
  }

  return {
    claimable: true,
    leaseExpiry: new Date(now.getTime() + leaseDurationMs).toISOString(),
    attempts: event.attempts + 1,
  };
}
