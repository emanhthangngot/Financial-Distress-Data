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
