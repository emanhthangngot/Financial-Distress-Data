import type {
  AgentConversation,
  AgentRegistryView,
  AnalystOverview,
  CompanyDetail,
  CompanySearchResult,
  ModelComparison,
  OpsDashboard,
  Role,
  SavedReport,
  SavedReportList,
  ViewState,
} from "@distresslens/contracts";

/**
 * The single data boundary the routes read through. Two adapters implement it:
 * the deterministic reference fixtures and the Supabase/RLS client. Routes never
 * import an adapter directly, so swapping the source cannot change what a page
 * is allowed to show.
 *
 * Every method returns a `ViewState`, not a bare value: forbidden, stale and
 * degraded are decided on the server where the role and plane status are known,
 * rather than inferred in the browser from a missing field.
 */

export interface RequestContext {
  userId: string | null;
  role: Role | null;
  aal: "aal1" | "aal2";
  /** False when the EKS evidence plane is unreachable. */
  planeReady: boolean;
}

export interface CompanySearchParams {
  query: string;
  page: number;
  pageSize: number;
}

export interface DistressLensDataPort {
  getAnalystOverview(context: RequestContext): Promise<ViewState<AnalystOverview>>;

  searchCompanies(
    context: RequestContext,
    params: CompanySearchParams,
  ): Promise<ViewState<CompanySearchResult>>;

  getCompanyDetail(context: RequestContext, ticker: string): Promise<ViewState<CompanyDetail>>;

  getModelComparison(
    context: RequestContext,
    ticker: string,
  ): Promise<ViewState<ModelComparison>>;

  listSavedReports(context: RequestContext): Promise<ViewState<SavedReportList>>;

  getSavedReport(context: RequestContext, reportId: string): Promise<ViewState<SavedReport>>;

  getAgentConversation(
    context: RequestContext,
    conversationId: string,
  ): Promise<ViewState<AgentConversation>>;

  getAgentRegistry(context: RequestContext): Promise<ViewState<AgentRegistryView>>;

  getOpsDashboard(context: RequestContext): Promise<ViewState<OpsDashboard>>;
}
