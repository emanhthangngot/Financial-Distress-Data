import { describe, expect, it } from "vitest";
import { safeRedirectTarget } from "./redirect-target";

describe("safeRedirectTarget", () => {
  it("defaults to / when next is absent", () => {
    expect(safeRedirectTarget(null)).toBe("/");
  });

  it("accepts a same-origin relative path", () => {
    expect(safeRedirectTarget("/companies")).toBe("/companies");
  });

  it("rejects an absolute URL", () => {
    expect(safeRedirectTarget("https://evil.example/phish")).toBe("/");
  });

  it("rejects a protocol-relative URL", () => {
    expect(safeRedirectTarget("//evil.example")).toBe("/");
  });

  it("rejects a path with no leading slash", () => {
    expect(safeRedirectTarget("evil.example")).toBe("/");
  });

  it("rejects a backslash-prefixed value (parses cross-origin despite passing the // check)", () => {
    expect(safeRedirectTarget("/\\evil.example")).toBe("/");
  });

  it("rejects a backslash anywhere in the value", () => {
    expect(safeRedirectTarget("/\\/evil.example")).toBe("/");
    expect(safeRedirectTarget("/companies/\\evil.example")).toBe("/");
  });

  it("accepts a percent-encoded backslash (stays same-origin, never reaches the parser unescaped)", () => {
    expect(safeRedirectTarget("/%5Cevil.example")).toBe("/%5Cevil.example");
  });
});
