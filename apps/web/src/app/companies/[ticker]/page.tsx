import type { CompanyDetail } from "@distresslens/contracts";
import Link from "next/link";
import { IndicatorTable } from "@/components/company/indicator-table";
import { ProvenancePanel } from "@/components/company/provenance-panel";
import { RiskKpiStrip } from "@/components/company/risk-kpi-strip";
import { ShapChart } from "@/components/company/shap-chart";
import { SourceList } from "@/components/company/source-list";
import { TrendChart } from "@/components/company/trend-chart";
import { AnalystShell } from "@/components/shell/analyst-shell";
import { DisclaimerBanner } from "@/components/shell/disclaimer-banner";
import { ButtonLink } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { StatePanel } from "@/components/ui/state-panel";
import type { AssistantContext } from "@/lib/assistant/assistant-context";
import { getDataPort } from "@/lib/data";
import { LIVE_FIXTURE_PROVENANCE } from "@/lib/data/fixtures/provenance-fixtures";
import { resolveSession } from "@/lib/server/session";
import { LOADING_COPY } from "@/lib/states/loading-copy";
import { isFailureState, viewCopy, viewData } from "@/lib/states/view-state";

/**
 * Company risk detail — the decision surface.
 *
 * The order is deliberate: the verdict, then the trend that produced it, then
 * the indicators behind the trend, then the model's own attribution, then the
 * documents all of it came from. An analyst reading top to bottom moves from
 * conclusion to evidence, and can stop wherever they are convinced.
 *
 * With the evidence plane off the page still renders — from the saved result,
 * labelled as saved. That is the whole point of the degraded state: a risk
 * product that goes blank when inference is down is useless exactly when
 * someone needs the last known number.
 */

export const dynamic = "force-dynamic";

export default async function CompanyDetailPage({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { user, context } = await resolveSession();
  const { ticker } = await params;

  const result = await getDataPort().getCompanyDetail(context, ticker);
  const detail: CompanyDetail | null = viewData(result);
  const copy = viewCopy(result, LOADING_COPY.companyDetail);
  const provenance = detail?.provenance ?? LIVE_FIXTURE_PROVENANCE;

  const assistantContext: AssistantContext = {
    scope: "company",
    route: "/companies/[ticker]",
    surfaceLabel: detail === null ? ticker.toUpperCase() : detail.company.name,
    ticker: detail?.company.ticker ?? ticker.toUpperCase(),
    selectedTickers: [],
    periodLabel: null,
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
        <nav aria-label="Đường dẫn" className="text-[13px] text-text-muted">
          <ol className="flex flex-wrap items-center gap-1.5">
            <li>
              <Link href="/" className="hover:text-primary-700 hover:underline">
                Tổng quan
              </Link>
            </li>
            <li aria-hidden="true">/</li>
            <li>
              <Link href="/companies" className="hover:text-primary-700 hover:underline">
                Doanh nghiệp
              </Link>
            </li>
            <li aria-hidden="true">/</li>
            <li className="font-mono font-medium text-text-body">{ticker.toUpperCase()}</li>
          </ol>
        </nav>

        {detail === null ? (
          <StatePanel
            copy={copy ?? LOADING_COPY.companyDetail}
            tone={isFailureState(result) ? "critical" : "neutral"}
            action={
              <ButtonLink href="/companies" variant="secondary">
                Về danh sách doanh nghiệp
              </ButtonLink>
            }
          />
        ) : (
          <>
            <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
              <div className="min-w-0">
                <h1 className="flex flex-wrap items-baseline gap-3 text-[28px]">
                  <span className="font-mono">{detail.company.ticker}</span>
                  <span className="text-[18px] font-medium text-text-muted">
                    {detail.company.exchange}
                  </span>
                </h1>
                <p className="mt-1 text-[16px] text-text-body">{detail.company.name}</p>
                <p className="mt-1 text-[13px] text-text-muted">
                  {detail.company.sector} · Kỳ dữ liệu {provenance.dataVersion}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <ButtonLink href={`/compare?ticker=${detail.company.ticker}`} variant="secondary">
                  So sánh phiên bản mô hình
                </ButtonLink>
                <ButtonLink href="/reports" variant="primary">
                  Lưu báo cáo
                </ButtonLink>
              </div>
            </div>

            {/* The degraded banner sits above the numbers, not below them: by the
                time a reader reaches a footnote they have already trusted the
                score as live. */}
            {copy !== null ? (
              <StatePanel copy={copy} tone={isFailureState(result) ? "critical" : "warning"} />
            ) : null}

            <DisclaimerBanner surface="company" />

            <RiskKpiStrip detail={detail} />

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
              <div className="flex flex-col gap-4">
                <Card>
                  <CardHeader
                    title="Diễn biến rủi ro"
                    description="Xác suất distress và Altman Z-Score qua các kỳ báo cáo"
                  />
                  <CardBody>
                    <TrendChart points={detail.trend} />
                  </CardBody>
                </Card>

                <Card>
                  <CardHeader
                    title="Chỉ tiêu tài chính"
                    description="Các chỉ tiêu mô hình sử dụng, theo kỳ báo cáo gần nhất"
                  />
                  <CardBody>
                    <IndicatorTable
                      periods={detail.indicatorPeriods}
                      indicators={detail.indicators}
                    />
                  </CardBody>
                </Card>

                <Card>
                  <CardHeader
                    title="Yếu tố tác động đến điểm rủi ro"
                    description={`Đóng góp của từng yếu tố theo ${detail.modelVersion}`}
                  />
                  <CardBody className="flex flex-col gap-4">
                    <ShapChart drivers={detail.shapDrivers} />
                    {/* The explanation is its own decision-support surface, so it
                        carries the disclaimer in its own right. */}
                    <DisclaimerBanner surface="model_explanation" variant="inline" />
                  </CardBody>
                </Card>
              </div>

              <div className="flex flex-col gap-4">
                <Card>
                  <CardHeader
                    title="Nguồn dữ liệu"
                    description="Tài liệu và tin tức đứng sau kết quả này"
                  />
                  <CardBody>
                    <SourceList sources={detail.sources} />
                  </CardBody>
                </Card>

                <Card>
                  <CardHeader
                    title="Xuất xứ kết quả"
                    description="Phiên bản dữ liệu, mô hình và commit đã sinh ra kết quả"
                  />
                  <CardBody>
                    <ProvenancePanel provenance={provenance} />
                  </CardBody>
                </Card>
              </div>
            </div>
          </>
        )}
      </div>
    </AnalystShell>
  );
}
