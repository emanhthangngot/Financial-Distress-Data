import type { PlaneHealth, PlaneStatus as PlaneStatusData } from "@distresslens/contracts";

/**
 * Plane health indicator. Status is carried by an icon shape and a word, never
 * by the dot color alone — the admin shell is read under time pressure and by
 * people who cannot distinguish the red/green pair.
 */

const HEALTH_LABELS: Record<PlaneHealth, string> = {
  ONLINE: "Trực tuyến",
  DEGRADED: "Suy giảm",
  OFFLINE: "Ngoại tuyến",
  UNKNOWN: "Chưa rõ",
};

/** Text tones only — the -ink variants, which clear 4.5:1 on every paper tone. */
const HEALTH_TONE: Record<PlaneHealth, string> = {
  ONLINE: "text-status-live-ink",
  DEGRADED: "text-status-pending-ink",
  OFFLINE: "text-status-fail-ink",
  UNKNOWN: "text-status-offline-ink",
};

export const PLANE_COMPONENT_LABELS = {
  WEB: "Web",
  SUPABASE: "Supabase",
  EKS_AI: "EKS AI",
} as const;

function HealthGlyph({ health }: { health: PlaneHealth }) {
  if (health === "ONLINE") {
    return (
      <svg viewBox="0 0 16 16" width={16} height={16} aria-hidden="true" fill="none">
        <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.6" />
        <path d="m5 8.2 2 2 4-4.2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    );
  }

  if (health === "OFFLINE" || health === "DEGRADED") {
    return (
      <svg viewBox="0 0 16 16" width={16} height={16} aria-hidden="true" fill="none">
        <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.6" />
        <path d="M8 4.5v4.2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        <circle cx="8" cy="11.4" r="0.9" fill="currentColor" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 16 16" width={16} height={16} aria-hidden="true" fill="none">
      <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.6" strokeDasharray="2 2" />
    </svg>
  );
}

export function PlaneStatusRow({ status }: { status: PlaneStatusData }) {
  return (
    <div className="flex items-start gap-2.5 py-1.5">
      <span className={`mt-0.5 shrink-0 ${HEALTH_TONE[status.health]}`}>
        <HealthGlyph health={status.health} />
      </span>
      <span className="min-w-0">
        <span className="flex flex-wrap items-baseline gap-x-2">
          <span className="text-[14px] font-semibold text-text-strong">
            {PLANE_COMPONENT_LABELS[status.component]}
          </span>
          <span className={`text-[13px] font-medium ${HEALTH_TONE[status.health]}`}>
            {HEALTH_LABELS[status.health]}
          </span>
        </span>
        {status.detail !== null ? (
          <span className="block text-[12px] text-text-muted">{status.detail}</span>
        ) : null}
      </span>
    </div>
  );
}

/** Single-pill summary for the admin header. */
export function PlaneStatusPill({ health }: { health: PlaneHealth }) {
  return (
    <span className="flex items-center gap-1.5 rounded-md border border-line-hairline bg-paper-0 px-2.5 py-1.5 text-[13px] font-medium">
      <span className={HEALTH_TONE[health]}>
        <HealthGlyph health={health} />
      </span>
      <span className="text-text-strong">{HEALTH_LABELS[health]}</span>
    </span>
  );
}
