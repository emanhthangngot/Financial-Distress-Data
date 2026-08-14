import { createClient } from "@supabase/supabase-js";
import { NextResponse, type NextRequest } from "next/server";
import { ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE, clearSessionCookies, setSessionCookies } from "@/lib/server/auth-cookies";
import { shouldAttemptRefresh } from "@/lib/server/middleware-refresh";

/**
 * Rotates the Supabase session before it decays to a guest.
 *
 * A Server Component cannot write cookies, so `resolveSession` (session.ts)
 * cannot rotate tokens where it runs -- this has to happen in middleware,
 * ahead of every page render.
 *
 * Fails open to the guest path: any error here (network, malformed cookie,
 * Supabase outage) is caught and the request passes through unchanged.
 * `resolveSession`'s own `auth.getUser()` call is the real authority and
 * renders the honest guest state if the token turns out to be bad -- this
 * middleware only tries to avoid that outcome when it can, it never causes it.
 */

export const config = {
  // Static assets, RSC/build internals, and the SSE assistant stream (which
  // must not be buffered behind a refresh round trip) are excluded.
  matcher: ["/((?!_next/|api/assistant/stream|favicon\\.ico|.*\\.[\\w]+$).*)"],
};

export async function middleware(request: NextRequest): Promise<NextResponse> {
  try {
    const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value ?? null;
    const refreshToken = request.cookies.get(REFRESH_TOKEN_COOKIE)?.value ?? null;

    if (!shouldAttemptRefresh({ accessToken, refreshToken })) {
      return NextResponse.next();
    }

    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    if (url === undefined || anonKey === undefined) {
      return NextResponse.next();
    }

    const client = createClient(url, anonKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
    const { data, error } = await client.auth.refreshSession({ refresh_token: refreshToken! });

    const response = NextResponse.next();

    if (error !== null) {
      // Only a definitive rejection (invalid/expired/revoked refresh token,
      // both surfaced as 400 or 401) means the credential itself is dead --
      // clear it. A network blip or a transient 5xx from Supabase
      // (`AuthRetryableFetchError`, `error.status` unset or >=500) must not
      // cost the caller their refresh token: it fails open by leaving the
      // existing cookies alone, and the next request tries again.
      if (error.status === 400 || error.status === 401) {
        clearSessionCookies(response.cookies);
      }
      return response;
    }

    if (data.session === null) {
      return response;
    }

    setSessionCookies(response.cookies, {
      accessToken: data.session.access_token,
      refreshToken: data.session.refresh_token,
      expiresIn: data.session.expires_in,
    });
    return response;
  } catch {
    return NextResponse.next();
  }
}
