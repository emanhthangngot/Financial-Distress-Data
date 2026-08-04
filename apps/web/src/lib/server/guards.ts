import "server-only";
import {
  authorize,
  isQuotaExhausted,
  type AuthorizationDenial,
  type QuotaState,
  type Role,
  type SessionAction,
} from "@distresslens/contracts";

/**
 * The checks every mutation and AI request passes before it reaches data.
 *
 * They are separate small functions rather than one middleware because each has
 * a different failure message the user needs, and because a test can prove each
 * one denies on its own. They run in a fixed order in `guardRequest`: identity
 * and role first, then origin, then rate limit, then quota — cheapest and most
 * decisive first, and never leaking that a resource exists to a caller who
 * failed an earlier check.
 */

export interface GuardContext {
  role: Role | null;
  aal: "aal1" | "aal2";
  userId: string | null;
  /** Origin header of the request, null when absent. */
  origin: string | null;
  /** Host the app is served on, from the request. */
  host: string | null;
}

export type GuardDenial =
  | { denial: AuthorizationDenial; reason: string }
  | { denial: "ORIGIN_MISMATCH"; reason: string };

export type GuardResult = { allowed: true } | { allowed: false; denial: GuardDenial };

const ALLOWED = { allowed: true } as const;

/**
 * Cross-origin write protection.
 *
 * A state-changing request must come from a page this app served. Browsers send
 * `Origin` on every cross-site POST, so a missing or foreign origin on a
 * mutation is either a bug or a forgery, and both should be refused.
 */
export function checkOrigin(context: GuardContext): GuardResult {
  if (context.host === null) {
    return deny("ORIGIN_MISMATCH", "Không xác định được máy chủ của yêu cầu.");
  }

  if (context.origin === null) {
    return deny("ORIGIN_MISMATCH", "Yêu cầu không kèm thông tin nguồn gốc hợp lệ.");
  }

  let originHost: string;
  try {
    originHost = new URL(context.origin).host;
  } catch {
    return deny("ORIGIN_MISMATCH", "Yêu cầu không kèm thông tin nguồn gốc hợp lệ.");
  }

  return originHost === context.host
    ? ALLOWED
    : deny("ORIGIN_MISMATCH", "Yêu cầu đến từ một nguồn khác với ứng dụng.");
}

export interface RateLimitState {
  /** Requests already made in the current window. */
  used: number;
  limit: number;
  /** ISO timestamp the window resets. */
  resetsAt: string;
}

export function checkRateLimit(state: RateLimitState): GuardResult {
  return state.used < state.limit
    ? ALLOWED
    : deny(
        "RATE_LIMITED",
        `Bạn đã gửi quá ${state.limit} yêu cầu trong cửa sổ hiện tại. Thử lại sau khi hạn mức được đặt lại.`,
      );
}

export function checkQuota(quota: QuotaState): GuardResult {
  return isQuotaExhausted(quota)
    ? deny(
        "QUOTA_EXHAUSTED",
        `Bạn đã dùng hết ${quota.limit} lượt phân tích AI của kỳ này. Hạn mức được đặt lại sau đó.`,
      )
    : ALLOWED;
}

export interface GuardRequestInput {
  context: GuardContext;
  action: SessionAction;
  /** Supplied for mutations; reads skip the origin check. */
  mutating: boolean;
  rateLimit?: RateLimitState;
  quota?: QuotaState;
}

/**
 * The single entry point a server action calls. Returns the first denial rather
 * than collecting all of them: telling a caller exactly which four checks they
 * failed is information they have not earned.
 */
export function guardRequest({
  context,
  action,
  mutating,
  rateLimit,
  quota,
}: GuardRequestInput): GuardResult {
  const decision = authorize({ role: context.role, aal: context.aal }, action);
  if (!decision.allowed) {
    return { allowed: false, denial: { denial: decision.denial, reason: decision.reason } };
  }

  if (mutating) {
    const origin = checkOrigin(context);
    if (!origin.allowed) {
      return origin;
    }
  }

  if (rateLimit !== undefined) {
    const limited = checkRateLimit(rateLimit);
    if (!limited.allowed) {
      return limited;
    }
  }

  if (quota !== undefined) {
    const quotaCheck = checkQuota(quota);
    if (!quotaCheck.allowed) {
      return quotaCheck;
    }
  }

  return ALLOWED;
}

function deny(denial: GuardDenial["denial"], reason: string): GuardResult {
  return { allowed: false, denial: { denial, reason } as GuardDenial };
}
