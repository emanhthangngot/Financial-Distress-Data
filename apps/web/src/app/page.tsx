import type { AnalystOverview } from "@distresslens/contracts";
import { AlertTimeline } from "@/components/dashboard/alert-timeline";
import { CompanyRiskTable, ShowingCount } from "@/components/company/company-risk-table";
import { MetricCard } from "@/components/dashboard/metric-card";
import { PageHeader, PeriodFilter } from "@/components/dashboard/page-header";
import { RiskDistribution } from "@/components/dashboard/risk-distribution";
import { SectorRiskChart } from "@/components/dashboard/sector-risk-chart";
import { AnalystShell } from "@/components/shell/analyst-shell";
import { DisclaimerBanner } from "@/components/shell/disclaimer-banner";
import { ButtonLink } from "@/components/ui/button";
import { Card, CardBody, CardFooter, CardHeader } from "@/components/ui/card";
import { StatePanel } from "@/components/ui/state-panel";
import type { AssistantContext } from "@/lib/assistant/assistant-context";
import { getDataPort } from "@/lib/data";
import { LIVE_FIXTURE_PROVENANCE } from "@/lib/data/fixtures/provenance-fixtures";
import { resolveSession } from "@/lib/server/session";
import { LOADING_COPY } from "@/lib/states/loading-copy";

/**
 * Analyst overview: the state of the monitored portfolio, and what to look at
 * first.
 *
 * The page reads through the data port, so authorization and plane degradation
 * are decided on the server. A denial or a failure renders the route's state
 * copy in place of the sections it would have filled — there is no path here
 * that leaves the analyst looking at an empty canvas.
 */

/**
 * Rendered per request, never prerendered: what this page shows depends on who
 * is asking and whether the evidence plane is up, and a build-time snapshot of
 * one analyst's portfolio would be both wrong and a data leak.
 */
export const dynamic = "force-dynamic";

const PERIOD_OPTIONS = [
  { value: "7d", label: "7 ngày" },
  { value: "30d", label: "30 ngày" },
  { value: "90d", label: "90 ngày" },
] as const;

export default async function OverviewPage({
  searchParams,
}: {
  searchParams: Promise<{ period?: string }>;
}) {
  const { user, context } = await resolveSession();
  const { period } = await searchParams;
  const selectedPeriod =
    PERIOD_OPTIONS.find((option) => option.value === period) ?? PERIOD_OPTIONS[1];

  const overview = await getDataPort().getAnalystOverview(context);
  const data: AnalystOverview | null =
    overview.state === "success" ? overview.data : (overview.state === "loading" ? null : overview.data);
  const provenance = data?.provenance ?? LIVE_FIXTURE_PROVENANCE;

  const assistantContext: AssistantContext = {
    scope: "portfolio",
    route: "/",
    surfaceLabel: "Tổng quan danh mục",
    ticker: null,
    selectedTickers: [],
    periodLabel: selectedPeriod.label,
    filters: [],
    dataVersion: provenance.dataVersion,
    modelVersion: provenance.modelVersion,
  };

  return (
    <AnalystShell
      user={user}
      provenance={provenance}
      syncedAtLabel="23/05/2025 08:46"
      assistantContext={assistantContext}
    >
      <div className="flex flex-col gap-5">
        <PageHeader
          title="Tổng quan danh mục"
          description="Theo dõi và đánh giá rủi ro tài chính của danh mục doanh nghiệp niêm yết"
          freshnessLabel={`Cập nhật lần cuối 23/05/2025 08:46 · Kỳ dữ liệu ${provenance.dataVersion}`}
          controls={<PeriodFilter value={selectedPeriod.value} options={PERIOD_OPTIONS} />}
          primaryAction={
            <ButtonLink href="/reports" variant="primary">
              Xuất báo cáo
            </ButtonLink>
          }
        />

        <DisclaimerBanner surface="company" />

        {overview.state !== "success" && data === null ? (
          <StatePanel
            copy={overview.state === "loading" ? LOADING_COPY.overview : overview.copy}
            tone={overview.state === "error" ? "critical" : "neutral"}
            action={
              <ButtonLink href="/" variant="secondary">
                Tải lại trang
              </ButtonLink>
            }
          />
        ) : null}

        {data !== null ? (
          <>
            {overview.state !== "success" && overview.state !== "loading" ? (
              <StatePanel copy={overview.copy} tone="warning" />
            ) : null}

            {/* Four across on a desktop canvas, two on a tablet, one on a
                phone: two 180px columns turn the change line into three
                wrapped fragments. */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard
                label="Doanh nghiệp theo dõi"
                value={String(data.attentionTotal)}
                change={null}
                comparisonLabel="so với tuần trước"
                intent="rising-is-good"
                explanation="Số doanh nghiệp niêm yết đang được chấm điểm trong kỳ dữ liệu hiện tại."
                href="/companies"
                drillDownLabel="Xem danh mục"
              />
              {data.bandSummaries.map((summary) => (
                <MetricCard
                  key={summary.band}
                  label={BAND_METRIC_LABEL[summary.band]}
                  value={String(summary.companyCount)}
                  unit="doanh nghiệp"
                  change={summary.changeVsPriorWeek}
                  changeUnit=" doanh nghiệp"
                  comparisonLabel="so với tuần trước"
                  intent={summary.band === "STABLE" ? "rising-is-good" : "rising-is-bad"}
                  explanation={BAND_METRIC_EXPLANATION[summary.band]}
                  href="/companies"
                  drillDownLabel="Xem doanh nghiệp"
                />
              ))}
            </div>

            {/* Charts and the alert rail share a row; the attention table gets
                the full canvas below them, because eight comparable columns in
                a 7fr column wrap into unreadable two-line cells. */}
            <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
              <Card>
                <CardHeader
                  title="Rủi ro theo ngành"
                  description="Xác suất distress trung bình của từng ngành trong kỳ dữ liệu hiện tại"
                />
                <CardBody>
                  <SectorRiskChart
                    sectors={data.sectorRisks}
                    marketAverage={data.marketAverageProbability}
                  />
                </CardBody>
                <CardFooter>{data.methodNote}</CardFooter>
              </Card>

              <div className="flex flex-col gap-4">
                <Card>
                  <CardHeader
                    title="Phân bố nhóm rủi ro"
                    description="Tỷ trọng danh mục theo nhóm rủi ro và thay đổi so với tuần trước"
                  />
                  <CardBody>
                    <RiskDistribution summaries={data.bandSummaries} />
                  </CardBody>
                </Card>

                <Card>
                  <CardHeader
                    title="Cảnh báo gần đây"
                    description="Thay đổi rủi ro phát hiện ở lần chấm điểm gần nhất"
                  />
                  <CardBody>
                    <AlertTimeline alerts={data.alerts} />
                  </CardBody>
                </Card>
              </div>
            </div>

            <Card>
              <CardHeader
                title="Doanh nghiệp cần chú ý"
                description="Xếp theo xác suất distress giảm dần trong kỳ dữ liệu hiện tại"
                action={
                  <ButtonLink href="/companies" variant="secondary">
                    Xem tất cả
                  </ButtonLink>
                }
              />
              <CardBody>
                <CompanyRiskTable
                  rows={data.attention}
                  caption="Doanh nghiệp cần chú ý, xếp theo xác suất distress giảm dần"
                  emptyTitle="Không có doanh nghiệp nào cần chú ý"
                  emptyDescription="Không doanh nghiệp nào trong danh mục vượt ngưỡng cảnh báo ở kỳ dữ liệu này."
                  footer={
                    <ShowingCount shown={data.attention.length} total={data.attentionTotal} />
                  }
                />
              </CardBody>
            </Card>
          </>
        ) : null}
      </div>
    </AnalystShell>
  );
}

const BAND_METRIC_LABEL: Record<string, string> = {
  HIGH: "Nguy cơ cao",
  WATCH: "Cần theo dõi",
  STABLE: "Ổn định",
};

const BAND_METRIC_EXPLANATION: Record<string, string> = {
  HIGH: "Doanh nghiệp có xác suất distress vượt ngưỡng cảnh báo của mô hình trong kỳ dữ liệu hiện tại.",
  WATCH:
    "Doanh nghiệp chưa vượt ngưỡng cảnh báo nhưng có chỉ tiêu tài chính đang xấu đi so với kỳ trước.",
  STABLE: "Doanh nghiệp có xác suất distress ở mức thấp và không có tín hiệu suy giảm đáng kể.",
};
