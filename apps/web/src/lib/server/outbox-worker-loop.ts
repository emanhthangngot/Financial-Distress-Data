import "server-only";

/**
 * The pure scheduling core of the outbox worker loop, split out from
 * `scripts/platform/outbox-worker.ts` so the backoff schedule and shutdown
 * ordering are unit-testable without a real Supabase connection.
 */

export interface LoopConfig {
  pollIntervalMs: number;
  backoffBaseMs: number;
  backoffCapMs: number;
}

export const DEFAULT_LOOP_CONFIG: LoopConfig = {
  pollIntervalMs: 3000,
  backoffBaseMs: 1000,
  backoffCapMs: 30000,
};

/** Exponential backoff on claim failure: base, 2x, 4x, ... capped. Never zero. */
export function nextBackoffMs(attempt: number, config: LoopConfig = DEFAULT_LOOP_CONFIG): number {
  const scaled = config.backoffBaseMs * 2 ** Math.max(0, attempt);
  return Math.min(scaled, config.backoffCapMs);
}

/** A full batch means there is more work; an empty one means wait for new events. */
export function nextDelayMs(claimed: number, batchSize: number, config: LoopConfig = DEFAULT_LOOP_CONFIG): number {
  return claimed >= batchSize ? 0 : config.pollIntervalMs;
}

export type ShutdownState = "running" | "draining" | "stopped";

/**
 * Tracks shutdown ordering: a signal sets `draining`, but the in-flight batch
 * still finishes and reports before the loop transitions to `stopped`. A
 * second signal has no further effect — the process exits once, cleanly.
 */
export class ShutdownController {
  private state: ShutdownState = "running";

  requestShutdown(): void {
    if (this.state === "running") {
      this.state = "draining";
    }
  }

  finishBatch(): void {
    if (this.state === "draining") {
      this.state = "stopped";
    }
  }

  get shouldStop(): boolean {
    return this.state !== "running";
  }

  get isStopped(): boolean {
    return this.state === "stopped";
  }
}
