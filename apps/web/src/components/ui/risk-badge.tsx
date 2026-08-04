import { RISK_BAND_LABELS, type RiskBand } from "@distresslens/contracts";

/**
 * Risk band chip.
 *
 * The band name is always written out, and a filled square precedes it. Colour
 * is the third signal, never the first: an analyst reading this on a projector
 * or with a colour vision deficiency still gets the band from the text.
 */

const BAND_TONE: Record<RiskBand, string> = {
  HIGH: "border-risk-high-fill/35 bg-risk-high-soft text-risk-high-ink",
  WATCH: "border-risk-watch-fill/35 bg-risk-watch-soft text-risk-watch-ink",
  STABLE: "border-risk-stable-fill/35 bg-risk-stable-soft text-risk-stable-ink",
};

const BAND_MARK: Record<RiskBand, string> = {
  HIGH: "bg-risk-high-fill",
  WATCH: "bg-risk-watch-fill",
  STABLE: "bg-risk-stable-fill",
};

export function RiskBadge({ band, size = "md" }: { band: RiskBand; size?: "sm" | "md" }) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-sm border font-medium",
        size === "sm" ? "px-1.5 py-0.5 text-[12px]" : "px-2 py-1 text-[13px]",
        BAND_TONE[band],
      ].join(" ")}
    >
      <span aria-hidden="true" className={`h-2 w-2 rounded-[2px] ${BAND_MARK[band]}`} />
      {RISK_BAND_LABELS[band]}
    </span>
  );
}

/** Neutral chip for counts, versions and non-risk metadata. */
export function MetaChip({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-sm border border-line-hairline bg-paper-2 px-1.5 py-0.5 font-mono text-[11px] font-medium text-text-body">
      {children}
    </span>
  );
}
