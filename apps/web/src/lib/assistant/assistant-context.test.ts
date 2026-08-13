import { describe, expect, it } from "vitest";
import {
  assistantThreadKey,
  latestDebtToAssetDriftRows,
  quickActionsFor,
  validateAssistantDriftRows,
  type AssistantContext,
} from "./assistant-context";

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

describe("assistant drift rows", () => {
  it("derives the latest visible Debt/Asset value without coercing or inventing data", () => {
    expect(
      latestDebtToAssetDriftRows("NVL", [
        { name: "Debt/Asset", values: [0.72, 0.76, 0.79] },
        { name: "ROA", values: [-1.8, -2.6, -3.1] },
      ]),
    ).toEqual([{ ticker: "NVL", debt_to_asset: 0.79 }]);
    expect(
      latestDebtToAssetDriftRows("NVL", [{ name: "Debt/Asset", values: [0.72, null] }]),
    ).toBeUndefined();
  });

  it("accepts finite numeric observations and rejects malformed rows", () => {
    expect(validateAssistantDriftRows([{ ticker: "NVL", debt_to_asset: 0.79 }])).toEqual([
      { ticker: "NVL", debt_to_asset: 0.79 },
    ]);
    expect(validateAssistantDriftRows([{ ticker: "NVL", debt_to_asset: "0.79" }])).toBeUndefined();
    expect(validateAssistantDriftRows([{ ticker: "NVL" }])).toBeUndefined();
  });
});
