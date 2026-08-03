import { describe, expect, it } from "vitest";
import {
  ALLOWED_TRANSITIONS,
  decideTransition,
  isSessionState,
  SESSION_STATES,
  TransitionError,
  type EvidenceSession,
} from "./session-state";

function baseSession(overrides: Partial<EvidenceSession> = {}): EvidenceSession {
  return {
    id: "session-1",
    state: "OFF",
    version: 1,
    actor: "platform_operator:alice",
    idempotencyKey: "idem-0",
    leaseExpiry: null,
    fencingToken: "fence-1",
    costSnapshotUsd: null,
    gitSha: null,
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("decideTransition", () => {
  it("allows OFF -> REQUESTED with a valid fencing token", () => {
    const session = baseSession();
    const result = decideTransition(session, {
      targetState: "REQUESTED",
      actor: "platform_operator:alice",
      idempotencyKey: "idem-1",
      fencingToken: "fence-1",
    });
    expect(result).toEqual({ nextState: "REQUESTED", nextVersion: 2, replayed: false });
  });

  it("rejects an illegal transition (OFF -> READY)", () => {
    const session = baseSession();
    expect(() =>
      decideTransition(session, {
        targetState: "READY",
        actor: "platform_operator:alice",
        idempotencyKey: "idem-1",
        fencingToken: "fence-1",
      }),
    ).toThrow(TransitionError);
  });

  it("rejects a stale fencing token", () => {
    const session = baseSession();
    expect(() =>
      decideTransition(session, {
        targetState: "REQUESTED",
        actor: "platform_operator:alice",
        idempotencyKey: "idem-1",
        fencingToken: "stale-token",
      }),
    ).toThrow(/fencing token mismatch/);
  });

  it("replays a retried idempotency key already applied, producing one transition total", () => {
    const requested = baseSession({
      state: "REQUESTED",
      version: 2,
      idempotencyKey: "idem-1",
    });
    const result = decideTransition(requested, {
      targetState: "REQUESTED",
      actor: "platform_operator:alice",
      idempotencyKey: "idem-1",
      fencingToken: "fence-1",
    });
    expect(result.replayed).toBe(true);
    expect(result.nextVersion).toBe(2);
  });

  it("allows FAILED -> REQUESTED retry", () => {
    const failed = baseSession({ state: "FAILED", version: 3 });
    const result = decideTransition(failed, {
      targetState: "REQUESTED",
      actor: "platform_operator:alice",
      idempotencyKey: "idem-retry",
      fencingToken: "fence-1",
    });
    expect(result.nextState).toBe("REQUESTED");
  });

  it("allows DESTROYING from a wedged mid-provision state (PROVISIONING)", () => {
    const provisioning = baseSession({ state: "PROVISIONING", version: 2 });
    const result = decideTransition(provisioning, {
      targetState: "DESTROYING",
      actor: "platform_operator:alice",
      idempotencyKey: "idem-teardown",
      fencingToken: "fence-1",
    });
    expect(result.nextState).toBe("DESTROYING");
  });

  it("rejects an idempotency key reused against a different target state", () => {
    const requested = baseSession({ state: "REQUESTED", version: 2, idempotencyKey: "idem-1" });
    expect(() =>
      decideTransition(requested, {
        targetState: "DESTROYING",
        actor: "platform_operator:alice",
        idempotencyKey: "idem-1",
        fencingToken: "fence-1",
      }),
    ).toThrow(/already applied to a different target state/);
  });
});

describe("ALLOWED_TRANSITIONS", () => {
  // The graph is loaded from JSON via a type assertion, which would happily
  // accept a file missing a state key; only a runtime check catches that.
  it("declares an entry for every session state, with only known targets", () => {
    for (const state of SESSION_STATES) {
      const targets = ALLOWED_TRANSITIONS[state];
      expect(targets, `missing transitions for ${state}`).toBeDefined();
      for (const target of targets) {
        expect(isSessionState(target), `${state} -> ${target} is not a session state`).toBe(true);
      }
    }
  });

  it("keeps DESTROYING reachable from every state that can hold live infrastructure", () => {
    for (const state of ["REQUESTED", "PROVISIONING", "SYNCING", "READY", "CAPTURING"] as const) {
      expect(ALLOWED_TRANSITIONS[state], `${state} cannot be destroyed`).toContain("DESTROYING");
    }
  });
});
