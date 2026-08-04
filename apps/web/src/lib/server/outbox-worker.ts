import "server-only";
import type { SupabaseClient } from "@supabase/supabase-js";
import type { SessionState } from "@distresslens/contracts";

/**
 * The outbox worker.
 *
 * A Vercel request cannot babysit a ten-minute AWS provision, so the request
 * writes an intent and returns; this worker does the slow half out of band. It
 * runs as a separate process against the service-role client and never inside a
 * request handler.
 *
 * Its guarantees come from the database functions it calls, not from this file:
 * `claim_outbox_events` hands out leases with `skip locked`, so two workers take
 * different rows and a crashed worker's rows return to the pool when its lease
 * expires. `complete_outbox_event` refuses a stale fencing token, so a worker
 * that stalled through someone else's transition cannot report success for work
 * the session has already moved past.
 */

export interface OutboxEventRow {
  id: string;
  session_id: string;
  target_state: SessionState;
  attempts: number;
  fencing_token: string | null;
}

/** What the worker does with one claimed event. */
export type OutboxHandler = (event: OutboxEventRow) => Promise<string>;

export interface WorkerOptions {
  workerId: string;
  batchSize?: number;
  /** How long a claim is held before another worker may take the event. */
  leaseSeconds?: number;
  maxAttempts?: number;
}

export interface DrainResult {
  claimed: number;
  completed: number;
  failed: number;
  /** Events rejected because the session advanced past them. */
  fenced: number;
}

export async function drainOutbox(
  client: SupabaseClient,
  handle: OutboxHandler,
  options: WorkerOptions,
): Promise<DrainResult> {
  const { workerId, batchSize = 5, leaseSeconds = 120, maxAttempts = 5 } = options;

  const { data, error } = await client.rpc("claim_outbox_events", {
    p_worker_id: workerId,
    p_limit: batchSize,
    p_lease_seconds: leaseSeconds,
  });

  if (error !== null) {
    throw new Error(`could not claim outbox events: ${error.message}`);
  }

  const events = (data ?? []) as OutboxEventRow[];
  const result: DrainResult = { claimed: events.length, completed: 0, failed: 0, fenced: 0 };

  for (const event of events) {
    try {
      const outcome = await handle(event);
      const completion = await client.rpc("complete_outbox_event", {
        p_event_id: event.id,
        p_worker_id: workerId,
        p_result: outcome,
      });

      if (completion.error !== null) {
        // A stale fencing token is not a worker failure — the database already
        // marked the event FAILED, and retrying would be wrong.
        if (isStaleFencing(completion.error.message)) {
          result.fenced += 1;
          continue;
        }
        throw new Error(completion.error.message);
      }

      result.completed += 1;
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : String(cause);
      const failure = await client.rpc("fail_outbox_event", {
        p_event_id: event.id,
        p_worker_id: workerId,
        // The message reaches an audit row, so it must stay free of anything
        // secret-bearing; handlers are responsible for redacting before throwing.
        p_error: message.slice(0, 500),
        p_max_attempts: maxAttempts,
      });

      if (failure.error !== null && !isStaleFencing(failure.error.message)) {
        throw new Error(`could not record outbox failure: ${failure.error.message}`);
      }

      result.failed += 1;
    }
  }

  return result;
}

function isStaleFencing(message: string): boolean {
  return message.includes("stale fencing token");
}
