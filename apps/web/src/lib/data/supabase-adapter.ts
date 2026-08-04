import "server-only";
import type { SupabaseClient } from "@supabase/supabase-js";
import type {
  AgentConversation,
  AgentRegistryView,
  AnalystOverview,
  CompanyDetail,
  CompanySearchResult,
  ModelComparison,
  OpsDashboard,
  Provenance,
  SavedReport,
  SavedReportList,
  SavedReportSummary,
  ViewState,
} from "@distresslens/contracts";
import {
  FixtureDataPort,
  copyFor,
  denied,
  guard,
} from "./fixture-adapter";
import { FIXTURE_DATA_VERSION, FIXTURE_SOURCE_SHA } from "./fixtures/provenance-fixtures";
import type { CompanySearchParams, DistressLensDataPort, RequestContext } from "./port";
import type { ProductRoute } from "../states/route-states";

/**
 * Supabase-backed data port for the surfaces Supabase owns.
 *
 * This is a composite, and it is deliberately narrow about what it calls real:
 *
 * - The Supabase schema owns exactly these tables: `saved_reports`,
 *   `evidence_session`, `evidence_session_transition`, `audit_log`,
 *   `outbox_events`, `profiles`, `session_transition_rule`. No tables exist for
 *   company records, SHAP explanations, search rows, agent registry, or the
 *   GitOps plane (planes, budgets, revision, pipelines, promotions,
 *   experiments, observability). Those belong to the ML and GitOps planes that
 *   are built in later phases.
 *
 * - So `listSavedReports` and `getSavedReport` read the real `saved_reports`
 *   table through an RLS-scoped request client, and stamp `origin: SUPABASE`.
 *
 * - Every other surface delegates to the deterministic reference fixtures,
 *   whose REFERENCE_FIXTURE provenance keeps a screenshot self-identifying.
 *   That includes `getOpsDashboard`: it mixes DB-owned session/audit rows with
 *   GitOps-plane rows that have no table, and a single `provenance.origin`
 *   cannot honestly claim both. Marking the whole dashboard SUPABASE would
 *   present fixture plane/budget numbers as real evidence, so the dashboard
 *   stays fixture-backed until the GitOps plane publishes.
 */

export class SupabaseDataPort implements DistressLensDataPort {
  private readonly fixture = new FixtureDataPort();

  constructor(private readonly client: SupabaseClient) {}

  async listSavedReports(context: RequestContext): Promise<ViewState<SavedReportList>> {
    const route: ProductRoute = "/reports";
    const rejection = guard<SavedReportList>(context, "analyst.query", route);
    if (rejection !== null) {
      return rejection;
    }

    let rows: readonly SavedReportRow[];
    try {
      const { data, error } = await this.client
        .from("saved_reports")
        .select("id, owner_id, company_id, payload, created_at")
        .order("created_at", { ascending: false });
      if (error !== null) {
        throw error;
      }
      rows = (data ?? []) as readonly SavedReportRow[];
    } catch {
      // A failing read surfaces an error state rather than blanking the page;
      // the caller can ask again. We never leak the underlying database error
      // text to the browser.
      return {
        state: "error",
        copy: copyFor(route, "error"),
        data: { reports: [], provenance: supabaseProvenance(nowIso()) },
      };
    }

    // Ownership is enforced by RLS (`owner_id = auth.uid()`), so rows here are
    // already the caller's. We still drop rows whose payload cannot be parsed,
    // because a malformed row must not render as an empty shell.
    const reports: readonly SavedReportSummary[] = rows
      .map((row) => parseReportRow(row))
      .filter((report): report is SavedReport => report !== null)
      .map((report) => ({
        id: report.id,
        company: report.detail.company,
        title: report.title,
        createdAt: report.createdAt,
        band: report.detail.band,
        distressProbability: report.detail.distressProbability,
        revokedAt: report.revokedAt,
      }));

    const data: SavedReportList = {
      reports,
      // The list-level stamp ages with the newest report; an empty read has no
      // row to age with, so it falls back to the request time rather than a
      // fabricated historical value.
      provenance: supabaseProvenance(reports[0]?.createdAt ?? nowIso()),
    };

    return reports.length === 0
      ? { state: "empty", copy: copyFor(route, "empty"), data }
      : { state: "success", data };
  }

  async getSavedReport(
    context: RequestContext,
    reportId: string,
  ): Promise<ViewState<SavedReport>> {
    const route: ProductRoute = "/reports/[id]";
    const rejection = guard<SavedReport>(context, "analyst.query", route);
    if (rejection !== null) {
      return rejection;
    }

    let row: SavedReportRow | null;
    try {
      const { data, error } = await this.client
        .from("saved_reports")
        .select("id, owner_id, company_id, payload, created_at")
        .eq("id", reportId)
        .maybeSingle();
      if (error !== null) {
        throw error;
      }
      row = (data as SavedReportRow | null) ?? null;
    } catch {
      return denied<SavedReport>(route);
    }

    const report = row === null ? null : parseReportRow(row);

    // RLS already scopes the row to the owner; a missing row and a row that is
    // not parseable answer the same way as one belonging to someone else — all
    // are "denied" so the caller cannot distinguish existence.
    return report === null ? denied<SavedReport>(route) : { state: "success", data: report };
  }

  // ----- Fixture-delegated surfaces (no Supabase tables exist for them yet) -----

  getAnalystOverview(context: RequestContext): Promise<ViewState<AnalystOverview>> {
    return this.fixture.getAnalystOverview(context);
  }

  searchCompanies(
    context: RequestContext,
    params: CompanySearchParams,
  ): Promise<ViewState<CompanySearchResult>> {
    return this.fixture.searchCompanies(context, params);
  }

  getCompanyDetail(context: RequestContext, ticker: string): Promise<ViewState<CompanyDetail>> {
    return this.fixture.getCompanyDetail(context, ticker);
  }

  getModelComparison(
    context: RequestContext,
    ticker: string,
  ): Promise<ViewState<ModelComparison>> {
    return this.fixture.getModelComparison(context, ticker);
  }

  getAgentConversation(
    context: RequestContext,
    conversationId: string,
  ): Promise<ViewState<AgentConversation>> {
    return this.fixture.getAgentConversation(context, conversationId);
  }

  getAgentRegistry(context: RequestContext): Promise<ViewState<AgentRegistryView>> {
    return this.fixture.getAgentRegistry(context);
  }

  getOpsDashboard(context: RequestContext): Promise<ViewState<OpsDashboard>> {
    // See the class doc for why this stays fixture-delegated.
    return this.fixture.getOpsDashboard(context);
  }
}

function nowIso(): string {
  return new Date().toISOString();
}

interface SavedReportRow {
  id: string;
  owner_id: string;
  company_id: string;
  payload: unknown;
  created_at: string;
}

/**
 * A stored report payload. `saved_reports.payload` carries the report display
 * fields; id, owner and creation time live in their own columns. The shape is
 * validated here rather than trusted from the row, because the payload crosses
 * a trust boundary and a malformed one must degrade, not throw across the page.
 */
interface SavedReportPayload {
  company: SavedReport["detail"]["company"];
  title: string;
  summary: string;
  detail: SavedReport["detail"];
  revokedAt: string | null;
}

function parseReportRow(row: SavedReportRow): SavedReport | null {
  const payload = row.payload as Partial<SavedReportPayload> | null;
  if (payload === null || typeof payload !== "object") {
    return null;
  }
  const { company, title, summary, detail, revokedAt } = payload;
  if (
    company === undefined ||
    typeof title !== "string" ||
    typeof summary !== "string" ||
    detail === undefined ||
    typeof company.ticker !== "string"
  ) {
    return null;
  }

  return {
    id: row.id,
    ownerId: row.owner_id,
    company,
    createdAt: row.created_at,
    title,
    summary,
    detail,
    revokedAt: revokedAt ?? null,
  };
}

/**
 * Provenance for a row read from the live Supabase `saved_reports` table.
 * `origin: SUPABASE` distinguishes it from the deterministic fixtures.
 *
 * A saved report is inherently a persisted snapshot, not a live inference, so
 * it is stamped CACHED_RESULT with `cachedAt` pinned to the report's own
 * `created_at` — the timestamp when the snapshot was stored, which is the only
 * honest age for the row.
 */
export function supabaseProvenance(cachedAt: string): Provenance {
  return {
    freshness: "CACHED_RESULT",
    planeAvailability: "LIVE_UNAVAILABLE",
    origin: "SUPABASE",
    cachedAt,
    sourceSha: FIXTURE_SOURCE_SHA,
    gitopsSha: null,
    dataVersion: FIXTURE_DATA_VERSION,
    modelVersion: null,
    agentVersion: null,
    runId: null,
  };
}