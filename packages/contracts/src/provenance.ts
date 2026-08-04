/**
 * Provenance is the anti-lying contract. Every displayed number carries where it
 * came from and whether the live inference plane actually produced it, so a
 * cached row can never be mistaken for a fresh KServe or agent run.
 */

export const RESULT_FRESHNESS = ["LIVE", "CACHED_RESULT"] as const;
export type ResultFreshness = (typeof RESULT_FRESHNESS)[number];

export const PLANE_AVAILABILITY = ["LIVE_AVAILABLE", "LIVE_UNAVAILABLE"] as const;
export type PlaneAvailability = (typeof PLANE_AVAILABILITY)[number];

/**
 * Marks data that came from the deterministic reference fixtures rather than a
 * real query. Rendered as a visible badge: a screenshot of fixture data must
 * never be filed as executed evidence.
 */
export const REFERENCE_FIXTURE = "REFERENCE_FIXTURE" as const;
export type DataOrigin = typeof REFERENCE_FIXTURE | "SUPABASE" | "EVIDENCE_PLANE";

export interface Provenance {
  freshness: ResultFreshness;
  planeAvailability: PlaneAvailability;
  origin: DataOrigin;
  /** ISO timestamp the cached row was produced. Required when CACHED_RESULT. */
  cachedAt: string | null;
  /** Commit of this repository that produced the result. */
  sourceSha: string;
  /** Commit of the GitOps control repository, when the evidence plane was involved. */
  gitopsSha: string | null;
  dataVersion: string;
  modelVersion: string | null;
  agentVersion: string | null;
  runId: string | null;
}

const SHA_PATTERN = /^[0-9a-f]{7,40}$/;

/**
 * Returns the reasons a provenance record is untrustworthy, empty when valid.
 * Returning reasons rather than throwing lets a route render a degraded state
 * naming the missing field instead of blanking the page.
 */
export function validateProvenance(provenance: Provenance): string[] {
  const problems: string[] = [];

  if (provenance.freshness === "CACHED_RESULT" && provenance.cachedAt === null) {
    problems.push("CACHED_RESULT requires cachedAt so the reader knows how old the row is");
  }

  // A live result while the plane is down is the exact lie this contract exists
  // to prevent.
  if (provenance.freshness === "LIVE" && provenance.planeAvailability === "LIVE_UNAVAILABLE") {
    problems.push("LIVE result cannot be claimed while the plane is LIVE_UNAVAILABLE");
  }

  if (!SHA_PATTERN.test(provenance.sourceSha)) {
    problems.push(`sourceSha ${provenance.sourceSha} is not a hex commit sha`);
  }

  if (provenance.gitopsSha !== null && !SHA_PATTERN.test(provenance.gitopsSha)) {
    problems.push(`gitopsSha ${provenance.gitopsSha} is not a hex commit sha`);
  }

  if (provenance.dataVersion.trim() === "") {
    problems.push("dataVersion is required");
  }

  return problems;
}

export function isCached(provenance: Provenance): boolean {
  return provenance.freshness === "CACHED_RESULT";
}

/**
 * The badges a surface must render for this provenance. Both labels appear
 * together when the plane is off: one states the row is cached, the other
 * states live inference is unavailable, and neither implies the other.
 */
export function provenanceLabels(provenance: Provenance): readonly string[] {
  const labels: string[] = [];
  if (provenance.freshness === "CACHED_RESULT") {
    labels.push("CACHED_RESULT");
  }
  if (provenance.planeAvailability === "LIVE_UNAVAILABLE") {
    labels.push("LIVE_UNAVAILABLE");
  }
  if (provenance.origin === REFERENCE_FIXTURE) {
    labels.push(REFERENCE_FIXTURE);
  }
  return labels;
}
