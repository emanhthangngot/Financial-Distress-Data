import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { ACCESS_TOKEN_COOKIE, clearSessionCookies } from "@/lib/server/auth-cookies";
import { safeRedirectTarget } from "@/lib/server/redirect-target";
import { createRequestClient } from "@/lib/server/supabase";

/**
 * Ends the server-side session created by the sign-in action.
 *
 * The shell exposes this as a normal link so it remains usable when a client
 * bundle is unavailable. Clears both cookies (access + refresh) and calls
 * `auth.signOut()` with the caller's token so the refresh token is revoked
 * server-side rather than merely forgotten by the browser -- a session cookie
 * copied before this route ran must not still work afterward.
 *
 * `?next=` lets the account switcher land on `/sign-in?email=...` after
 * sign-out; it goes through the same same-origin validator as the sign-in
 * action so this route cannot become an open redirect.
 */
export async function GET(request: Request): Promise<NextResponse> {
  const jar = await cookies();
  const accessToken = jar.get(ACCESS_TOKEN_COOKIE)?.value ?? null;

  if (accessToken !== null) {
    // Best-effort: sign-out must still clear cookies and redirect even if the
    // upstream revoke call fails (network issue, already-expired token).
    try {
      await createRequestClient(accessToken).auth.signOut();
    } catch {
      // Cookies are cleared below regardless.
    }
  }

  clearSessionCookies(jar);

  const url = new URL(request.url);
  const next = safeRedirectTarget(url.searchParams.get("next"));
  const destination = next === "/" ? "/sign-in" : next;

  return NextResponse.redirect(new URL(destination, request.url));
}
