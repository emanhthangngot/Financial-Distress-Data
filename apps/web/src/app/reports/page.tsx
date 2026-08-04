import type { SavedReportList } from "@distresslens/contracts";
import Link from "next/link";
import { PageHeader } from "@/components/dashboard/page-header";
import { AnalystShell } from "@/components/shell/analyst-shell";
import { ButtonLink } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { RiskBadge } from "@/components/ui/risk-badge";
import { EmptyState, StatePanel } from "@/components/ui/state-panel";
import type { AssistantContext } from "@/lib/assistant/assistant-context";
import { getDataPort } from "@/lib/data";
import { LIVE_FIXTURE_PROVENANCE } from "@/lib/data/fixtures/provenance-fixtures";
import { resolveSession } from "@/lib/server/session";
import { LOADING_COPY } from "@/lib/states/loading-copy";
import { isFailureState, viewCopy, viewData } from "@/lib/states/view-state";

/**
 * Reports the signed-in analyst owns.
 *
 * Ownership is decided by the data port, not filtered in the browser: a list
 * that arrives complete and is hidden client-side has already leaked.
 */

export const dynamic = "force-dynamic";

export default async function ReportsPage() {
  const { user, context } = await resolveSession();
  const result = await getDataPort().listSavedReports(context);
  const data: SavedReportList | null = viewData(result);
  const copy = viewCopy(result, LOADING_COPY.report);
  const provenance = data?.provenance ?? LIVE_FIXTURE_PROVENANCE;

  const assistantContext: AssistantContext = {
    scope: "report",
    route: "/reports",
    surfaceLabel: "Báo cáo đã lưu",
    ticker: null,
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
        <PageHeader
          title="Báo cáo"
          description="Các báo cáo rủi ro bạn đã lưu, kèm xuất xứ dữ liệu tại thời điểm lưu"
          freshnessLabel={`Kỳ dữ liệu ${provenance.dataVersion} · Cập nhật 23/05/2025 08:46`}
          primaryAction={
            <ButtonLink href="/companies" variant="primary">
              Tạo báo cáo mới
            </ButtonLink>
          }
        />

        {data === null ? (
          <StatePanel
            copy={copy ?? LOADING_COPY.report}
            tone={isFailureState(result) ? "critical" : "neutral"}
            action={
              <ButtonLink href="/companies" variant="secondary">
                Về danh sách doanh nghiệp
              </ButtonLink>
            }
          />
        ) : (
          <Card>
            <CardHeader
              title="Báo cáo của bạn"
              description={`${data.reports.length} báo cáo đã lưu`}
            />
            <CardBody>
              {data.reports.length === 0 ? (
                <EmptyState
                  title={result.state === "empty" ? result.copy.unavailable : "Chưa có báo cáo"}
                  description={
                    result.state === "empty"
                      ? result.copy.nextAction
                      : "Mở một doanh nghiệp và chọn “Lưu báo cáo” để tạo báo cáo đầu tiên."
                  }
                  action={
                    <ButtonLink href="/companies" variant="secondary">
                      Chọn doanh nghiệp
                    </ButtonLink>
                  }
                />
              ) : (
                <ul className="flex flex-col divide-y divide-line-hairline">
                  {data.reports.map((report) => (
                    <li
                      key={report.id}
                      className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2 py-3 first:pt-0 last:pb-0"
                    >
                      <div className="min-w-0">
                        <p className="text-[15px]">
                          {report.revokedAt === null ? (
                            <Link
                              href={`/reports/${report.id}`}
                              className="font-semibold text-text-strong underline-offset-2 hover:text-primary-700 hover:underline"
                            >
                              {report.title}
                            </Link>
                          ) : (
                            <span className="font-semibold text-text-muted line-through">
                              {report.title}
                            </span>
                          )}
                        </p>
                        <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-text-muted">
                          <span className="font-mono font-medium text-text-body">
                            {report.company.ticker}
                          </span>
                          <span aria-hidden="true">·</span>
                          <span>{report.company.name}</span>
                          <span aria-hidden="true">·</span>
                          <time dateTime={report.createdAt} data-numeric className="font-mono">
                            {report.createdAt.slice(0, 10)}
                          </time>
                        </p>
                      </div>

                      <div className="flex shrink-0 items-center gap-3">
                        <span data-numeric className="font-mono text-[15px] font-semibold text-text-strong">
                          {report.distressProbability.toFixed(1)}%
                        </span>
                        <RiskBadge band={report.band} size="sm" />
                        {report.revokedAt !== null ? (
                          <span className="rounded-sm border border-line-strong bg-paper-2 px-1.5 py-0.5 text-[12px] text-text-muted">
                            Đã thu hồi
                          </span>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        )}
      </div>
    </AnalystShell>
  );
}
