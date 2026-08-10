import { describe, expect, it } from "vitest";
import type { QuotaState } from "@distresslens/contracts";
import { checkOrigin, checkQuota, checkRateLimit, guardRequest, type GuardContext } from "./guards";

const operator: GuardContext = {
  role: "platform_operator",
  aal: "aal2",
  userId: "op-1",
  origin: "https://distresslens.example",
  host: "distresslens.example",
};

const quota: QuotaState = { used: 3, limit: 10, resetsAt: "2025-05-23T00:00:00+07:00" };

describe("origin check", () => {
  it("accepts a request from the app's own origin", () => {
    expect(checkOrigin(operator).allowed).toBe(true);
  });

  it("rejects a request from another site", () => {
    const result = checkOrigin({ ...operator, origin: "https://evil.example" });
    expect(result.allowed).toBe(false);
  });

  it("rejects a mutation with no origin at all", () => {
    // A browser sends Origin on every cross-site POST, so its absence on a
    // mutation is either a bug or a forgery.
    expect(checkOrigin({ ...operator, origin: null }).allowed).toBe(false);
  });

  it("rejects an origin that is not a URL rather than throwing", () => {
    expect(checkOrigin({ ...operator, origin: "not a url" }).allowed).toBe(false);
  });
});

describe("rate limit and quota", () => {
  it("allows a caller inside the window and denies one at the limit", () => {
    expect(
      checkRateLimit({ used: 9, limit: 10, resetsAt: "2025-05-23T00:00:00+07:00" }).allowed,
    ).toBe(true);
    expect(
      checkRateLimit({ used: 10, limit: 10, resetsAt: "2025-05-23T00:00:00+07:00" }).allowed,
    ).toBe(false);
  });

  it("denies an exhausted AI quota", () => {
    expect(checkQuota(quota).allowed).toBe(true);
    expect(checkQuota({ ...quota, used: 10 }).allowed).toBe(false);
  });
});

describe("guardRequest ordering", () => {
  it("denies an unauthorized role before it ever looks at the origin", () => {
    // Ordering matters: an unauthorized caller must not be able to learn
    // anything from which later check would have failed.
    const result = guardRequest({
      context: { ...operator, role: "analyst", origin: "https://evil.example" },
      action: "session.provision",
      mutating: true,
    });

    expect(result.allowed).toBe(false);
    if (!result.allowed) {
      expect(result.denial.denial).toBe("ROLE_NOT_PERMITTED");
    }
  });

  it("requires AAL2 for a privileged mutation", () => {
    const result = guardRequest({
      context: { ...operator, aal: "aal1" },
      action: "session.provision",
      mutating: true,
    });

    expect(result.allowed).toBe(false);
    if (!result.allowed) {
      expect(result.denial.denial).toBe("AAL2_REQUIRED");
    }
  });

  it("checks the origin on a mutation and skips it on a read", () => {
    const foreign = { ...operator, origin: "https://evil.example" };

    const mutation = guardRequest({
      context: foreign,
      action: "session.provision",
      mutating: true,
    });
    expect(mutation.allowed).toBe(false);

    // A read has no side effect to forge, and requiring an origin on it would
    // break ordinary navigation.
    const read = guardRequest({ context: foreign, action: "session.read", mutating: false });
    expect(read.allowed).toBe(true);
  });

  it("denies a rate-limited caller before spending their quota", () => {
    const result = guardRequest({
      context: operator,
      action: "session.read",
      mutating: false,
      rateLimit: { used: 10, limit: 10, resetsAt: "2025-05-23T00:00:00+07:00" },
      quota: { ...quota, used: 10 },
    });

    expect(result.allowed).toBe(false);
    if (!result.allowed) {
      expect(result.denial.denial).toBe("RATE_LIMITED");
    }
  });

  it("passes an operator with everything in order", () => {
    expect(
      guardRequest({
        context: operator,
        action: "session.provision",
        mutating: true,
        rateLimit: { used: 1, limit: 10, resetsAt: "2025-05-23T00:00:00+07:00" },
        quota,
      }).allowed,
    ).toBe(true);
  });
});
