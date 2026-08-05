import { describe, expect, it } from "vitest";
import {
  RISK_BANDS,
  RISK_BAND_LABELS,
  SOURCE_KINDS,
  TREND_DIRECTIONS,
  TREND_LABELS,
} from "./company";

describe("RISK_BAND_LABELS", () => {
  it("labels every risk band — a band added without a label is a bug", () => {
    for (const band of RISK_BANDS) {
      expect(RISK_BAND_LABELS[band]).toBeTruthy();
    }
  });
});

describe("TREND_LABELS", () => {
  it("labels every trend direction", () => {
    for (const direction of TREND_DIRECTIONS) {
      expect(TREND_LABELS[direction]).toBeTruthy();
    }
  });
});

describe("SOURCE_KINDS", () => {
  it("carries the closed set of citation source kinds", () => {
    expect([...SOURCE_KINDS]).toEqual(["BCTC", "NEWS", "MARKET", "INTERNAL"]);
  });
});
