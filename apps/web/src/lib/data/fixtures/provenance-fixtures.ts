import type { Provenance } from "@distresslens/contracts";

/**
 * Provenance stamps shared by every fixture. `origin: REFERENCE_FIXTURE` is what
 * makes a fixture-backed screenshot self-identifying, so it can never be filed
 * as executed runtime evidence.
 */

/** Pinned so screenshots stay byte-stable across runs. */
export const FIXTURE_DATA_VERSION = "gold-2025-05-22";
export const FIXTURE_MODEL_VERSION = "DL-Score v2.1";
export const FIXTURE_AGENT_VERSION = "coordinator-exp-20250522";
export const FIXTURE_CACHED_AT = "2025-05-22T08:46:00.000Z";
export const FIXTURE_SOURCE_SHA = "ee9b876";
export const FIXTURE_GITOPS_SHA = "a1b2c3d";

export const LIVE_FIXTURE_PROVENANCE: Provenance = {
  freshness: "LIVE",
  planeAvailability: "LIVE_AVAILABLE",
  origin: "REFERENCE_FIXTURE",
  cachedAt: null,
  sourceSha: FIXTURE_SOURCE_SHA,
  gitopsSha: FIXTURE_GITOPS_SHA,
  dataVersion: FIXTURE_DATA_VERSION,
  modelVersion: FIXTURE_MODEL_VERSION,
  agentVersion: FIXTURE_AGENT_VERSION,
  runId: "run-20250522-0846",
};

export const CACHED_FIXTURE_PROVENANCE: Provenance = {
  ...LIVE_FIXTURE_PROVENANCE,
  freshness: "CACHED_RESULT",
  planeAvailability: "LIVE_UNAVAILABLE",
  cachedAt: FIXTURE_CACHED_AT,
  agentVersion: null,
};

/** Picks the right stamp for the caller's plane status in one place. */
export function fixtureProvenance(planeReady: boolean): Provenance {
  return planeReady ? LIVE_FIXTURE_PROVENANCE : CACHED_FIXTURE_PROVENANCE;
}
