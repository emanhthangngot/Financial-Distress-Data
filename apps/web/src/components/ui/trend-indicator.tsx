import type { TrendDirection } from "@distresslens/contracts";
import { TREND_LABELS } from "@distresslens/contracts";

/**
 * Period-over-period change.
 *
 * Direction is carried by an arrow glyph and by the sign on the number, so the
 * red/green tone is reinforcement rather than the message. `intent` exists
 * because "up" is bad news for a distress probability and good news for a
 * company count — the caller knows which, the component does not guess.
 */

export interface TrendIndicatorProps {
  /** Signed change. 0 renders as "không đổi". */
  value: number;
  /** Suffix appended to the absolute value, e.g. "%" or " doanh nghiệp". */
  unit?: string;
  /** Whether a rising value is a deterioration (risk) or an improvement. */
  intent: "rising-is-bad" | "rising-is-good";
  /** Period the comparison is against, e.g. "so với tuần trước". */
  comparisonLabel: string;
  decimals?: number;
}

export function TrendIndicator({
  value,
  unit = "",
  intent,
  comparisonLabel,
  decimals = 0,
}: TrendIndicatorProps) {
  const magnitude = Math.abs(value).toFixed(decimals);

  if (value === 0) {
    return (
      <p className="flex items-center gap-1.5 text-[13px] text-text-muted">
        <span aria-hidden="true">→</span>
        Không đổi {comparisonLabel}
      </p>
    );
  }

  const rising = value > 0;
  const bad = intent === "rising-is-bad" ? rising : !rising;

  return (
    <p
      className={`flex items-center gap-1.5 text-[13px] font-medium ${
        bad ? "text-risk-high-ink" : "text-risk-stable-ink"
      }`}
    >
      <span aria-hidden="true">{rising ? "↑" : "↓"}</span>
      <span data-numeric>
        {rising ? "+" : "−"}
        {magnitude}
        {unit}
      </span>
      <span className="font-normal text-text-muted">{comparisonLabel}</span>
    </p>
  );
}

/** Compact inline trend for table cells, where a full sentence would not fit. */
export function TrendGlyph({ trend }: { trend: TrendDirection }) {
  const glyph: Record<TrendDirection, string> = {
    UP_STRONG: "↑↑",
    UP: "↑",
    FLAT: "→",
    DOWN: "↓",
    DOWN_STRONG: "↓↓",
  };

  const tone: Record<TrendDirection, string> = {
    UP_STRONG: "text-risk-high-ink",
    UP: "text-risk-high-ink",
    FLAT: "text-text-muted",
    DOWN: "text-risk-stable-ink",
    DOWN_STRONG: "text-risk-stable-ink",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap text-[13px] ${tone[trend]}`}
    >
      <span aria-hidden="true" className="font-mono">
        {glyph[trend]}
      </span>
      {TREND_LABELS[trend]}
    </span>
  );
}
