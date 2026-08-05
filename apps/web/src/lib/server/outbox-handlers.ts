import "server-only";
import type { SessionState } from "@distresslens/contracts";
import type { OutboxEventRow, OutboxHandler } from "./outbox-worker";

/**
 * Outbox handler registry.
 *
 * Dispatches a claimed outbox event to the handler registered for its
 * `target_state`. An event whose target state has no handler is a defect —
 * either a migration added a transition the worker does not know about yet,
 * or a bug wrote the wrong target — so it fails loudly rather than reporting
 * a silent success `drainOutbox` would otherwise record as completed.
 */

export class NoOutboxHandlerError extends Error {
  constructor(targetState: SessionState) {
    super(`no outbox handler registered for target state "${targetState}"`);
    this.name = "NoOutboxHandlerError";
  }
}

export interface OutboxHandlerRegistry {
  register(targetState: SessionState, handler: OutboxHandler): void;
  handle: OutboxHandler;
}

export function createOutboxHandlerRegistry(): OutboxHandlerRegistry {
  const handlers = new Map<SessionState, OutboxHandler>();

  return {
    register(targetState, handler) {
      handlers.set(targetState, handler);
    },
    async handle(event: OutboxEventRow): Promise<string> {
      const handler = handlers.get(event.target_state);
      if (handler === undefined) {
        throw new NoOutboxHandlerError(event.target_state);
      }
      return handler(event);
    },
  };
}

/**
 * The state-advance-only placeholder. It contacts no infrastructure — the
 * GitOps dispatcher that actually drives EKS provisioning/destruction lands
 * in phase-03 of the unified plan (a separate control repo). Until then the
 * outbox event exists only to prove the lease/fencing/dispatch machinery
 * works end to end; the result string says so explicitly so an operator (and
 * the audit row it feeds) never mistakes this for a real provision.
 */
export const noInfrastructureHandler: OutboxHandler = async (event) => {
  return `state-advance-only: no infrastructure contacted (GitOps dispatch lands in parent phase-03); session already in ${event.target_state}`;
};

/**
 * Wires the default registry this worker process runs with today. Every
 * lifecycle target state resolves to the placeholder until the GitOps
 * dispatcher replaces it — the loop, the registry shape and this call site
 * do not change when that happens, only the registered handler body.
 */
export function createDefaultOutboxHandlerRegistry(): OutboxHandlerRegistry {
  const registry = createOutboxHandlerRegistry();
  const targets: SessionState[] = [
    "REQUESTED",
    "PROVISIONING",
    "SYNCING",
    "CAPTURING",
    "DESTROYING",
  ];
  for (const target of targets) {
    registry.register(target, noInfrastructureHandler);
  }
  return registry;
}
