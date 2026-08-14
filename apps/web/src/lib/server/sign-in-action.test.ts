import { describe, expect, it, vi } from "vitest";
import type { SupabaseClient } from "@supabase/supabase-js";
import { authenticateWithPassword } from "./sign-in-action";

function fakeClient(
  response: Awaited<ReturnType<SupabaseClient["auth"]["signInWithPassword"]>>,
): SupabaseClient {
  return {
    auth: { signInWithPassword: vi.fn().mockResolvedValue(response) },
  } as unknown as SupabaseClient;
}

describe("authenticateWithPassword", () => {
  it("returns the access token, refresh token, and expiry on a successful sign-in", async () => {
    const client = fakeClient({
      data: {
        session: {
          access_token: "token-abc",
          refresh_token: "refresh-abc",
          expires_in: 3600,
        },
        user: { id: "user-1" },
      },
      error: null,
    } as never);

    const result = await authenticateWithPassword(client, "grader@example.com", "correct-horse");

    expect(result).toEqual({
      ok: true,
      accessToken: "token-abc",
      refreshToken: "refresh-abc",
      expiresIn: 3600,
    });
  });

  it("surfaces Supabase's own message on a rejected credential", async () => {
    const client = fakeClient({
      data: { session: null, user: null },
      error: { message: "Invalid login credentials" },
    } as never);

    const result = await authenticateWithPassword(client, "grader@example.com", "wrong");

    expect(result).toEqual({ ok: false, message: "Invalid login credentials" });
  });

  it("falls back to generic copy when there is no session and no error message", async () => {
    const client = fakeClient({ data: { session: null, user: null }, error: null } as never);

    const result = await authenticateWithPassword(client, "grader@example.com", "wrong");

    expect(result.ok).toBe(false);
    expect((result as { message: string }).message).not.toBe("");
  });
});
