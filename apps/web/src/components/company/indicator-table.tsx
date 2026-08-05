import type { FinancialIndicator } from "@distresslens/contracts";
import { EmptyState } from "@/components/ui/state-panel";
import { TrendGlyph } from "@/components/ui/trend-indicator";

/**
 * Financial indicators across the reported periods.
 *
 * A null value means the period was not reported, and it renders as an em dash
 * with a screen-reader explanation rather than a zero — a missing filing and a
 * zero balance are different facts, and conflating them changes the ratio an
 * analyst reads.
 */
export function IndicatorTable({
  periods,
  indicators,
}: {
  periods: readonly string[];
  indicators: readonly FinancialIndicator[];
}) {
  if (indicators.length === 0) {
    return (
      <EmptyState
        title="Chưa có chỉ tiêu tài chính"
        description="Báo cáo tài chính của doanh nghiệp này chưa được nạp vào kỳ dữ liệu hiện tại."
      />
    );
  }

  return (
    <div
      className="overflow-x-auto"
      tabIndex={0}
      role="region"
      aria-label="Chỉ tiêu tài chính theo kỳ báo cáo và xu hướng của từng chỉ tiêu"
    >
      <table className="w-full min-w-[520px] border-collapse text-[14px]">
        <caption className="sr-only">
          Chỉ tiêu tài chính theo kỳ báo cáo và xu hướng của từng chỉ tiêu
        </caption>
        <thead>
          <tr className="border-b border-line-hairline text-[13px] text-text-muted">
            <th scope="col" className="py-2 pr-3 text-left font-medium">
              Chỉ tiêu
            </th>
            {periods.map((period) => (
              <th key={period} scope="col" className="py-2 pr-3 text-right font-medium">
                {period}
              </th>
            ))}
            <th scope="col" className="py-2 text-left font-medium">
              Xu hướng
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line-hairline">
          {indicators.map((indicator) => (
            <tr key={indicator.name}>
              <th scope="row" className="py-2.5 pr-3 text-left font-medium text-text-strong">
                {indicator.name}
                <span className="ml-1.5 font-normal text-text-muted">({indicator.unit})</span>
              </th>
              {indicator.values.map((value, index) => (
                <td
                  key={periods[index] ?? index}
                  data-numeric
                  className="py-2.5 pr-3 text-right font-mono text-text-body"
                >
                  {value === null ? (
                    <>
                      <span aria-hidden="true">—</span>
                      <span className="sr-only">chưa có số liệu</span>
                    </>
                  ) : (
                    value.toLocaleString("vi-VN")
                  )}
                </td>
              ))}
              <td className="py-2.5">
                <TrendGlyph trend={indicator.trend} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
