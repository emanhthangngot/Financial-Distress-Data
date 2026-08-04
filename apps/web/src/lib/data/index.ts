import "server-only";
import { FixtureDataPort } from "./fixture-adapter";
import type { DistressLensDataPort } from "./port";
import { SupabaseDataPort } from "./supabase-adapter";
import { createRequestClient, isSupabaseConfigured } from "../server/supabase";

export type { DistressLensDataPort, RequestContext, CompanySearchParams } from "./port";

/**
 * Adapter selection. Routes call `getDataPort(accessToken)` and never import an
 * adapter directly, so adding a data source only touches this function.
 *
 * Ordering is deliberate:
 *
 * - `fixture` is the explicit opt-in for local development and the Playwright
 *   evidence run; it needs a deterministic identity and no live project.
 * - Otherwise, if Supabase is configured, routes read through the live
 *   RLS-scoped adapter for the surfaces Supabase owns (saved reports) and the
 *   reference fixtures for everything else.
 * - A deployment with neither is a configuration error, surfaced loudly rather
 *   than silently served synthetic data.
 */
export function getDataPort(accessToken: string | null = null): DistressLensDataPort {
  if (process.env.DISTRESSLENS_DATA_SOURCE === "fixture") {
    return new FixtureDataPort();
  }

  if (isSupabaseConfigured()) {
    return new SupabaseDataPort(createRequestClient(accessToken));
  }

  throw new Error(
    "no data adapter configured: set DISTRESSLENS_DATA_SOURCE=fixture for local/evidence runs, or configure Supabase env vars",
  );
}