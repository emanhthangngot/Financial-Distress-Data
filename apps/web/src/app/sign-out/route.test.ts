import { beforeEach, describe, expect, it, vi } from "vitest";

const { deleteCookie } = vi.hoisted(() => ({ deleteCookie: vi.fn() }));

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ delete: deleteCookie })),
}));

import { GET } from "./route";

describe("GET /sign-out", () => {
  beforeEach(() => {
    deleteCookie.mockClear();
  });

  it("clears the access-token cookie and redirects to sign-in", async () => {
    const response = await GET(new Request("https://distresslens.example/companies"));

    expect(deleteCookie).toHaveBeenCalledWith("sb-access-token");
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("https://distresslens.example/sign-in");
  });
});
