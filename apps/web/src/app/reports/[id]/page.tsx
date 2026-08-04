import type { SavedReport } from "@distresslens/contracts";
import Link from "next/link";
import { ExportReportButton } from "@/components/company/export-report-button";
import { IndicatorTable } from "@/components/company/indicator-table";
import { ProvenancePanel } from "@/components/company/provenance-panel";
import { ShapChart } from "@/components/company/shap-chart";
import { SourceList } from "@/components/company/source-list";
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
 * A saved report.
 *
 * A report is a snapshot, not a live view: it renders the numbers as they stood
 * when it was saved, with the provenance of that moment. It deliberately does
 * not re-query the current score — a document whose contents change after it is
 * cited is not a report.
 *
 * A revoked report and a report belonging to someone else produce the same
 * denial, because distinguishing them would confirm the report exists.
 */

export const dynamic = "force-dynamic";

export default async function SavedReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { user, context } = await resolveSession();
  const { id } = await params;

  const result = await getDataPort().getSavedReport(context, id);
  const report: SavedReport | null = viewData(result);
  const copy = viewCopy(result, LOADING_COPY.report);
  const provenance = report?.detail.provenance ?? LIVE_FIXTURE_PROVENANCE;

  const assistantContext: AssistantContext = {
    scope: "report",
    route: "/reports/[id]",
    surfaceLabel: report === null ? "Báo cáo đã lưu" : report.title,
    ticker: report?.company.ticker ?? null,
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
              <Link href="/reports" className="hover:text-primary-700 hover:underline">
                Báo cáo
              </Link>
            </li>
            <li aria-hidden="true">/</li>
            <li className="font-mono font-medium text-text-body">{id}</li>
          </ol>
        </nav>

        {report === null ? (
          <StatePanel
            copy={copy ?? LOADING_COPY.report}
            tone={isFailureState(result) ? "critical" : "neutral"}
            action={
              <ButtonLink href="/reports" variant="secondary">
                Về danh sách báo cáo
              </ButtonLink>
            }
          />
        ) : (
          <>
            <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
              <div className="min-w-0">
                <h1 className="text-[28px]">{report.title}</h1>
                <p className="mt-1 text-[15px] text-text-body">{report.summary}</p>
                <p className="mt-1.5 text-[13px] text-text-muted">
                  Lưu lúc{" "}
                  <time dateTime={report.createdAt} data-numeric className="font-mono">
                    {report.createdAt.slice(0, 16).replace("T", " ")}
                  </time>{" "}
                  · {report.company.ticker} · {report.company.name}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <ButtonLink href={`/companies/${report.company.ticker}`} variant="secondary">
                  Xem số liệu hiện tại
                </ButtonLink>
                <ExportReportButton />
              </div>
            </div>

            <DisclaimerBanner surface="report_export" />

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
              <div className="flex flex-col gap-4">
                <Card>
                  <CardHeader
                    title="Chỉ tiêu tài chính tại thời điểm lưu"
                    description={`Theo ${report.detail.modelVersion}`}
                  />
                  <CardBody>
                    <IndicatorTable
                      periods={report.detail.indicatorPeriods}
                      indicators={report.detail.indicators}
                    />
                  </CardBody>
                </Card>

                <Card>
                  <CardHeader
                    title="Yếu tố tác động đến điểm rủi ro"
                    description="Đóng góp của từng yếu tố trong lần chấm điểm được lưu"
                  />
                  <CardBody className="flex flex-col gap-4">
                    <ShapChart drivers={report.detail.shapDrivers} />
                    <DisclaimerBanner surface="model_explanation" variant="inline" />
                  </CardBody>
                </Card>
              </div>

              <div className="flex flex-col gap-4">
                <Card>
                  <CardHeader
                    title="Nguồn dữ liệu"
                    description="Tài liệu và tin tức được trích dẫn trong báo cáo"
                  />
                  <CardBody>
                    <SourceList sources={report.detail.sources} />
                  </CardBody>
                </Card>

                <Card>
                  <CardHeader
                    title="Xuất xứ kết quả"
                    description="Trạng thái dữ liệu và mô hình tại thời điểm báo cáo được lưu"
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
