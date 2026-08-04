import { provenanceLabels, type Provenance } from "@distresslens/contracts";

/**
 * The evidence ribbon — the one memorable element of this design.
 *
 * A persistent engraved strip under every header carrying where the data on
 * screen came from: live or cached, the data version, the source and GitOps
 * commits, and the model that produced the numbers. It is domain-derived rather
 * than decorative: in a product where a cached score and a live score look
 * identical, the provenance strip is the thing that keeps the page honest.
 *
 * Cached state changes the ribbon's edge and adds explicit chips, so the
 * difference is visible at a glance and not only in small print.
 */

export interface EvidenceRibbonProps {
  provenance: Provenance;
  /** Compact variant for narrow shells; hides the secondary commit fields. */
  compact?: boolean;
}

export function EvidenceRibbon({ provenance, compact = false }: EvidenceRibbonProps) {
  const labels = provenanceLabels(provenance);
  const isLive = provenance.freshness === "LIVE" && provenance.planeAvailability === "LIVE_AVAILABLE";

  return (
    <div
      // Provenance changes as the user navigates and must be announced, but it
      // is not urgent enough to interrupt: polite, not assertive.
      aria-live="polite"
      className={[
        "flex flex-wrap items-center gap-x-4 gap-y-1 border-b bg-paper-0 px-4 py-1.5 font-mono text-[12px] text-text-muted lg:px-6",
        isLive
          ? "border-line-hairline shadow-[inset_3px_0_0_0_var(--color-status-live)]"
          : "border-line-strong shadow-[inset_3px_0_0_0_var(--color-status-pending)]",
      ].join(" ")}
    >
      <span className="flex items-center gap-1.5">
        <span
          aria-hidden="true"
          className={`h-2 w-2 rounded-full ${isLive ? "bg-status-live" : "bg-status-pending"}`}
        />
        <span className="font-sans font-semibold text-text-strong">
          {isLive ? "Dữ liệu trực tiếp" : "Dữ liệu đã lưu"}
        </span>
      </span>

      {labels.map((label) => (
        <span
          key={label}
          className="rounded-sm border border-line-strong bg-paper-2 px-1.5 py-0.5 text-[11px] font-semibold tracking-wide text-text-strong"
        >
          {label}
        </span>
      ))}

      {provenance.cachedAt !== null ? (
        <RibbonField label="Lưu lúc" value={formatTimestamp(provenance.cachedAt)} />
      ) : null}

      <RibbonField label="Dữ liệu" value={provenance.dataVersion} />

      {provenance.modelVersion !== null ? (
        <RibbonField label="Mô hình" value={provenance.modelVersion} />
      ) : null}

      {/* Commit and agent provenance is desktop-only chrome. On a phone it
          pushed the ribbon to five lines and buried the page; the full set
          still reaches the evidence manifest, which is what the auditor reads. */}
      {!compact ? (
        <span className="hidden flex-wrap items-center gap-x-4 lg:flex">
          <RibbonField label="Source" value={provenance.sourceSha} />
          {provenance.gitopsSha !== null ? (
            <RibbonField label="GitOps" value={provenance.gitopsSha} />
          ) : null}
          {provenance.agentVersion !== null ? (
            <RibbonField label="Agent" value={provenance.agentVersion} />
          ) : null}
        </span>
      ) : null}
    </div>
  );
}

function RibbonField({ label, value }: { label: string; value: string }) {
  return (
    <span className="flex items-baseline gap-1.5 border-l border-line-hairline pl-4 first:border-l-0 first:pl-0">
      <span className="font-sans text-text-muted">{label}</span>
      <span className="text-text-body">{value}</span>
    </span>
  );
}

function formatTimestamp(iso: string): string {
  // Fixed locale and timezone: the evidence screenshots must be byte-stable
  // regardless of where the run happens.
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(new Date(iso));
}
