import { RISK_BAND_LABELS, type RiskBandSummary } from "@distresslens/contracts";
import Link from "next/link";
import { EmptyState } from "@/components/ui/state-panel";
import { TrendIndicator } from "@/components/ui/trend-indicator";

/**
 * How the monitored portfolio splits across risk bands.
 *
 * A single proportional bar rather than a donut: the question is "how much of
 * the book is in trouble", and a length comparison answers that faster than an
 * angle. Each band is also listed with its count, its share and its movement,
 * so the bar is a summary of the list rather than the only place the numbers
 * exist.
 */

const BAND_FILL: Record<string, string> = {
  HIGH: "bg-risk-high-fill",
  WATCH: "bg-risk-watch-fill",
  STABLE: "bg-risk-stable-fill",
};

export function RiskDistribution({ summaries }: { summaries: readonly RiskBandSummary[] }) {
  const total = summaries.reduce((sum, summary) => sum + summary.companyCount, 0);

  if (total === 0) {
    return (
      <EmptyState
        title="Chưa có doanh nghiệp nào được chấm điểm"
        description="Thêm doanh nghiệp vào danh mục để bắt đầu theo dõi sức khỏe tài chính và nhận cảnh báo."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div
        role="img"
        aria-label={summaries
          .map(
            (summary) =>
              `${RISK_BAND_LABELS[summary.band]}: ${summary.companyCount} trên ${total} doanh nghiệp`,
          )
          .join("; ")}
        className="flex h-3 w-full overflow-hidden rounded-sm bg-paper-2"
      >
        {summaries.map((summary) => (
          <span
            key={summary.band}
            className={BAND_FILL[summary.band]}
            style={{ width: `${(summary.companyCount / total) * 100}%` }}
          />
        ))}
      </div>

      <ul className="flex flex-col divide-y divide-line-hairline">
        {summaries.map((summary) => (
          <li key={summary.band} className="flex items-center justify-between gap-4 py-2.5">
            <span className="flex min-w-0 items-center gap-2">
              <span
                aria-hidden="true"
                className={`h-2.5 w-2.5 shrink-0 rounded-[2px] ${BAND_FILL[summary.band]}`}
              />
              <span className="truncate text-[14px] text-text-body">
                {RISK_BAND_LABELS[summary.band]}
              </span>
            </span>

            <span className="flex shrink-0 items-center gap-4">
              <span className="text-right">
                <span
                  data-numeric
                  className="block text-[16px] font-semibold text-text-strong"
                >
                  {summary.companyCount}
                </span>
                <span data-numeric className="block text-[12px] text-text-muted">
                  {((summary.companyCount / total) * 100).toFixed(0)}%
                </span>
              </span>
              <span className="w-[130px] text-right">
                <TrendIndicator
                  value={summary.changeVsPriorWeek}
                  intent={summary.band === "STABLE" ? "rising-is-good" : "rising-is-bad"}
                  comparisonLabel="so với tuần trước"
                />
              </span>
            </span>
          </li>
        ))}
      </ul>

      <Link
        href="/companies"
        className="text-[13px] font-medium text-primary-600 underline-offset-2 hover:underline"
      >
        Xem toàn bộ {total} doanh nghiệp
      </Link>
    </div>
  );
}
