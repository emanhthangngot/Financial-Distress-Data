import "server-only";
import { FixtureDataPort } from "./fixture-adapter";
import type { DistressLensDataPort } from "./port";

export type { DistressLensDataPort, RequestContext, CompanySearchParams } from "./port";

/**
 * Adapter selection. Routes call `getDataPort()` and never import an adapter
 * directly, so the Supabase implementation drops in here without touching a
 * single page.
 */
export function getDataPort(): DistressLensDataPort {
  if (process.env.DISTRESSLENS_DATA_SOURCE === "fixture") {
    return new FixtureDataPort();
  }

  throw new Error(
    "no data adapter configured: set DISTRESSLENS_DATA_SOURCE=fixture for local/evidence runs",
  );
}
