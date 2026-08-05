import { describe, expect, it, vi } from "vitest";
import type { SupabaseClient } from "@supabase/supabase-js";
import { consumeAiBudget, recordAuditEvent } from "./ai-budget";

/**
 * The wrappers are tested against a stub of the RPC surface. What is proved here
 * is the translation: that a database row becomes a typed decision with the same
 * copy the pre-flight guards use, and that an RPC failure throws rather than
 * pretending the budget was checked. The RPCs themselves are proved by the SQL
 * migration and the RLS pytest suite.
 */

interface RpcCall {
  name: string;
  args: Record<string, unknown>;
}

const ALLOWED_ROW = {
  allowed: true,
  denial: null,
  quota_used: 1,
  quota_limit: 20,
  quota_resets_at: "2025-05-23T00:00:00.000Z",
  rate_used: 1,
  rate_limit: 5,
  rate_resets_at: "2025-05-22T12:01:00.000Z",
};

function stubClient(
  overrides: Record<string, { data?: unknown; error?: { message: string } | null }> = {},
): { client: SupabaseClient; calls: RpcCall[] } {
  const calls: RpcCall[] = [];
  const client = {
    rpc: vi.fn(async (name: string, args: Record<string, unknown>) => {
      calls.push({ name, args });
      const override = overrides[name];
      return { data: override?.data ?? null, error: override?.error ?? null };
    }),
  } as unknown as SupabaseClient;
  return { client, calls };
}

describe("consumeAiBudget", () => {
  it("maps an allowed row to typed quota and rate state", async () => {
    const { client, calls } = stubClient({ consume_ai_quota: { data: [ALLOWED_ROW] } });

    const decision = await consumeAiBudget(client);

    expect(decision).toEqual({
      ok: true,
      quotaState: { used: 1, limit: 20, resetsAt: "2025-05-23T00:00:00.000Z" },
      rateState: { used: 1, limit: 5, resetsAt: "2025-05-22T12:01:00.000Z" },
    });
    expect(calls[0]?.name).toBe("consume_ai_quota");
    expect(calls[0]?.args).toMatchObject({
      p_quota_limit: 20,
      p_quota_window: "86400 seconds",
      p_rate_limit: 5,
      p_rate_window: "60 seconds",
    });
  });

  it("maps a quota exhaustion row to the guards' exact copy", async () => {
    const { client } = stubClient({
      consume_ai_quota: {
        data: [
          {
            allowed: false,
            denial: "QUOTA_EXHAUSTED",
            quota_used: 20,
            quota_limit: 20,
            quota_resets_at: "2025-05-23T00:00:00.000Z",
            rate_used: 1,
            rate_limit: 5,
            rate_resets_at: "2025-05-22T12:01:00.000Z",
          },
        ],
      },
    });

    const decision = await consumeAiBudget(client);

    expect(decision.ok).toBe(false);
    if (!decision.ok) {
      expect(decision.denial).toBe("QUOTA_EXHAUSTED");
      expect(decision.resetsAt).toBe("2025-05-23T00:00:00.000Z");
      expect(decision.reason).toMatch(/hạn mức/i);
    }
  });

  it("maps a rate limit row to the rate copy with its own reset time", async () => {
    const { client } = stubClient({
      consume_ai_quota: {
        data: [
          {
            allowed: false,
            denial: "RATE_LIMITED",
            quota_used: 3,
            quota_limit: 20,
            quota_resets_at: "2025-05-23T00:00:00.000Z",
            rate_used: 5,
            rate_limit: 5,
            rate_resets_at: "2025-05-22T12:01:00.000Z",
          },
        ],
      },
    });

    const decision = await consumeAiBudget(client);

    expect(decision.ok).toBe(false);
    if (!decision.ok) {
      expect(decision.denial).toBe("RATE_LIMITED");
      expect(decision.resetsAt).toBe("2025-05-22T12:01:00.000Z");
      expect(decision.reason).toContain("cửa sổ hiện tại");
    }
  });

  it("throws when the RPC reports an error instead of returning a fake pass", async () => {
    const { client } = stubClient({
      consume_ai_quota: { error: { message: "connection refused" } },
    });

    await expect(consumeAiBudget(client)).rejects.toThrow(/connection refused/);
  });

  it("throws when the RPC returns no decision row", async () => {
    const { client } = stubClient({ consume_ai_quota: { data: [] } });

    await expect(consumeAiBudget(client)).rejects.toThrow(/no decision row/);
  });
});

describe("recordAuditEvent", () => {
  it("passes action, outcome, context id and whitelisted metadata to the RPC", async () => {
    const { client, calls } = stubClient({
      record_audit_event: { data: "00000000-0000-0000-0000-0000000000aa" },
    });

    const id = await recordAuditEvent(client, {
      action: "ai.request",
      outcome: "ALLOWED",
      contextId: "NVL",
      metadata: { quota_remaining: 18, rate_remaining: 4 },
    });

    expect(id).toBe("00000000-0000-0000-0000-0000000000aa");
    expect(calls[0]?.name).toBe("record_audit_event");
    expect(calls[0]?.args).toEqual({
      p_action: "ai.request",
      p_outcome: "ALLOWED",
      p_context_id: "NVL",
      p_metadata: { quota_remaining: 18, rate_remaining: 4 },
    });
  });

  it("sends an empty object rather than undefined metadata", async () => {
    const { client, calls } = stubClient({ record_audit_event: { data: "id-1" } });

    await recordAuditEvent(client, {
      action: "ai.request",
      outcome: "PLANE_OFF",
      contextId: "HPG",
    });

    expect(calls[0]?.args.p_metadata).toEqual({});
  });

  it("throws when the RPC reports an error so callers can audit FAILED", async () => {
    const { client } = stubClient({
      record_audit_event: { error: { message: "metadata key is not permitted" } },
    });

    await expect(
      recordAuditEvent(client, {
        action: "ai.request",
        outcome: "ALLOWED",
        contextId: "HPG",
      }),
    ).rejects.toThrow(/metadata key is not permitted/);
  });
});