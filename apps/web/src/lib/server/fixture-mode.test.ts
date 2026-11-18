import { describe, expect, it } from "vitest";
import { fixtureModeEnabled } from "./fixture-mode";

describe("fixture eligibility", () => {
  it("keeps regular deployments on the real session path", () => {
    expect(fixtureModeEnabled({ NODE_ENV: "production" })).toBe(false);
  });

  it("allows explicit local development and production-mode browser fixtures", () => {
    expect(fixtureModeEnabled({ NODE_ENV: "development", DISTRESSLENS_DATA_SOURCE: "fixture" })).toBe(true);
    expect(fixtureModeEnabled({
      NODE_ENV: "production",
      DISTRESSLENS_DATA_SOURCE: "fixture",
      DISTRESSLENS_ALLOW_LOCAL_FIXTURES: "1",
    })).toBe(true);
  });

  it.each([
    {},
    { DISTRESSLENS_RELEASE_IMAGE: "1", DISTRESSLENS_ALLOW_LOCAL_FIXTURES: "1" },
    { VERCEL_ENV: "production", DISTRESSLENS_ALLOW_LOCAL_FIXTURES: "1" },
  ])("rejects a release or an unapproved production process (%j)", (env) => {
    expect(() => fixtureModeEnabled({
      NODE_ENV: "production",
      DISTRESSLENS_DATA_SOURCE: "fixture",
      ...env,
    })).toThrow("fixture mode is not permitted");
  });
});
