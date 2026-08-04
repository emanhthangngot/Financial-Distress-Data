import type { CompanyDetail } from "@distresslens/contracts";
import { RiskBadge } from "@/components/ui/risk-badge";
import { TrendIndicator } from "@/components/ui/trend-indicator";

/**
 * The company's headline verdict: probability, band, movement and how sure the
 * model is.
 *
 * Confidence sits beside the probability rather than in a footnote, because a
 * 78.6% score at 72% confidence is a different decision from the same score at
 * 95%, and burying that is how a model gets over-trusted.
 */
export function RiskKpiStrip({ detail }: { detail: CompanyDetail }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <section className="flex flex-col gap-2 rounded-lg border border-line-hairline bg-paper-0 px-5 py-4 shadow-(--shadow-card)">
        <h2 className="text-[14px] font-medium text-text-muted">Xác suất distress</h2>
        <p className="flex items-baseline gap-2">
          <span data-numeric className="text-[36px] font-bold leading-none text-text-strong">
            {detail.distressProbability.toFixed(1)}
          </span>
          <span className="text-[18px] font-medium text-text-muted">%</span>
        </p>
        <TrendIndicator
          value={detail.changeVsPriorRun}
          unit=" điểm %"
          decimals={1}
          intent="rising-is-bad"
          comparisonLabel="so với kỳ trước"
        />
      </section>

      <section className="flex flex-col gap-2 rounded-lg border border-line-hairline bg-paper-0 px-5 py-4 shadow-(--shadow-card)">
        <h2 className="text-[14px] font-medium text-text-muted">Nhóm rủi ro</h2>
        <p className="pt-1">
          <RiskBadge band={detail.band} />
        </p>
        <p className="text-[13px] text-text-muted">
          Phân loại bởi {detail.modelVersion} theo ngưỡng cảnh báo của mô hình.
        </p>
      </section>

      <section className="flex flex-col gap-2 rounded-lg border border-line-hairline bg-paper-0 px-5 py-4 shadow-(--shadow-card)">
        <h2 className="text-[14px] font-medium text-text-muted">Độ tin cậy của mô hình</h2>
        <p className="flex items-baseline gap-2">
          <span data-numeric className="text-[36px] font-bold leading-none text-text-strong">
            {detail.confidence}
          </span>
          <span className="text-[18px] font-medium text-text-muted">%</span>
        </p>
        {/* A bar as well as the number: confidence is a quantity the reader
            compares between companies, not a label. */}
        <span
          aria-hidden="true"
          className="mt-auto flex h-1.5 w-full overflow-hidden rounded-sm bg-paper-2"
        >
          <span className="bg-primary-500" style={{ width: `${detail.confidence}%` }} />
        </span>
      </section>
    </div>
  );
}
