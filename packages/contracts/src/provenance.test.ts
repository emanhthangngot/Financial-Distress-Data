import { describe, expect, it } from "vitest";
import {
  isCached,
  provenanceLabels,
  validateProvenance,
  type Provenance,
} from "./provenance";

const live: Provenance = {
  freshness: "LIVE",
  planeAvailability: "LIVE_AVAILABLE",
  origin: "EVIDENCE_PLANE",
  cachedAt: null,
  sourceSha: "ee9b876",
  gitopsSha: "a1b2c3d",
  dataVersion: "gold-2025-05-22",
  modelVersion: "DL-Score v2.1",
  agentVersion: "coordinator-1.4.0",
  runId: "run-20250522-0846",
};

const cached: Provenance = {
  ...live,
  freshness: "CACHED_RESULT",
  planeAvailability: "LIVE_UNAVAILABLE",
  origin: "SUPABASE",
  cachedAt: "2025-05-22T08:46:00Z",
  agentVersion: null,
  runId: "run-20250522-0846",
};

describe("validateProvenance", () => {
  it("accepts a well-formed live record", () => {
    expect(validateProvenance(live)).toEqual([]);
  });

  it("rejects a cached result with no cachedAt timestamp", () => {
    expect(validateProvenance({ ...cached, cachedAt: null })).toContain(
      "CACHED_RESULT requires cachedAt so the reader knows how old the row is",
    );
  });

  it("rejects a LIVE claim while the plane is unavailable", () => {
    const problems = validateProvenance({ ...live, planeAvailability: "LIVE_UNAVAILABLE" });
    expect(problems).toContain(
      "LIVE result cannot be claimed while the plane is LIVE_UNAVAILABLE",
    );
  });

  it("rejects a non-hex source sha", () => {
    expect(validateProvenance({ ...live, sourceSha: "HEAD" })).toHaveLength(1);
  });

  it("requires a data version", () => {
    expect(validateProvenance({ ...live, dataVersion: "  " })).toContain("dataVersion is required");
  });
});

describe("provenanceLabels", () => {
  it("emits both cached and live-unavailable labels when the plane is off", () => {
    expect(provenanceLabels(cached)).toEqual(["CACHED_RESULT", "LIVE_UNAVAILABLE"]);
  });

  it("emits no labels for a genuine live result", () => {
    expect(provenanceLabels(live)).toEqual([]);
  });

  it("marks fixture-backed data so a screenshot cannot pass as executed evidence", () => {
    expect(provenanceLabels({ ...live, origin: "REFERENCE_FIXTURE" })).toEqual([
      "REFERENCE_FIXTURE",
    ]);
  });

  it("reports cached state", () => {
    expect(isCached(cached)).toBe(true);
    expect(isCached(live)).toBe(false);
  });
});
