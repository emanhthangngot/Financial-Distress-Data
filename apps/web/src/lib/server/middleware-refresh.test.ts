import { describe, expect, it } from "vitest";
import { shouldAttemptRefresh } from "./middleware-refresh";

function tokenWithExp(expSecondsFromNow: number): string {
  const header = base64url({ alg: "HS256", typ: "JWT" });
  const exp = Math.floor(Date.now() / 1000) + expSecondsFromNow;
  const payload = base64url({ sub: "u1", exp });
  return `${header}.${payload}.sig`;
}

function base64url(obj: unknown): string {
  return Buffer.from(JSON.stringify(obj))
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

describe("shouldAttemptRefresh", () => {
  it("does nothing when there is no refresh token, regardless of access token state", () => {
    expect(shouldAttemptRefresh({ accessToken: null, refreshToken: null })).toBe(false);
    expect(shouldAttemptRefresh({ accessToken: tokenWithExp(3600), refreshToken: null })).toBe(
      false,
    );
  });

  it("attempts a refresh when the access token is missing but a refresh token exists", () => {
    expect(shouldAttemptRefresh({ accessToken: null, refreshToken: "refresh-1" })).toBe(true);
  });

  it("skips the refresh when the access token is comfortably unexpired", () => {
    expect(
      shouldAttemptRefresh({ accessToken: tokenWithExp(3600), refreshToken: "refresh-1" }),
    ).toBe(false);
  });

  it("attempts a refresh when the access token is already past expiry", () => {
    expect(
      shouldAttemptRefresh({ accessToken: tokenWithExp(-10), refreshToken: "refresh-1" }),
    ).toBe(true);
  });

  it("attempts a refresh inside the expiry skew window", () => {
    expect(
      shouldAttemptRefresh({ accessToken: tokenWithExp(10), refreshToken: "refresh-1" }),
    ).toBe(true);
  });

  it("attempts a refresh when the access token claim cannot be read", () => {
    expect(
      shouldAttemptRefresh({ accessToken: "not-a-jwt", refreshToken: "refresh-1" }),
    ).toBe(true);
  });
});
