import "server-only";
import { decodeJwtPayload } from "./jwt-claims";

/**
 * The refresh decision, factored out of `middleware.ts` so it is a pure
 * function testable without spinning up the Next.js middleware runtime.
 *
 * Refresh is attempted whenever a refresh token exists and the access token
 * is either absent or looks expired. The expiry read is a local decode of an
 * unverified `exp` claim, used only to decide whether a refresh round trip is
 * worth attempting -- it grants nothing by itself. If a caller forges an
 * `exp` claim to skip the refresh attempt, `resolveSession`'s real
 * `auth.getUser()` call still rejects the token and the request renders the
 * guest state; this heuristic can only cause a wasted refresh call, never a
 * false grant.
 */

/** Refresh a little before the real deadline, not exactly at it. */
const EXPIRY_SKEW_SECONDS = 30;

export interface RefreshDecisionInput {
  accessToken: string | null;
  refreshToken: string | null;
}

export function shouldAttemptRefresh({ accessToken, refreshToken }: RefreshDecisionInput): boolean {
  if (refreshToken === null) {
    return false;
  }
  if (accessToken === null) {
    return true;
  }
  return isExpiredOrUnreadable(accessToken);
}

function isExpiredOrUnreadable(accessToken: string): boolean {
  const claims = decodeJwtPayload(accessToken);
  const exp = claims?.exp;
  if (typeof exp !== "number") {
    // Unreadable claim: treat as expired so the middleware attempts the
    // refresh round trip rather than serving a token it cannot evaluate.
    return true;
  }
  return exp - EXPIRY_SKEW_SECONDS <= Date.now() / 1000;
}
