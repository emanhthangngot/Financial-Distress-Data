import { beforeEach, describe, expect, it, vi } from "vitest";

const { getCookie, deleteCookie, signOut, createRequestClient } = vi.hoisted(() => ({
  getCookie: vi.fn(),
  deleteCookie: vi.fn(),
  signOut: vi.fn().mockResolvedValue({ error: null }),
  createRequestClient: vi.fn(),
}));

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie, delete: deleteCookie })),
}));

vi.mock("@/lib/server/supabase", () => ({
  createRequestClient: createRequestClient.mockImplementation(() => ({
    auth: { signOut },
  })),
}));

import { GET } from "./route";

describe("GET /sign-out", () => {
  beforeEach(() => {
    getCookie.mockReset();
    deleteCookie.mockClear();
    signOut.mockClear();
    createRequestClient.mockClear();
  });

  it("clears both cookies, revokes upstream, and redirects to /sign-in when no next is given", async () => {
    getCookie.mockReturnValue({ value: "token-abc" });

    const response = await GET(new Request("https://distresslens.example/sign-out"));

    expect(createRequestClient).toHaveBeenCalledWith("token-abc");
    expect(signOut).toHaveBeenCalledOnce();
    expect(deleteCookie).toHaveBeenCalledWith("sb-access-token");
    expect(deleteCookie).toHaveBeenCalledWith("sb-refresh-token");
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("https://distresslens.example/sign-in");
  });

  it("skips the upstream revoke when there is no access-token cookie", async () => {
    getCookie.mockReturnValue(undefined);

    await GET(new Request("https://distresslens.example/sign-out"));

    expect(createRequestClient).not.toHaveBeenCalled();
    expect(signOut).not.toHaveBeenCalled();
  });

  it("still clears cookies and redirects when the upstream revoke throws", async () => {
    getCookie.mockReturnValue({ value: "token-abc" });
    signOut.mockRejectedValueOnce(new Error("network blip"));

    const response = await GET(new Request("https://distresslens.example/sign-out"));

    expect(deleteCookie).toHaveBeenCalledWith("sb-access-token");
    expect(deleteCookie).toHaveBeenCalledWith("sb-refresh-token");
    expect(response.status).toBe(307);
  });

  it("redirects to a validated same-origin next instead of the default", async () => {
    getCookie.mockReturnValue(undefined);

    const response = await GET(
      new Request("https://distresslens.example/sign-out?next=%2Fsign-in%3Femail%3Da%40b.c"),
    );

    expect(response.headers.get("location")).toBe(
      "https://distresslens.example/sign-in?email=a@b.c",
    );
  });

  it("falls back to /sign-in for an absolute-URL next (open-redirect shape)", async () => {
    getCookie.mockReturnValue(undefined);

    const response = await GET(
      new Request("https://distresslens.example/sign-out?next=https%3A%2F%2Fevil.example"),
    );

    expect(response.headers.get("location")).toBe("https://distresslens.example/sign-in");
  });

  it("falls back to /sign-in for a protocol-relative next (open-redirect shape)", async () => {
    getCookie.mockReturnValue(undefined);

    const response = await GET(
      new Request("https://distresslens.example/sign-out?next=%2F%2Fevil.example"),
    );

    expect(response.headers.get("location")).toBe("https://distresslens.example/sign-in");
  });
});
