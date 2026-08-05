/**
 * Per-user AI budget constants and window math.
 *
 * The RLS test, the route handler and the UI copy all need the same numbers,
 * so they live here once instead of being duplicated across Python, SQL and
 * React where they could drift. The window is a fixed bucketed window rather
 * than sliding, because a fixed window lets the UI state an exact reset time
 * instead of a rolling one.
 *
 * Nothing here carries a prompt or a token: it is counters and clocks only.
 */

export const AI_QUOTA_LIMIT = 20;
export const AI_QUOTA_WINDOW_MS = 24 * 60 * 60 * 1000; // 24h
export const AI_RATE_LIMIT = 5;
export const AI_RATE_WINDOW_MS = 60 * 1000; // 60s

export interface AILimits {
  quotaLimit: number;
  quotaWindowMs: number;
  rateLimit: number;
  rateWindowMs: number;
}

/** The single source of truth the database RPC callers and the UI read. */
export const AI_BUDGET_DEFAULTS: AILimits = {
  quotaLimit: AI_QUOTA_LIMIT,
  quotaWindowMs: AI_QUOTA_WINDOW_MS,
  rateLimit: AI_RATE_LIMIT,
  rateWindowMs: AI_RATE_WINDOW_MS,
};

export interface RateLimitState {
  /** Requests already made in the current window. */
  used: number;
  limit: number;
  /** ISO timestamp the window resets. */
  resetsAt: string;
}

/**
 * Start of the bucketed window containing `now`. Epoch-millisecond bucketing is
 * UTC by construction (`Date#getTime` is UTC), so there is no timezone case to
 * reason about and no DST boundary to miss.
 */
export function windowStartAt(now: Date, windowMs: number): Date {
  return new Date(Math.floor(now.getTime() / windowMs) * windowMs);
}

/** Instant the window starting at `windowStart` resets. */
export function resetsAtTime(windowStart: Date, windowMs: number): Date {
  return new Date(windowStart.getTime() + windowMs);
}