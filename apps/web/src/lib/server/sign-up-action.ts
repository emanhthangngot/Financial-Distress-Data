"use server";

import "server-only";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { SupabaseClient } from "@supabase/supabase-js";
import { setSessionCookies } from "./auth-cookies";
import { createRequestClient } from "./supabase";

/**
 * Server-side sign-up.
 *
 * New accounts default to `analyst` via the `handle_new_user()` trigger
 * (`supabase/migrations/20260814200000_phase2_profile_identity.sql`) -- this
 * action never writes a role.
 *
 * The remote project requires email confirmation
 * (`GET /auth/v1/settings` reports `mailer_autoconfirm: false`), unlike the
 * local `supabase/config.toml`, which only governs the local stack. A
 * successful `signUp` call therefore does not always return a session: when
 * confirmation is required, Supabase returns a user with no session and the
 * UI must show "check your email" copy instead of redirecting to `/`.
 */

export interface SignUpResult {
  ok: boolean;
  /** Set when signup succeeded but the account needs email confirmation before it can sign in. */
  needsEmailConfirmation?: boolean;
  /** User-facing message; never a raw Supabase/database error string. */
  message: string;
}

type RegisterResult =
  | { ok: true; session: { accessToken: string; refreshToken: string; expiresIn: number } }
  | { ok: true; needsEmailConfirmation: true }
  | { ok: false; message: string };

/**
 * The registration call, factored out from the cookie/redirect side effects
 * so it can be unit-tested against a hand-built fake client.
 */
export async function registerWithPassword(
  client: SupabaseClient,
  input: { email: string; password: string; displayName: string | null },
): Promise<RegisterResult> {
  const { data, error } = await client.auth.signUp({
    email: input.email,
    password: input.password,
    options: {
      data: input.displayName === null ? undefined : { full_name: input.displayName },
    },
  });

  if (error !== null) {
    return { ok: false, message: mapSignUpError(error.message) };
  }

  if (data.session === null) {
    // No error, no session: Supabase accepted the account and is waiting on
    // email confirmation before it will issue one.
    return { ok: true, needsEmailConfirmation: true };
  }

  return {
    ok: true,
    session: {
      accessToken: data.session.access_token,
      refreshToken: data.session.refresh_token,
      expiresIn: data.session.expires_in,
    },
  };
}

/**
 * A table, not a passthrough: an unmapped upstream error never reaches the
 * UI verbatim, so a change in Supabase's wording cannot leak internal detail
 * through a fallback string it happens to match loosely.
 */
function mapSignUpError(message: string): string {
  if (message.includes("already registered")) {
    return "Email này đã có tài khoản. Đăng nhập thay vì đăng ký.";
  }
  if (message.toLowerCase().includes("password")) {
    return "Mật khẩu quá ngắn hoặc không đủ mạnh. Dùng ít nhất 6 ký tự.";
  }
  if (message.includes("Signups not allowed") || message.includes("Signup requires a valid password")) {
    return "Đăng ký đang tắt. Liên hệ quản trị viên để được cấp tài khoản.";
  }
  if (message.toLowerCase().includes("rate limit")) {
    return "Hệ thống gửi email xác nhận đang quá tải. Thử lại sau ít phút.";
  }
  if (message.toLowerCase().includes("email") && message.toLowerCase().includes("invalid")) {
    return "Địa chỉ email không hợp lệ.";
  }
  return "Không đăng ký được. Thử lại sau.";
}

function validateInput(
  email: FormDataEntryValue | null,
  password: FormDataEntryValue | null,
): { ok: true; email: string; password: string } | { ok: false; message: string } {
  if (typeof email !== "string" || email.trim() === "") {
    return { ok: false, message: "Nhập email." };
  }
  if (typeof password !== "string" || password.length < 6) {
    return { ok: false, message: "Mật khẩu cần ít nhất 6 ký tự." };
  }
  return { ok: true, email: email.trim(), password };
}

export async function signUp(_prevState: SignUpResult, formData: FormData): Promise<SignUpResult> {
  const validated = validateInput(formData.get("email"), formData.get("password"));
  if (!validated.ok) {
    return { ok: false, message: validated.message };
  }

  const displayNameRaw = formData.get("displayName");
  const displayName =
    typeof displayNameRaw === "string" && displayNameRaw.trim() !== "" ? displayNameRaw.trim() : null;

  const result = await registerWithPassword(createRequestClient(null), {
    email: validated.email,
    password: validated.password,
    displayName,
  });

  if (!result.ok) {
    return result;
  }

  if ("needsEmailConfirmation" in result) {
    return {
      ok: true,
      needsEmailConfirmation: true,
      message: "Đã gửi email xác nhận. Kiểm tra hộp thư rồi đăng nhập.",
    };
  }

  setSessionCookies(await cookies(), result.session);

  // Throws internally (NEXT_REDIRECT) — deliberately not wrapped above.
  redirect("/");
}
