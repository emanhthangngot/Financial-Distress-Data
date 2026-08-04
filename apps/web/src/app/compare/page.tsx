import type { ModelComparison } from "@distresslens/contracts";
import { ComparisonSplit } from "@/components/company/comparison-split";
import { PageHeader } from "@/components/dashboard/page-header";
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
 * Model version comparison.
 *
 * The ticker is a URL parameter rather than a picker with hidden state, so a
 * reviewer can link straight to the comparison being discussed and the
 * screenshot fixtures stay deterministic.
 */

export const dynamic = "force-dynamic";

const DEFAULT_TICKER = "NVL";

export default async function ComparePage({
  searchParams,
}: {
  searchParams: Promise<{ ticker?: string }>;
}) {
  const { user, context } = await resolveSession();
  const { ticker = DEFAULT_TICKER } = await searchParams;

  const result = await getDataPort().getModelComparison(context, ticker);
  const comparison: ModelComparison | null = viewData(result);
  const copy = viewCopy(result, LOADING_COPY.compare);
  const provenance = comparison?.provenance ?? LIVE_FIXTURE_PROVENANCE;

  const assistantContext: AssistantContext = {
    scope: "comparison",
    route: "/compare",
    surfaceLabel: `So sánh mô hình — ${ticker.toUpperCase()}`,
    ticker: ticker.toUpperCase(),
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
          title="So sánh phiên bản mô hình"
          description="Đối chiếu kết quả của phiên bản ứng viên với phiên bản đang chạy trên cùng một doanh nghiệp"
          freshnessLabel={`Kỳ dữ liệu ${provenance.dataVersion} · Cập nhật 23/05/2025 08:46`}
          primaryAction={
            <ButtonLink href={`/companies/${ticker.toUpperCase()}`} variant="secondary">
              Xem hồ sơ doanh nghiệp
            </ButtonLink>
          }
        />

        <DisclaimerBanner surface="compare" />

        {comparison === null ? (
          <StatePanel
            copy={copy ?? LOADING_COPY.compare}
            tone={isFailureState(result) ? "critical" : "neutral"}
            action={
              <ButtonLink href="/companies" variant="secondary">
                Chọn doanh nghiệp khác
              </ButtonLink>
            }
          />
        ) : (
          <>
            {copy !== null ? (
              <StatePanel copy={copy} tone={isFailureState(result) ? "critical" : "warning"} />
            ) : null}

            <Card>
              <CardHeader
                title={`${comparison.ticker} — hai phiên bản mô hình`}
                description="Xác suất distress, nhóm rủi ro, độ tin cậy và yếu tố tác động lớn nhất của từng phiên bản"
              />
              <CardBody>
                <ComparisonSplit comparison={comparison} />
              </CardBody>
            </Card>
          </>
        )}
      </div>
    </AnalystShell>
  );
}
