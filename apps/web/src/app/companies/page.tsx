import type { CompanySearchResult } from "@distresslens/contracts";
import { CompanyRiskTable } from "@/components/company/company-risk-table";
import { PageHeader } from "@/components/dashboard/page-header";
import { AnalystShell } from "@/components/shell/analyst-shell";
import { ButtonLink } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { DenialAction } from "@/components/ui/denial-action";
import { StatePanel } from "@/components/ui/state-panel";
import type { AssistantContext } from "@/lib/assistant/assistant-context";
import { getDataPort } from "@/lib/data";
import { LIVE_FIXTURE_PROVENANCE } from "@/lib/data/fixtures/provenance-fixtures";
import { resolveSession } from "@/lib/server/session";
import { LOADING_COPY } from "@/lib/states/loading-copy";
import { isFailureState, viewCopy, viewData } from "@/lib/states/view-state";

/**
 * Company search and portfolio browse.
 *
 * The query lives in the URL rather than component state: it survives a reload,
 * can be shared with a colleague, and makes every search state reproducible in
 * a screenshot for the evidence run.
 */

export const dynamic = "force-dynamic";

const PAGE_SIZE = 20;

export default async function CompaniesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; page?: string }>;
}) {
  const { user, context, accessToken } = await resolveSession();
  const { q = "", page } = await searchParams;
  const pageNumber = Number.parseInt(page ?? "1", 10);

  const result = await getDataPort(accessToken).searchCompanies(context, {
    query: q,
    page: Number.isFinite(pageNumber) && pageNumber > 0 ? pageNumber : 1,
    pageSize: PAGE_SIZE,
  });

  const data: CompanySearchResult | null = viewData(result);
  const copy = viewCopy(result, LOADING_COPY.companies);
  const provenance = data?.provenance ?? LIVE_FIXTURE_PROVENANCE;

  const assistantContext: AssistantContext = {
    scope: "portfolio",
    route: "/companies",
    surfaceLabel: q === "" ? "Danh sách doanh nghiệp" : `Tìm kiếm: ${q}`,
    ticker: null,
    selectedTickers: [],
    periodLabel: null,
    filters: q === "" ? [] : [`từ khóa: ${q}`],
    dataVersion: provenance.dataVersion,
    modelVersion: provenance.modelVersion,
  };

  return (
    <AnalystShell
      user={user}
      provenance={provenance}
      syncedAtLabel="23/05/2025 08:46"
      assistantContext={assistantContext}
      searchDefaultValue={q}
    >
      <div className="flex flex-col gap-5">
        <PageHeader
          title="Doanh nghiệp"
          description="Tra cứu và so sánh mức rủi ro tài chính của các doanh nghiệp đang được theo dõi"
          freshnessLabel={`Kỳ dữ liệu ${provenance.dataVersion} · Cập nhật 23/05/2025 08:46`}
        />

        {/* A denial or a hard failure replaces the results entirely: there is no
            partial list to show, and an empty table would read as "no matches". */}
        {data === null ? (
          <StatePanel
            copy={copy ?? LOADING_COPY.companies}
            tone={isFailureState(result) ? "critical" : "neutral"}
            action={<DenialAction state={result.state} context={context} reloadHref="/companies" />}
          />
        ) : (
          <>
            {result.state === "stale" ? <StatePanel copy={result.copy} tone="warning" /> : null}

            <Card>
              <CardHeader
                title={q === "" ? "Toàn bộ danh mục theo dõi" : `Kết quả cho “${q}”`}
                description={
                  result.state === "empty"
                    ? "Không có doanh nghiệp nào khớp từ khóa hiện tại"
                    : `${data.total} doanh nghiệp, xếp theo xác suất distress giảm dần`
                }
              />
              <CardBody>
                <CompanyRiskTable
                  rows={data.rows}
                  caption={`Kết quả tìm kiếm doanh nghiệp cho từ khóa “${q}”`}
                  emptyTitle={result.state === "empty" ? result.copy.unavailable : "Danh mục trống"}
                  emptyDescription={
                    result.state === "empty"
                      ? result.copy.nextAction
                      : "Chưa có doanh nghiệp nào được thêm vào danh mục theo dõi."
                  }
                  emptyAction={
                    <ButtonLink href="/companies" variant="secondary">
                      Xóa bộ lọc
                    </ButtonLink>
                  }
                  footer={
                    data.rows.length > 0
                      ? `Đang hiển thị ${data.rows.length} trong ${data.total} doanh nghiệp.`
                      : undefined
                  }
                />
              </CardBody>
            </Card>
          </>
        )}
      </div>
    </AnalystShell>
  );
}
