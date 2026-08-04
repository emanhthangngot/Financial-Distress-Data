import { provenanceLabels, type Provenance } from "@distresslens/contracts";
import { ChevronDownIcon } from "./icons";

/**
 * The system status control — the one memorable element of this interface.
 *
 * In a product where a cached score and a live score render identically, the
 * question "where did this number come from" has to be answerable from the
 * chrome of every page. It is answered in two tiers: a single line an analyst
 * reads without stopping ("Đã đồng bộ · Mô hình DL-Score v2.1"), and a popover
 * carrying the fixture origin, source and GitOps commits, agent version and run
 * id for whoever is auditing the run.
 *
 * Built on `<details>` rather than a JS popover so it still opens on a degraded
 * page where the client bundle failed to load.
 */

export interface SystemStatusProps {
  provenance: Provenance;
  /** Human sync time, e.g. "23/05/2025 08:46". */
  syncedAtLabel: string;
}

export function SystemStatus({ provenance, syncedAtLabel }: SystemStatusProps) {
  const labels = provenanceLabels(provenance);
  const isLive =
    provenance.freshness === "LIVE" && provenance.planeAvailability === "LIVE_AVAILABLE";

  return (
    <details className="relative">
      <summary
        className="tap-target flex list-none items-center gap-2 rounded-md px-2.5 py-1.5 text-[13px] text-text-body hover:bg-paper-2 [&::-webkit-details-marker]:hidden"
        // Provenance changes as the analyst navigates and must be announced,
        // but it is not urgent enough to interrupt: polite, not assertive.
        aria-live="polite"
      >
        <span
          aria-hidden="true"
          className={`h-2 w-2 shrink-0 rounded-full ${
            isLive ? "bg-status-live" : "bg-status-pending"
          }`}
        />
        {/* Below `md` the status word is dropped and the dot carries the
            signal: the header has a brand, a menu and an account control to fit
            in 390px, and this line is the one that can be reached by tapping
            rather than read at a glance. The word stays in the popover. */}
        <span className="hidden font-medium text-text-strong md:inline">
          {isLive ? "Đã đồng bộ" : "Dữ liệu đã lưu"}
        </span>
        <span className="sr-only">{isLive ? "Đã đồng bộ" : "Dữ liệu đã lưu"}</span>
        {provenance.modelVersion !== null ? (
          <span className="hidden text-text-muted xl:inline">· {provenance.modelVersion}</span>
        ) : null}
        <span className="sr-only">Xem chi tiết hệ thống</span>
        <ChevronDownIcon width={14} height={14} />
      </summary>

      <div className="absolute right-0 z-(--z-overlay) mt-1 w-[320px] rounded-lg border border-line-hairline bg-paper-0 p-4 shadow-(--shadow-popover)">
        <h2 className="text-[14px] font-semibold text-text-strong">Chi tiết hệ thống</h2>
        <p className="mt-1 text-[13px] text-text-muted">
          {isLive
            ? "Kết quả đang hiển thị được sinh trực tiếp từ mặt phẳng suy luận."
            : "Kết quả đang hiển thị là bản đã lưu, không phải suy luận trực tiếp."}
        </p>

        {labels.length > 0 ? (
          <ul className="mt-3 flex flex-wrap gap-1.5">
            {labels.map((label) => (
              <li
                key={label}
                className="rounded-sm border border-line-strong bg-paper-2 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-text-strong"
              >
                {label}
              </li>
            ))}
          </ul>
        ) : null}

        <dl className="mt-3 flex flex-col gap-2 border-t border-line-hairline pt-3 text-[13px]">
          <StatusField label="Đồng bộ lần cuối" value={syncedAtLabel} />
          <StatusField label="Phiên bản dữ liệu" value={provenance.dataVersion} mono />
          {provenance.modelVersion !== null ? (
            <StatusField label="Mô hình" value={provenance.modelVersion} mono />
          ) : null}
          {provenance.agentVersion !== null ? (
            <StatusField label="Agent" value={provenance.agentVersion} mono />
          ) : null}
          <StatusField label="Commit nguồn" value={provenance.sourceSha} mono />
          {provenance.gitopsSha !== null ? (
            <StatusField label="Commit GitOps" value={provenance.gitopsSha} mono />
          ) : null}
          {provenance.runId !== null ? (
            <StatusField label="Mã lần chạy" value={provenance.runId} mono />
          ) : null}
        </dl>
      </div>
    </details>
  );
}

function StatusField({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="shrink-0 text-text-muted">{label}</dt>
      <dd
        className={`min-w-0 truncate text-right text-text-body ${mono ? "font-mono text-[12px]" : ""}`}
      >
        {value}
      </dd>
    </div>
  );
}
