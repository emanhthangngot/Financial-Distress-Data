import { describe, expect, it, vi } from "vitest";
import type { SupabaseClient } from "@supabase/supabase-js";
import { registerWithPassword } from "./sign-up-action";

function fakeClient(response: Awaited<ReturnType<SupabaseClient["auth"]["signUp"]>>): SupabaseClient {
  return {
    auth: { signUp: vi.fn().mockResolvedValue(response) },
  } as unknown as SupabaseClient;
}

describe("registerWithPassword", () => {
  it("returns a session on immediate signup (confirmation not required)", async () => {
    const client = fakeClient({
      data: {
        user: { id: "user-1" },
        session: {
          access_token: "token-abc",
          refresh_token: "refresh-abc",
          expires_in: 3600,
        },
      },
      error: null,
    } as never);

    const result = await registerWithPassword(client, {
      email: "new@example.com",
      password: "correct-horse",
      displayName: "Nguyễn Văn A",
    });

    expect(result).toEqual({
      ok: true,
      session: { accessToken: "token-abc", refreshToken: "refresh-abc", expiresIn: 3600 },
    });
  });

  it("passes full_name metadata through to auth.signUp when a display name is given", async () => {
    const signUp = vi.fn().mockResolvedValue({
      data: { user: { id: "user-1" }, session: { access_token: "a", refresh_token: "r", expires_in: 3600 } },
      error: null,
    });
    const client = { auth: { signUp } } as unknown as SupabaseClient;

    await registerWithPassword(client, {
      email: "new@example.com",
      password: "correct-horse",
      displayName: "Nguyễn Văn A",
    });

    expect(signUp).toHaveBeenCalledWith({
      email: "new@example.com",
      password: "correct-horse",
      options: { data: { full_name: "Nguyễn Văn A" } },
    });
  });

  it("reports needsEmailConfirmation when Supabase accepts the account but returns no session", async () => {
    const client = fakeClient({
      data: { user: { id: "user-1" }, session: null },
      error: null,
    } as never);

    const result = await registerWithPassword(client, {
      email: "new@example.com",
      password: "correct-horse",
      displayName: null,
    });

    expect(result).toEqual({ ok: true, needsEmailConfirmation: true });
  });

  it("maps a duplicate-email error to Vietnamese copy", async () => {
    const client = fakeClient({
      data: { user: null, session: null },
      error: { message: "User already registered" },
    } as never);

    const result = await registerWithPassword(client, {
      email: "dup@example.com",
      password: "correct-horse",
      displayName: null,
    });

    expect(result).toEqual({
      ok: false,
      message: "Email này đã có tài khoản. Đăng nhập thay vì đăng ký.",
    });
  });

  it("maps a weak-password error to Vietnamese copy", async () => {
    const client = fakeClient({
      data: { user: null, session: null },
      error: { message: "Password should be at least 6 characters" },
    } as never);

    const result = await registerWithPassword(client, {
      email: "weak@example.com",
      password: "abc",
      displayName: null,
    });

    expect(result.ok).toBe(false);
    expect((result as { message: string }).message).toContain("Mật khẩu");
  });

  it("maps a signups-disabled error to Vietnamese copy", async () => {
    const client = fakeClient({
      data: { user: null, session: null },
      error: { message: "Signups not allowed for this instance" },
    } as never);

    const result = await registerWithPassword(client, {
      email: "any@example.com",
      password: "correct-horse",
      displayName: null,
    });

    expect(result).toEqual({
      ok: false,
      message: "Đăng ký đang tắt. Liên hệ quản trị viên để được cấp tài khoản.",
    });
  });

  it("maps a mailer rate-limit error to Vietnamese copy", async () => {
    const client = fakeClient({
      data: { user: null, session: null },
      error: { message: "email rate limit exceeded" },
    } as never);

    const result = await registerWithPassword(client, {
      email: "any@example.com",
      password: "correct-horse",
      displayName: null,
    });

    expect(result).toEqual({
      ok: false,
      message: "Hệ thống gửi email xác nhận đang quá tải. Thử lại sau ít phút.",
    });
  });

  it("never forwards an unmapped upstream error string verbatim", async () => {
    const client = fakeClient({
      data: { user: null, session: null },
      error: { message: "some internal database constraint violation xyz-123" },
    } as never);

    const result = await registerWithPassword(client, {
      email: "any@example.com",
      password: "correct-horse",
      displayName: null,
    });

    expect(result.ok).toBe(false);
    expect((result as { message: string }).message).not.toContain("xyz-123");
    expect((result as { message: string }).message).not.toContain("constraint");
  });
});
