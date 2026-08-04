import { describe, expect, it, vi } from "vitest";
import type { SupabaseClient } from "@supabase/supabase-js";
import { drainOutbox, type OutboxEventRow } from "./outbox-worker";

/**
 * The worker is tested against a stub of the RPC surface rather than a live
 * database. What is proved here is the worker's own behavior: that it completes
 * what succeeds, records what fails, and does not retry an event the session
 * has advanced past. The database functions themselves are proved by the SQL
 * migration and the RLS suite.
 */

interface RpcCall {
  name: string;
  args: Record<string, unknown>;
}

function stubClient(
  events: OutboxEventRow[],
  overrides: Record<string, { data?: unknown; error?: { message: string } | null }> = {},
): { client: SupabaseClient; calls: RpcCall[] } {
  const calls: RpcCall[] = [];

  const client = {
    rpc: vi.fn(async (name: string, args: Record<string, unknown>) => {
      calls.push({ name, args });
      if (name === "claim_outbox_events") {
        return { data: events, error: null };
      }
      const override = overrides[name];
      return { data: override?.data ?? null, error: override?.error ?? null };
    }),
  } as unknown as SupabaseClient;

  return { client, calls };
}

const event: OutboxEventRow = {
  id: "evt-1",
  session_id: "sess-1",
  target_state: "PROVISIONING",
  attempts: 1,
  fencing_token: "token-1",
};

describe("outbox worker", () => {
  it("completes an event whose handler succeeds", async () => {
    const { client, calls } = stubClient([event]);
    const result = await drainOutbox(client, async () => "provisioned", { workerId: "w1" });

    expect(result).toEqual({ claimed: 1, completed: 1, failed: 0, fenced: 0 });
    expect(calls.map((call) => call.name)).toEqual([
      "claim_outbox_events",
      "complete_outbox_event",
    ]);
    expect(calls[1]?.args.p_worker_id).toBe("w1");
  });

  it("records a handler failure for retry instead of losing the event", async () => {
    const { client, calls } = stubClient([event]);
    const result = await drainOutbox(
      client,
      async () => {
        throw new Error("AWS API timed out");
      },
      { workerId: "w1" },
    );

    expect(result.failed).toBe(1);
    expect(result.completed).toBe(0);
    const failure = calls.find((call) => call.name === "fail_outbox_event");
    expect(failure?.args.p_error).toContain("AWS API timed out");
  });

  it("does not retry an event the session has advanced past", async () => {
    // The database already marked the event FAILED when it rejected the stale
    // token; retrying would re-run infrastructure work for a state nobody wants.
    const { client, calls } = stubClient([event], {
      complete_outbox_event: { error: { message: "stale fencing token for outbox event evt-1" } },
    });

    const result = await drainOutbox(client, async () => "provisioned", { workerId: "w1" });

    expect(result).toEqual({ claimed: 1, completed: 0, failed: 0, fenced: 1 });
    expect(calls.some((call) => call.name === "fail_outbox_event")).toBe(false);
  });

  it("passes the lease and batch size the caller asked for", async () => {
    const { client, calls } = stubClient([]);
    await drainOutbox(client, async () => "noop", {
      workerId: "w2",
      batchSize: 3,
      leaseSeconds: 30,
    });

    expect(calls[0]?.args).toMatchObject({
      p_worker_id: "w2",
      p_limit: 3,
      p_lease_seconds: 30,
    });
  });

  it("keeps processing the rest of the batch after one event fails", async () => {
    const second: OutboxEventRow = { ...event, id: "evt-2" };
    const { client } = stubClient([event, second]);
    let call = 0;

    const result = await drainOutbox(
      client,
      async () => {
        call += 1;
        if (call === 1) {
          throw new Error("transient");
        }
        return "provisioned";
      },
      { workerId: "w1" },
    );

    expect(result.failed).toBe(1);
    expect(result.completed).toBe(1);
  });

  it("surfaces a claim failure rather than reporting an empty drain", async () => {
    const client = {
      rpc: vi.fn(async () => ({ data: null, error: { message: "connection refused" } })),
    } as unknown as SupabaseClient;

    await expect(drainOutbox(client, async () => "x", { workerId: "w1" })).rejects.toThrow(
      /connection refused/,
    );
  });
});
