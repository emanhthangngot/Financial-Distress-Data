import transitions from "./session-transitions.json" with { type: "json" };

export const SESSION_STATES = [
  "OFF",
  "REQUESTED",
  "PROVISIONING",
  "SYNCING",
  "READY",
  "CAPTURING",
  "DESTROYING",
  "FAILED",
  "EXPIRED",
] as const;

export type SessionState = (typeof SESSION_STATES)[number];

export function isSessionState(value: unknown): value is SessionState {
  return typeof value === "string" && (SESSION_STATES as readonly string[]).includes(value);
}

/**
 * The legal state graph. DESTROYING is reachable from every state that can hold
 * live infrastructure, so an operator can always tear down a session wedged
 * mid-provision — the case that otherwise keeps burning cloud spend.
 *
 * Loaded from session-transitions.json, which is also the source the
 * `session_transition_rule` table is seeded from, so the client and the
 * database cannot drift into disagreeing about which transitions are legal.
 * The database remains the authority actually enforced at write time; a test
 * asserts the seeded table matches this file exactly.
 */
export const ALLOWED_TRANSITIONS: Record<SessionState, readonly SessionState[]> =
  transitions as Record<SessionState, readonly SessionState[]>;

export interface EvidenceSession {
  id: string;
  state: SessionState;
  version: number;
  actor: string;
  idempotencyKey: string;
  leaseExpiry: string | null;
  fencingToken: string;
  costSnapshotUsd: number | null;
  gitSha: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface TransitionRequest {
  targetState: SessionState;
  actor: string;
  idempotencyKey: string;
  fencingToken: string;
}

export type TransitionErrorCode =
  | "ILLEGAL_TRANSITION"
  | "STALE_FENCING_TOKEN"
  | "DUPLICATE_IDEMPOTENCY_KEY_CONFLICT";

export class TransitionError extends Error {
  constructor(
    public readonly code: TransitionErrorCode,
    message: string,
  ) {
    super(message);
    this.name = "TransitionError";
  }
}

export interface TransitionResult {
  nextState: SessionState;
  nextVersion: number;
  /** true when this call replayed an already-applied idempotency key (no new transition) */
  replayed: boolean;
}

/**
 * Pure decision function: validates a requested transition against the current
 * session row without touching the database. The caller (outbox writer) is
 * responsible for committing session + outbox rows atomically.
 */
export function decideTransition(
  current: EvidenceSession,
  request: TransitionRequest,
): TransitionResult {
  if (request.idempotencyKey === current.idempotencyKey) {
    if (current.state === request.targetState) {
      return { nextState: current.state, nextVersion: current.version, replayed: true };
    }
    throw new TransitionError(
      "DUPLICATE_IDEMPOTENCY_KEY_CONFLICT",
      `idempotency key ${request.idempotencyKey} was already applied to a different target state`,
    );
  }

  if (current.fencingToken !== request.fencingToken) {
    throw new TransitionError(
      "STALE_FENCING_TOKEN",
      `fencing token mismatch on session ${current.id}: expected ${current.fencingToken}`,
    );
  }

  // `current` crosses a trust boundary (database row / API payload), so the
  // SessionState type is only a compile-time claim. An unrecognised state must
  // deny rather than throw a TypeError on undefined.
  const allowed = ALLOWED_TRANSITIONS[current.state] ?? [];
  if (!allowed.includes(request.targetState)) {
    throw new TransitionError(
      "ILLEGAL_TRANSITION",
      `cannot transition session ${current.id} from ${current.state} to ${request.targetState}`,
    );
  }

  return {
    nextState: request.targetState,
    nextVersion: current.version + 1,
    replayed: false,
  };
}
