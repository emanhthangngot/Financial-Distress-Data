"use server";

import "server-only";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { SupabaseClient } from "@supabase/supabase-js";
import { setSessionCookies } from "./auth-cookies";
import { safeRedirectTarget } from "./redirect-target";
import { createRequestClient } from "./supabase";

/**
 * Server-side sign-in.
 *
 * `NEXT_PUBLIC_*` values are inlined into the browser bundle at Next.js build
 * time, so injecting them as runtime env into a prebuilt image never
 * configures a browser-side Supabase client — only a server-side exchange
 * that runs after the image is built can use runtime env. This route is that
 * exchange: it authenticates against Supabase with the anon key (server-side,
 * never shipped as a service-role key) and sets the session cookies
 * `resolveSession` (session.ts) already reads. The anon key itself never
 * reaches the browser through this path — only the resulting session cookies
 * do.
 *
 * The access token alone used to be the whole session, which decayed to a
 * guest after `expires_in` (~1h). The refresh token is now stored too, and
 * `middleware.ts` rotates the pair before it expires.
 */

export interface SignInResult {
  ok: boolean;
  /** User-facing message; never a Supabase/database error string verbatim. */
  message: string;
}

/**
 * The authentication call, factored out from the cookie/redirect side
 * effects so it can be unit-tested against a hand-built fake client instead
 * of a real Supabase project.
 */
export async function authenticateWithPassword(
  client: SupabaseClient,
  email: string,
  password: string,
): Promise<
  | { ok: true; accessToken: string; refreshToken: string; expiresIn: number }
  | { ok: false; message: string }
> {
  const { data, error } = await client.auth.signInWithPassword({ email, password });

  if (error !== null || data.session === null) {
    // Supabase's own message ("Invalid login credentials") is safe to show
    // as-is — it never carries a stack trace or an internal identifier —
    // but a missing session on a null error still gets the same generic
    // copy rather than surfacing an unexpected shape to the user.
    return {
      ok: false,
      message: error?.message ?? "Không đăng nhập được. Kiểm tra lại email và mật khẩu.",
    };
  }

  return {
    ok: true,
    accessToken: data.session.access_token,
    refreshToken: data.session.refresh_token,
    expiresIn: data.session.expires_in,
  };
}

export async function signIn(_prevState: SignInResult, formData: FormData): Promise<SignInResult> {
  const email = formData.get("email");
  const password = formData.get("password");

  if (typeof email !== "string" || email.trim() === "" || typeof password !== "string" || password === "") {
    return { ok: false, message: "Nhập email và mật khẩu." };
  }

  const result = await authenticateWithPassword(createRequestClient(null), email, password);
  if (!result.ok) {
    return result;
  }

  setSessionCookies(await cookies(), {
    accessToken: result.accessToken,
    refreshToken: result.refreshToken,
    expiresIn: result.expiresIn,
  });

  const target = safeRedirectTarget(formData.get("next"));

  // Throws internally (NEXT_REDIRECT) — deliberately not wrapped in a
  // try/catch above, or the redirect would be swallowed as an error.
  redirect(target);
}
