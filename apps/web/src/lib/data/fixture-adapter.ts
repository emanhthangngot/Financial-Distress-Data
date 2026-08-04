import {
  authorize,
  type AgentConversation,
  type AgentRegistryView,
  type AnalystOverview,
  type CompanyDetail,
  type CompanySearchResult,
  type EvidenceSessionView,
  type ModelComparison,
  type OpsDashboard,
  type SavedReport,
  type SavedReportList,
  type SavedReportSummary,
  type SessionAction,
  type ViewState,
} from "@distresslens/contracts";
import {
  ASSISTANT_STATE_COPY,
  ROUTE_STATE_COPY,
  type ProductRoute,
} from "../states/route-states";
import type { CompanySearchParams, DistressLensDataPort, RequestContext } from "./port";
import {
  FIXTURE_ALERTS,
  FIXTURE_ATTENTION_ROWS,
  FIXTURE_ATTENTION_TOTAL,
  FIXTURE_BAND_SUMMARIES,
  FIXTURE_MARKET_AVERAGE,
  FIXTURE_METHOD_NOTE,
  FIXTURE_SECTOR_RISKS,
} from "./fixtures/analyst-fixtures";
import {
  FIXTURE_COMPANY_DETAILS,
  FIXTURE_SEARCHABLE_ROWS,
} from "./fixtures/company-fixtures";
import {
  FIXTURE_AGENT_ID,
  FIXTURE_AGENT_MESSAGES,
  FIXTURE_CONVERSATION_ID,
  FIXTURE_REGISTRY_ENTRIES,
} from "./fixtures/agent-fixtures";
import {
  FIXTURE_AUDIT_EVENTS,
  FIXTURE_BUDGETS,
  FIXTURE_ENVIRONMENT_LABEL,
  FIXTURE_EXPERIMENTS,
  FIXTURE_NEXT_SESSION_AT,
  FIXTURE_PIPELINES,
  FIXTURE_PROMOTIONS,
  fixtureObservabilityLinks,
  fixturePlanes,
  fixtureRevision,
} from "./fixtures/ops-fixtures";
import { CACHED_FIXTURE_PROVENANCE, fixtureProvenance } from "./fixtures/provenance-fixtures";

/**
 * Deterministic adapter used by local development and the Playwright evidence
 * run. It applies the same authorization decision and the same plane-aware
 * degradation as the Supabase adapter; only the row source differs, so a state
 * proved here is the state the real adapter must also produce.
 */

/** Report the fixture user owns. Any other id resolves to forbidden. */
export const FIXTURE_REPORT_ID = "rpt-20250522-nvl";
export const FIXTURE_USER_ID = "fixture-analyst";

/** Shared by both adapters so the authorization decision cannot drift. */
export function copyFor(route: ProductRoute, state: keyof (typeof ROUTE_STATE_COPY)[ProductRoute]) {
  const copy = ROUTE_STATE_COPY[route][state];
  if (copy === undefined) {
    // A route rendering a state it never wrote copy for is a contract bug, not
    // a runtime condition to paper over.
    throw new Error(`route ${route} has no copy for state ${String(state)}`);
  }
  return copy;
}

export function assistantCopyFor(state: keyof typeof ASSISTANT_STATE_COPY) {
  const copy = ASSISTANT_STATE_COPY[state];
  if (copy === undefined) {
    throw new Error(`assistant has no copy for state ${String(state)}`);
  }
  return copy;
}

export function denied<T>(route: ProductRoute): ViewState<T> {
  return { state: "forbidden", copy: copyFor(route, "forbidden"), data: null };
}

export function guard<T>(
  context: RequestContext,
  action: SessionAction,
  route: ProductRoute,
): ViewState<T> | null {
  return authorize({ role: context.role, aal: context.aal }, action).allowed
    ? null
    : denied<T>(route);
}

function fixtureSession(planeReady: boolean): EvidenceSessionView {
  if (!planeReady) {
    return {
      id: null,
      state: "OFF",
      version: 1,
      actor: null,
      leaseExpiry: null,
      costSnapshotUsd: null,
      gitSha: null,
      updatedAt: "2025-05-22T18:32:00+07:00",
      history: [],
    };
  }

  return {
    id: "ev-20250522-1000",
    state: "READY",
    version: 4,
    actor: "minhanh.nguyen",
    leaseExpiry: "2025-05-22T20:00:00+07:00",
    costSnapshotUsd: 12.5,
    gitSha: "a1b2c3d",
    updatedAt: "2025-05-22T18:32:00+07:00",
    history: [
      {
        fromState: "SYNCING",
        toState: "READY",
        version: 4,
        actor: "minhanh.nguyen",
        occurredAt: "2025-05-22T18:32:00+07:00",
      },
      {
        fromState: "PROVISIONING",
        toState: "SYNCING",
        version: 3,
        actor: "minhanh.nguyen",
        occurredAt: "2025-05-22T18:18:00+07:00",
      },
      {
        fromState: "REQUESTED",
        toState: "PROVISIONING",
        version: 2,
        actor: "minhanh.nguyen",
        occurredAt: "2025-05-22T18:02:00+07:00",
      },
      {
        fromState: "OFF",
        toState: "REQUESTED",
        version: 1,
        actor: "minhanh.nguyen",
        occurredAt: "2025-05-22T17:58:00+07:00",
      },
    ],
  };
}

function buildSavedReport(detail: CompanyDetail): SavedReport {
  return {
    id: FIXTURE_REPORT_ID,
    ownerId: FIXTURE_USER_ID,
    company: detail.company,
    createdAt: "2025-05-22T09:10:00+07:00",
    title: `Đánh giá rủi ro ${detail.company.ticker} – Q1/2025`,
    summary: `Xác suất distress ${detail.distressProbability}% (${detail.modelVersion}), tăng ${detail.changeVsPriorRun} điểm % so với kỳ trước.`,
    detail: { ...detail, provenance: CACHED_FIXTURE_PROVENANCE },
    revokedAt: null,
  };
}

export class FixtureDataPort implements DistressLensDataPort {
  async getAnalystOverview(context: RequestContext): Promise<ViewState<AnalystOverview>> {
    const rejection = guard<AnalystOverview>(context, "analyst.query", "/");
    if (rejection !== null) {
      return rejection;
    }

    const data: AnalystOverview = {
      bandSummaries: FIXTURE_BAND_SUMMARIES,
      attention: FIXTURE_ATTENTION_ROWS,
      attentionTotal: FIXTURE_ATTENTION_TOTAL,
      alerts: FIXTURE_ALERTS,
      sectorRisks: FIXTURE_SECTOR_RISKS,
      marketAverageProbability: FIXTURE_MARKET_AVERAGE,
      methodNote: FIXTURE_METHOD_NOTE,
      provenance: fixtureProvenance(context.planeReady),
    };

    // The overview stays fully readable with the plane off; it is the live
    // labels that change, not the content.
    return context.planeReady
      ? { state: "success", data }
      : { state: "degraded", copy: copyFor("/", "degraded"), data };
  }

  async searchCompanies(
    context: RequestContext,
    params: CompanySearchParams,
  ): Promise<ViewState<CompanySearchResult>> {
    const rejection = guard<CompanySearchResult>(context, "analyst.query", "/companies");
    if (rejection !== null) {
      return rejection;
    }

    const needle = params.query.trim().toLowerCase();
    const matched =
      needle === ""
        ? FIXTURE_SEARCHABLE_ROWS
        : FIXTURE_SEARCHABLE_ROWS.filter(
            (row) =>
              row.ticker.toLowerCase().includes(needle) ||
              row.name.toLowerCase().includes(needle) ||
              row.sector.toLowerCase().includes(needle),
          );

    const start = (params.page - 1) * params.pageSize;
    const data: CompanySearchResult = {
      rows: matched.slice(start, start + params.pageSize),
      total: needle === "" ? FIXTURE_ATTENTION_TOTAL : matched.length,
      query: params.query,
      provenance: fixtureProvenance(context.planeReady),
    };

    if (matched.length === 0) {
      return { state: "empty", copy: copyFor("/companies", "empty"), data };
    }

    return context.planeReady
      ? { state: "success", data }
      : { state: "stale", copy: copyFor("/companies", "stale"), data };
  }

  async getCompanyDetail(
    context: RequestContext,
    ticker: string,
  ): Promise<ViewState<CompanyDetail>> {
    const route: ProductRoute = "/companies/[ticker]";
    const rejection = guard<CompanyDetail>(context, "analyst.query", route);
    if (rejection !== null) {
      return rejection;
    }

    const detail = FIXTURE_COMPANY_DETAILS[ticker.toUpperCase()];
    if (detail === undefined) {
      return { state: "empty", copy: copyFor(route, "empty"), data: null };
    }

    if (!context.planeReady) {
      // Cached row, explicitly stamped: the page shows the saved score and says
      // live inference is unavailable rather than implying a fresh run.
      return {
        state: "degraded",
        copy: copyFor(route, "degraded"),
        data: { ...detail, provenance: CACHED_FIXTURE_PROVENANCE },
      };
    }

    return { state: "success", data: detail };
  }

  async getModelComparison(
    context: RequestContext,
    ticker: string,
  ): Promise<ViewState<ModelComparison>> {
    const rejection = guard<ModelComparison>(context, "analyst.query", "/compare");
    if (rejection !== null) {
      return rejection;
    }

    const detail = FIXTURE_COMPANY_DETAILS[ticker.toUpperCase()];
    if (detail === undefined) {
      return {
        state: "empty",
        copy: copyFor("/compare", "empty"),
        data: null,
      };
    }

    const data: ModelComparison = {
      ticker: detail.company.ticker,
      candidate: {
        modelVersion: "DL-Score v2.2.0",
        distressProbability: 81.4,
        band: "HIGH",
        confidence: 76,
        topDrivers: detail.shapDrivers.slice(0, 3),
      },
      baseline: {
        modelVersion: detail.modelVersion,
        distressProbability: detail.distressProbability,
        band: detail.band,
        confidence: detail.confidence,
        topDrivers: detail.shapDrivers.slice(0, 3),
      },
      provenance: fixtureProvenance(context.planeReady),
    };

    return { state: "success", data };
  }

  async listSavedReports(context: RequestContext): Promise<ViewState<SavedReportList>> {
    const route: ProductRoute = "/reports";
    const rejection = guard<SavedReportList>(context, "analyst.query", route);
    if (rejection !== null) {
      return rejection;
    }

    const detail = FIXTURE_COMPANY_DETAILS.NVL;
    const report = detail === undefined ? null : buildSavedReport(detail);

    // Only the caller's own reports. Ownership is filtered here as well as in
    // RLS so the fixture adapter cannot prove a state the database would deny.
    const reports: readonly SavedReportSummary[] =
      report === null || report.ownerId !== context.userId
        ? []
        : [
            {
              id: report.id,
              company: report.company,
              title: report.title,
              createdAt: report.createdAt,
              band: report.detail.band,
              distressProbability: report.detail.distressProbability,
              revokedAt: report.revokedAt,
            },
          ];

    const data: SavedReportList = {
      reports,
      provenance: fixtureProvenance(context.planeReady),
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
    // Reading a saved report is a query; `analyst.save_report` governs writing
    // one. Row ownership is checked separately below.
    const rejection = guard<SavedReport>(context, "analyst.query", route);
    if (rejection !== null) {
      return rejection;
    }

    const detail = FIXTURE_COMPANY_DETAILS.NVL;
    if (reportId !== FIXTURE_REPORT_ID || detail === undefined) {
      // Unknown and not-yours are the same answer on purpose: distinguishing
      // them would confirm the report exists.
      return denied<SavedReport>(route);
    }

    const report = buildSavedReport(detail);
    if (report.ownerId !== context.userId) {
      return denied<SavedReport>(route);
    }

    return { state: "success", data: report };
  }

  async getAgentConversation(
    context: RequestContext,
    conversationId: string,
  ): Promise<ViewState<AgentConversation>> {
    // The assistant is a floating surface, not a route, so its state copy comes
    // from the assistant catalog rather than the route catalog.
    if (!authorize({ role: context.role, aal: context.aal }, "analyst.run_ai_request").allowed) {
      return {
        state: "forbidden",
        copy: assistantCopyFor("forbidden"),
        data: null,
      };
    }

    const data: AgentConversation = {
      id: conversationId === "" ? FIXTURE_CONVERSATION_ID : conversationId,
      agentId: FIXTURE_AGENT_ID,
      messages: FIXTURE_AGENT_MESSAGES,
      provenance: fixtureProvenance(context.planeReady),
    };

    // Bounded SSE only runs against a READY plane; with it off the analyst sees
    // saved answers and is told why nothing new can be asked.
    return context.planeReady
      ? { state: "success", data }
      : {
          state: "degraded",
          copy: assistantCopyFor("degraded"),
          data: { ...data, provenance: CACHED_FIXTURE_PROVENANCE },
        };
  }

  async getAgentRegistry(context: RequestContext): Promise<ViewState<AgentRegistryView>> {
    const route: ProductRoute = "/agents/registry";
    const rejection = guard<AgentRegistryView>(context, "session.read", route);
    if (rejection !== null) {
      return rejection;
    }

    const data: AgentRegistryView = {
      entries: context.planeReady
        ? FIXTURE_REGISTRY_ENTRIES
        : FIXTURE_REGISTRY_ENTRIES.map((entry) => ({
            ...entry,
            // Replica counts are a live-plane reading; with EKS off they are
            // unknown, and zeroing them would read as "scaled to zero".
            replicas: { ...entry.replicas, ready: 0, lastHeartbeatAt: null },
          })),
      provenance: fixtureProvenance(context.planeReady),
    };

    return context.planeReady
      ? { state: "success", data }
      : { state: "degraded", copy: copyFor(route, "degraded"), data };
  }

  async getOpsDashboard(context: RequestContext): Promise<ViewState<OpsDashboard>> {
    const route: ProductRoute = "/ops/evidence";
    const rejection = guard<OpsDashboard>(context, "session.read", route);
    if (rejection !== null) {
      return rejection;
    }

    const data: OpsDashboard = {
      environmentLabel: FIXTURE_ENVIRONMENT_LABEL,
      planes: fixturePlanes(context.planeReady),
      budgets: FIXTURE_BUDGETS,
      session: fixtureSession(context.planeReady),
      nextSessionAt: FIXTURE_NEXT_SESSION_AT,
      revision: fixtureRevision(context.planeReady),
      pipelines: FIXTURE_PIPELINES,
      promotions: FIXTURE_PROMOTIONS,
      experiments: FIXTURE_EXPERIMENTS,
      auditEvents: FIXTURE_AUDIT_EVENTS,
      observability: fixtureObservabilityLinks(context.planeReady),
      provenance: fixtureProvenance(context.planeReady),
    };

    return context.planeReady
      ? { state: "success", data }
      : { state: "degraded", copy: copyFor(route, "degraded"), data };
  }
}
