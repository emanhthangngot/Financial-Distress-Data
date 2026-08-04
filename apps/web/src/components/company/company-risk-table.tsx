import type { CompanyRiskRow } from "@distresslens/contracts";
import Link from "next/link";
import type { ReactNode } from "react";
import { RiskBadge } from "@/components/ui/risk-badge";
import { EmptyState } from "@/components/ui/state-panel";
import { TrendGlyph } from "@/components/ui/trend-indicator";

/**
 * The one company table. The overview's attention list and the search results
 * are the same rows with a different caption and footer, so they are the same
 * component — a second table would drift in column order and risk semantics.
 *
 * Three compositions, not one shrunk: the full eight columns at `xl`, a
 * six-column table from `lg` where sector and data-through give way, and a
 * stacked card list below that — an eight-column table on a 390px screen is
 * either unreadable or a horizontal scroll nobody discovers.
 */

export interface CompanyRiskTableProps {
  rows: readonly CompanyRiskRow[];
  /** Screen-reader caption describing what this particular list is. */
  caption: string;
  emptyTitle: string;
  emptyDescription: string;
  emptyAction?: ReactNode;
  /** Row-count line rendered under the table. */
  footer?: ReactNode;
}

export function CompanyRiskTable({
  rows,
  caption,
  emptyTitle,
  emptyDescription,
  emptyAction,
  footer,
}: CompanyRiskTableProps) {
  if (rows.length === 0) {
    return (
      <EmptyState title={emptyTitle} description={emptyDescription} action={emptyAction} />
    );
  }

  return (
    <>
      {/* Sector and data-through appear only at `xl`. Below that the table
          composes down to the columns a decision needs rather than relying on a
          horizontal scroll nobody discovers — eight columns do not fit the
          canvas at 1024, and a scroll container there just hides that. */}
      <div className="hidden w-0 min-w-full overflow-x-auto lg:block">
        <table className="w-full border-collapse text-[14px]">
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr className="border-b border-line-hairline text-left text-[13px] text-text-muted">
              <th scope="col" className="py-2 pr-3 font-medium">
                Mã
              </th>
              <th scope="col" className="py-2 pr-3 font-medium">
                Doanh nghiệp
              </th>
              <th scope="col" className="hidden py-2 pr-3 font-medium xl:table-cell">
                Ngành
              </th>
              <th scope="col" className="py-2 pr-3 text-right font-medium">
                Xác suất distress
              </th>
              <th scope="col" className="py-2 pr-3 font-medium">
                Nhóm rủi ro
              </th>
              <th scope="col" className="py-2 pr-3 font-medium">
                Xu hướng
              </th>
              <th scope="col" className="hidden py-2 pr-3 font-medium xl:table-cell">
                Dữ liệu đến
              </th>
              <th scope="col" className="py-2">
                <span className="sr-only">Hành động</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line-hairline">
            {rows.map((row) => (
              <tr key={row.ticker} className="hover:bg-paper-1">
                <th scope="row" className="py-2.5 pr-3 text-left">
                  <span className="font-mono text-[14px] font-semibold text-text-strong">
                    {row.ticker}
                  </span>
                </th>
                <td className="max-w-[280px] truncate py-2.5 pr-3 text-text-body">{row.name}</td>
                <td className="hidden py-2.5 pr-3 text-text-muted xl:table-cell">{row.sector}</td>
                <td data-numeric className="py-2.5 pr-3 text-right font-mono font-semibold text-text-strong">
                  {row.distressProbability.toFixed(1)}%
                </td>
                <td className="py-2.5 pr-3">
                  <RiskBadge band={row.band} size="sm" />
                </td>
                <td className="py-2.5 pr-3">
                  <TrendGlyph trend={row.trend} />
                </td>
                <td
                  data-numeric
                  className="hidden whitespace-nowrap py-2.5 pr-3 font-mono text-[13px] text-text-muted xl:table-cell"
                >
                  {row.dataThrough}
                </td>
                <td className="py-2.5 text-right">
                  <Link
                    href={`/companies/${row.ticker}`}
                    className="whitespace-nowrap text-[13px] font-medium text-primary-600 underline-offset-2 hover:underline"
                  >
                    Xem chi tiết
                    <span className="sr-only"> doanh nghiệp {row.ticker}</span>
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className="flex flex-col divide-y divide-line-hairline lg:hidden">
        {rows.map((row) => (
          <li key={row.ticker} className="flex flex-col gap-2 py-3">
            <div className="flex items-baseline justify-between gap-3">
              <span className="min-w-0">
                <span className="font-mono text-[15px] font-semibold text-text-strong">
                  {row.ticker}
                </span>
                <span className="ml-2 text-[13px] text-text-muted">{row.sector}</span>
              </span>
              <span data-numeric className="shrink-0 font-mono text-[16px] font-semibold text-text-strong">
                {row.distressProbability.toFixed(1)}%
              </span>
            </div>
            <p className="text-[14px] text-text-body">{row.name}</p>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
              <RiskBadge band={row.band} size="sm" />
              <TrendGlyph trend={row.trend} />
              <span data-numeric className="font-mono text-[12px] text-text-muted">
                Dữ liệu đến {row.dataThrough}
              </span>
            </div>
            <Link
              href={`/companies/${row.ticker}`}
              className="tap-target inline-flex items-center text-[14px] font-medium text-primary-600 underline-offset-2 hover:underline"
            >
              Xem chi tiết
              <span className="sr-only"> doanh nghiệp {row.ticker}</span>
            </Link>
          </li>
        ))}
      </ul>

      {footer !== undefined ? (
        <p className="pt-3 text-[13px] text-text-muted">{footer}</p>
      ) : null}
    </>
  );
}

/** Footer for a list that shows a slice of a larger monitored set. */
export function ShowingCount({ shown, total }: { shown: number; total: number }) {
  return (
    <>
      Đang hiển thị {shown} trong {total} doanh nghiệp được theo dõi.{" "}
      <Link
        href="/companies"
        className="font-medium text-primary-600 underline-offset-2 hover:underline"
      >
        Xem tất cả
      </Link>
    </>
  );
}
