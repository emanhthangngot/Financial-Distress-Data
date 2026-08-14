import "server-only";

/**
 * The Supabase session cookie contract, defined in exactly one place.
 *
 * `sb-access-token` and `sb-refresh-token` were previously a string literal
 * repeated in `sign-in-action.ts`, `session.ts`, and `sign-out/route.ts` --
 * three places that could silently drift. Every reader and writer of these
 * cookies goes through this module instead.
 */

export const ACCESS_TOKEN_COOKIE = "sb-access-token";
export const REFRESH_TOKEN_COOKIE = "sb-refresh-token";

const ONE_DAY_SECONDS = 60 * 60 * 24;

interface CookieJarLike {
  set(name: string, value: string, options: Record<string, unknown>): void;
  delete(name: string): void;
}

/** Base options shared by both cookies; only `maxAge` differs between them. */
function baseCookieOptions(): { httpOnly: true; secure: boolean; sameSite: "lax"; path: "/" } {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
  };
}

export interface SessionCookiePair {
  accessToken: string;
  refreshToken: string;
  /** Seconds until the access token expires, from Supabase's `expires_in`. */
  expiresIn: number;
}

/** Writes both cookies for a freshly issued or rotated session. */
export function setSessionCookies(jar: CookieJarLike, pair: SessionCookiePair): void {
  jar.set(ACCESS_TOKEN_COOKIE, pair.accessToken, {
    ...baseCookieOptions(),
    maxAge: pair.expiresIn,
  });
  jar.set(REFRESH_TOKEN_COOKIE, pair.refreshToken, {
    ...baseCookieOptions(),
    maxAge: 30 * ONE_DAY_SECONDS,
  });
}

/** Clears both cookies; the caller is left with the guest state. */
export function clearSessionCookies(jar: CookieJarLike): void {
  jar.delete(ACCESS_TOKEN_COOKIE);
  jar.delete(REFRESH_TOKEN_COOKIE);
}
