import { describe, expect, it } from "vitest";
import { validateProvenance } from "@distresslens/contracts";
import type { SupabaseClient } from "@supabase/supabase-js";
import { SupabaseDataPort, supabaseProvenance } from "./supabase-adapter";
import type { RequestContext } from "./port";

const analyst: RequestContext = {
  userId: "user-analyst",
  role: "analyst",
  aal: "aal1",
  planeReady: true,
};

const signedOut: RequestContext = {
  userId: null,
  role: null,
  aal: "aal1",
  planeReady: true,
};

const viewer: RequestContext = {
  userId: "user-viewer",
  role: "platform_viewer",
  aal: "aal2",
  planeReady: true,
};

const payload = {
  company: { ticker: "NVL", name: "Novaland", sector: "Bất động sản", exchange: "HOSE" },
  title: "Đánh giá rủi ro NVL – Q1/2025",
  summary: "Tóm tắt",
  detail: {
    company: { ticker: "NVL", name: "Novaland", sector: "Bất động sản", exchange: "HOSE" },
    distressProbability: 82.4,
    band: "HIGH",
    changeVsPriorRun: 3.2,
    confidence: 91.0,
    modelVersion: "DL-Score v2.1",
    trend: [],
    indicatorPeriods: [],
    indicators: [],
    shapDrivers: [],
    sources: [],
    provenance: {
      freshness: "CACHED_RESULT",
      planeAvailability: "LIVE_UNAVAILABLE",
      origin: "SUPABASE",
      cachedAt: "2025-05-22T09:10:00+07:00",
      sourceSha: "ee9b876",
      gitopsSha: null,
      dataVersion: "gold-2025-05-22",
      modelVersion: "DL-Score v2.1",
      agentVersion: null,
      runId: null,
    },
  },
  revokedAt: null,
};

const row = (overrides: Partial<Record<string, unknown>> = {}) => ({
  id: "rpt-db-1",
  owner_id: analyst.userId,
  company_id: "NVL",
  payload,
  created_at: "2025-05-22T09:10:00+07:00",
  ...overrides,
});

/** A minimal fake of the Supabase query chain the adapter drives. */
function mockClient(rows: unknown[] | Error, single: unknown = null) {
  const chain = {
    select: () => chain,
    order: () => chain,
    eq: () => chain,
    maybeSingle: () =>
      Promise.resolve(
        single instanceof Error ? { data: null, error: { message: single.message } } : { data: single, error: null },
      ),
    then: (resolve: (value: unknown) => unknown) =>
      resolve(
        rows instanceof Error
          ? { data: null, error: { message: rows.message } }
          : { data: rows, error: null },
      ),
  };

  return { from: () => chain };
}

describe("SupabaseDataPort saved reports", () => {
  it("blocks a signed-out caller before querying", async () => {
    const port = new SupabaseDataPort(mockClient([]) as unknown as SupabaseClient);
    const result = await port.listSavedReports(signedOut);
    expect(result.state).toBe("forbidden");
  });

  it("blocks a platform role from analyst reports", async () => {
    const port = new SupabaseDataPort(mockClient([]) as unknown as SupabaseClient);
    expect((await port.listSavedReports(viewer)).state).toBe("forbidden");
    expect((await port.getSavedReport(viewer, "rpt-db-1")).state).toBe("forbidden");
  });

  it("lists parsed rows owned by the caller with SUPABASE provenance", async () => {
    const port = new SupabaseDataPort(
      mockClient([row()]) as unknown as SupabaseClient,
    );
    const result = await port.listSavedReports(analyst);
    expect(result.state).toBe("success");
    if (result.state !== "success") return;
    expect(result.data.reports).toHaveLength(1);
    expect(result.data.reports[0]?.id).toBe("rpt-db-1");
    expect(result.data.reports[0]?.band).toBe("HIGH");
    expect(result.data.provenance.origin).toBe("SUPABASE");
    expect(validateProvenance(result.data.provenance)).toEqual([]);
  });

  it("returns an empty state when the caller owns no reports", async () => {
    const port = new SupabaseDataPort(mockClient([]) as unknown as SupabaseClient);
    const result = await port.listSavedReports(analyst);
    expect(result.state).toBe("empty");
  });

  it("drops rows whose payload cannot be parsed instead of rendering a shell", async () => {
    const malformed = row({ payload: { title: "missing everything else" } });
    const port = new SupabaseDataPort(mockClient([malformed]) as unknown as SupabaseClient);
    const result = await port.listSavedReports(analyst);
    expect(result.state).toBe("empty");
  });

  it("surfaces an error state when the database read fails", async () => {
    const port = new SupabaseDataPort(
      mockClient(new Error("relation does not exist")) as unknown as SupabaseClient,
    );
    const result = await port.listSavedReports(analyst);
    expect(result.state).toBe("error");
  });

  it("serves a report the caller owns", async () => {
    const port = new SupabaseDataPort(
      mockClient([], row()) as unknown as SupabaseClient,
    );
    const result = await port.getSavedReport(analyst, "rpt-db-1");
    expect(result.state).toBe("success");
    if (result.state !== "success") return;
    expect(result.data.ownerId).toBe(analyst.userId);
    expect(result.data.detail.band).toBe("HIGH");
  });

  it("denies a missing report and a read error identically", async () => {
    const missing = new SupabaseDataPort(mockClient([], null) as unknown as SupabaseClient);
    const failed = new SupabaseDataPort(
      mockClient([], new Error("boom")) as unknown as SupabaseClient,
    );
    const a = await missing.getSavedReport(analyst, "nope");
    const b = await failed.getSavedReport(analyst, "nope");
    expect(a.state).toBe("forbidden");
    expect(b.state).toBe("forbidden");
  });
});

describe("SupabaseDataPort delegation", () => {
  it("delegates analyst surfaces to the reference fixtures", async () => {
    const port = new SupabaseDataPort(mockClient([]) as unknown as SupabaseClient);
    const overview = await port.getAnalystOverview(analyst);
    expect(overview.state).toBe("success");
    if (overview.state !== "success") return;
    // The delegated surface stays self-identifying as reference data.
    expect(overview.data.provenance.origin).toBe("REFERENCE_FIXTURE");
  });

  it("keeps the ops dashboard fixture-backed so mixed data cannot be mislabeled", async () => {
    const port = new SupabaseDataPort(mockClient([]) as unknown as SupabaseClient);
    const dashboard = await port.getOpsDashboard(viewer);
    expect(dashboard.state).toBe("success");
    if (dashboard.state !== "success") return;
    expect(dashboard.data.provenance.origin).toBe("REFERENCE_FIXTURE");
  });
});

describe("supabaseProvenance", () => {
  it("stamps a SUPABASE cached result with the given age", () => {
    const stamp = supabaseProvenance("2025-05-22T09:10:00+07:00");
    expect(stamp.origin).toBe("SUPABASE");
    expect(stamp.freshness).toBe("CACHED_RESULT");
    expect(stamp.cachedAt).toBe("2025-05-22T09:10:00+07:00");
    expect(validateProvenance(stamp)).toEqual([]);
  });
});
