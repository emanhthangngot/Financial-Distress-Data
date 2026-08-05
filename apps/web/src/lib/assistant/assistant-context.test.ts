import { describe, expect, it } from "vitest";
import { assistantThreadKey, quickActionsFor, type AssistantContext } from "./assistant-context";

function context(overrides: Partial<AssistantContext> = {}): AssistantContext {
  return {
    scope: "company",
    route: "/companies/ACME",
    surfaceLabel: "ACME",
    ticker: "ACME",
    selectedTickers: [],
    periodLabel: "30 ngày",
    filters: [],
    dataVersion: "v1",
    modelVersion: "m1",
    ...overrides,
  };
}

describe("assistantThreadKey", () => {
  it("keys a ticker-scoped context by scope and ticker", () => {
    expect(assistantThreadKey(context({ scope: "company", ticker: "ACME" }))).toBe(
      "company:ACME",
    );
  });

  it("keys a portfolio-wide context by scope alone", () => {
    expect(assistantThreadKey(context({ scope: "portfolio", ticker: null }))).toBe("portfolio");
  });
});

describe("quickActionsFor", () => {
  it("returns a distinct action set per scope", () => {
    const portfolio = quickActionsFor(context({ scope: "portfolio" }));
    const comparison = quickActionsFor(context({ scope: "comparison" }));

    expect(portfolio.length).toBeGreaterThan(0);
    expect(comparison.length).toBeGreaterThan(0);
    expect(portfolio).not.toEqual(comparison);
  });
});
