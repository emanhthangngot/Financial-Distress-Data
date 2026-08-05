import "server-only";
import type { SupabaseClient } from "@supabase/supabase-js";
import {
  AI_BUDGET_DEFAULTS,
  type QuotaState,
  type RateLimitState,
} from "@distresslens/contracts";
import { checkQuota, checkRateLimit } from "./guards";

/**
 * Server wrapper over the phase-01 AI budget RPCs.
 *
 * `consumeAiBudget` performs the atomic consume-and-check per user per window and
 * returns a typed decision. It reuses the exact denial copy in `guards.ts` by
 * feeding the RPC's returned state back through `checkRateLimit`/`checkQuota`,
 * so the copy cannot drift between the pre-flight guard and the persisted path.
 *
 * `recordAuditEvent` is the only AI-request audit write. It takes no free-text
 * message and no token: `contextId` is a ticker/session id and `metadata` may
 * only carry the whitelisted scalar keys the database function validates, so
 * prompt text is unrepresentable at the signature.
 *
 * Both functions throw on an RPC/transport error; callers translate a throw into
 * an audit `FAILED` row and an honest refusal. They will never swallow the
 * database error and pretend the budget was not checked.
 */

export const AI_AUDIT_OUTCOMES = [
  "ALLOWED",
  "RATE_LIMITED",
  "QUOTA_EXHAUSTED",
  "FORBIDDEN",
  "PLANE_OFF",
  "FAILED",
] as const;
export type AIAuditOutcome = (typeof AI_AUDIT_OUTCOMES)[number];

export type AiBudgetDecision =
  | { ok: true; quotaState: QuotaState; rateState: RateLimitState }
  | { ok: false; denial: "RATE_LIMITED" | "QUOTA_EXHAUSTED"; reason: string; resetsAt: string };

/**
 * The fields `consume_ai_quota` returns. Column names are snake_case because
 * they come straight from Postgres and never cross the wire over the app boundary.
 */
interface ConsumeAiQuotaRow {
  allowed: boolean;
  denial: string | null;
  quota_used: number;
  quota_limit: number;
  quota_resets_at: string;
  rate_used: number;
  rate_limit: number;
  rate_resets_at: string;
}

export async function consumeAiBudget(
  client: SupabaseClient,
): Promise<AiBudgetDecision> {
  const { quotaLimit, quotaWindowMs, rateLimit, rateWindowMs } = AI_BUDGET_DEFAULTS;

  const { data, error } = await client.rpc("consume_ai_quota", {
    p_quota_limit: quotaLimit,
    p_quota_window: `${Math.round(quotaWindowMs / 1000)} seconds`,
    p_rate_limit: rateLimit,
    p_rate_window: `${Math.round(rateWindowMs / 1000)} seconds`,
  });

  if (error !== null) {
    throw new Error(`could not consume AI quota: ${error.message}`);
  }

  const row = (data as ConsumeAiQuotaRow[] | null)?.[0];
  if (row === undefined) {
    throw new Error("consume_ai_quota returned no decision row");
  }

  const rateState: RateLimitState = {
    used: row.rate_used,
    limit: row.rate_limit,
    resetsAt: row.rate_resets_at,
  };
  const quotaState: QuotaState = {
    used: row.quota_used,
    limit: row.quota_limit,
    resetsAt: row.quota_resets_at,
  };

  if (!row.allowed) {
    // The RPC denies for exactly one reason; re-derive the copy through the
    // guards so this decision matches what the pre-flight guard would have said.
    if (row.denial === "RATE_LIMITED") {
      const limited = checkRateLimit(rateState);
      return {
        ok: false,
        denial: "RATE_LIMITED",
        reason: limited.allowed ? "" : limited.denial.reason,
        resetsAt: rateState.resetsAt,
      };
    }
    const exhausted = checkQuota(quotaState);
    return {
      ok: false,
      denial: "QUOTA_EXHAUSTED",
      reason: exhausted.allowed ? "" : exhausted.denial.reason,
      resetsAt: quotaState.resetsAt,
    };
  }

  return { ok: true, quotaState, rateState };
}

export interface AuditEventInput {
  action: "ai.request";
  outcome: AIAuditOutcome;
  /** Ticker or session id — never free text. */
  contextId: string;
  /** Whitelisted scalar keys only: reason, quota_remaining, rate_remaining, attempt. */
  metadata?: Record<string, number | string>;
}

export async function recordAuditEvent(
  client: SupabaseClient,
  event: AuditEventInput,
): Promise<string | null> {
  const { data, error } = await client.rpc("record_audit_event", {
    p_action: event.action,
    p_outcome: event.outcome,
    p_context_id: event.contextId,
    p_metadata: event.metadata ?? {},
  });

  if (error !== null) {
    throw new Error(`could not record AI audit event: ${error.message}`);
  }

  return data === undefined || data === null ? null : String(data);
}