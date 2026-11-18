/**
 * Outbox worker entrypoint.
 *
 * Runs `drainOutbox` in a loop against the service-role Supabase client. Must
 * never run inside a request handler — it holds the service-role key, which
 * bypasses RLS. Run locally with `pnpm --filter @distresslens/web
 * outbox:worker`; the same command is the container entrypoint later, with no
 * code change.
 */
import { hostname } from "node:os";
import { createServiceClient } from "@/lib/server/supabase";
import { drainOutbox } from "@/lib/server/outbox-worker";
import { createDefaultOutboxHandlerRegistry } from "@/lib/server/outbox-handlers";
import { DEFAULT_LOOP_CONFIG, ShutdownController, nextBackoffMs, nextDelayMs } from "@/lib/server/outbox-worker-loop";

const REQUIRED_ENV = ["NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"] as const;

function assertEnv(): void {
  const missing = REQUIRED_ENV.filter((name) => (process.env[name] ?? "").trim() === "");
  if (missing.length > 0) {
    console.error(`outbox worker: missing required env var(s): ${missing.join(", ")}`);
    process.exit(1);
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function log(fields: Record<string, unknown>): void {
  console.log(JSON.stringify({ ts: new Date().toISOString(), ...fields }));
}

async function main(): Promise<void> {
  assertEnv();

  const client = createServiceClient();
  const registry = createDefaultOutboxHandlerRegistry();
  const workerId = `${hostname()}-${process.pid}`;
  const controller = new ShutdownController();

  process.on("SIGTERM", () => controller.requestShutdown());
  process.on("SIGINT", () => controller.requestShutdown());

  log({ event: "worker_start", workerId });

  let failureAttempt = 0;

  while (!controller.shouldStop) {
    try {
      const result = await drainOutbox(client, registry.handle, { workerId });
      failureAttempt = 0;

      log({
        event: "drain_result",
        workerId,
        claimed: result.claimed,
        completed: result.completed,
        failed: result.failed,
        fenced: result.fenced,
      });

      if (controller.shouldStop) {
        break;
      }

      const delay = nextDelayMs(result.claimed, 5, DEFAULT_LOOP_CONFIG);
      if (delay > 0) {
        await sleep(delay);
      }
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : String(cause);
      log({ event: "claim_error", workerId, attempt: failureAttempt, error: message });

      const backoff = nextBackoffMs(failureAttempt, DEFAULT_LOOP_CONFIG);
      failureAttempt += 1;
      await sleep(backoff);
    }
  }

  controller.finishBatch();
  log({ event: "worker_stop", workerId });
  process.exit(0);
}

main().catch((cause) => {
  console.error("outbox worker: fatal error", cause instanceof Error ? cause.message : cause);
  process.exit(1);
});
