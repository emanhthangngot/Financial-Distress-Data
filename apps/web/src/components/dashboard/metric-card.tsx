import Link from "next/link";
import { InfoIcon } from "@/components/shell/icons";
import { TrendIndicator } from "@/components/ui/trend-indicator";

/**
 * A single portfolio metric.
 *
 * Every card answers four things in the same order: what is measured, the
 * value, how it moved, and where to go to act on it. The explanation is a
 * `<details>` rather than a hover tooltip, because a definition an analyst
 * cannot reach by keyboard is a definition half the team never reads.
 */

export interface MetricCardProps {
  label: string;
  /** Preformatted value; the caller owns rounding and units. */
  value: string;
  unit?: string;
  /** Signed change against the comparison period, or null when unknown. */
  change: number | null;
  changeUnit?: string;
  changeDecimals?: number;
  comparisonLabel: string;
  intent: "rising-is-bad" | "rising-is-good";
  /** What the metric means and how it is derived. */
  explanation: string;
  /** Drill-down target; omitted when no route shows this metric in detail. */
  href?: string;
  drillDownLabel?: string;
}

export function MetricCard({
  label,
  value,
  unit,
  change,
  changeUnit = "",
  changeDecimals = 0,
  comparisonLabel,
  intent,
  explanation,
  href,
  drillDownLabel = "Xem chi tiết",
}: MetricCardProps) {
  return (
    <section className="flex flex-col gap-2.5 rounded-lg border border-line-hairline bg-paper-0 px-5 py-4 shadow-(--shadow-card)">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-[14px] font-medium text-text-muted">{label}</h3>
        <details className="group relative shrink-0">
          <summary className="flex list-none items-center justify-center rounded-sm p-1 text-text-muted hover:text-text-body [&::-webkit-details-marker]:hidden">
            <InfoIcon />
            <span className="sr-only">Giải thích chỉ số {label}</span>
          </summary>
          <p className="absolute right-0 z-(--z-sticky) mt-1 w-64 rounded-md border border-line-hairline bg-paper-0 px-3 py-2 text-[13px] leading-relaxed text-text-body shadow-(--shadow-popover)">
            {explanation}
          </p>
        </details>
      </div>

      <p className="flex items-baseline gap-1">
        <span data-numeric className="text-[32px] font-bold leading-none text-text-strong">
          {value}
        </span>
        {unit !== undefined ? (
          <span className="text-[16px] font-medium text-text-muted">{unit}</span>
        ) : null}
      </p>

      {change === null ? (
        <p className="text-[13px] text-text-muted">Chưa có số liệu kỳ trước để so sánh</p>
      ) : (
        <TrendIndicator
          value={change}
          unit={changeUnit}
          decimals={changeDecimals}
          intent={intent}
          comparisonLabel={comparisonLabel}
        />
      )}

      {href !== undefined ? (
        <Link
          href={href}
          className="mt-auto pt-1 text-[13px] font-medium text-primary-600 underline-offset-2 hover:underline"
        >
          {drillDownLabel}
        </Link>
      ) : null}
    </section>
  );
}
