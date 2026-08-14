import "server-only";

/**
 * Reads the `aal` claim off an already-verified access token.
 *
 * This is a payload decode, not an independent trust decision: callers only
 * reach this after `auth.getUser()` has verified the token against Supabase.
 * `@supabase/auth-js`'s `User` type carries no `aal` field (it exists only on
 * the raw JWT payload), so the claim has to be read here instead of trusted
 * from a field that does not exist on the object Supabase returns.
 */

interface JwtClaims {
  aal?: unknown;
  [key: string]: unknown;
}

/** Decodes the base64url JWT payload without verifying the signature. */
export function decodeJwtPayload(token: string | null): JwtClaims | null {
  if (token === null) {
    return null;
  }

  const parts = token.split(".");
  if (parts.length !== 3) {
    return null;
  }

  try {
    const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = payload.padEnd(payload.length + ((4 - (payload.length % 4)) % 4), "=");
    const json = Buffer.from(padded, "base64").toString("utf8");
    const parsed: unknown = JSON.parse(json);
    return parsed !== null && typeof parsed === "object" ? (parsed as JwtClaims) : null;
  } catch {
    return null;
  }
}

/** Fail-closed: anything not positively `aal2` is treated as `aal1`. */
export function readAssuranceLevel(accessToken: string | null): "aal1" | "aal2" {
  const claims = decodeJwtPayload(accessToken);
  return claims?.aal === "aal2" ? "aal2" : "aal1";
}
