import type { AlertItem } from "@distresslens/contracts";
import Link from "next/link";
import { RiskBadge } from "@/components/ui/risk-badge";
import { EmptyState } from "@/components/ui/state-panel";

/**
 * Risk events in the order they were detected.
 *
 * These are model-detected changes with a timestamp, not a generic activity
 * feed: every entry names the company, what changed and when, so it can be
 * acted on without opening anything. Nothing is listed here that the scoring
 * run did not actually produce.
 */
export function AlertTimeline({ alerts }: { alerts: readonly AlertItem[] }) {
  if (alerts.length === 0) {
    return (
      <EmptyState
        title="Chưa có cảnh báo mới"
        description="Lần chấm điểm gần nhất không phát hiện thay đổi rủi ro nào vượt ngưỡng cảnh báo."
      />
    );
  }

  return (
    <ol className="flex flex-col divide-y divide-line-hairline">
      {alerts.map((alert) => (
        <li key={alert.id} className="flex flex-col gap-1.5 py-3 first:pt-0 last:pb-0">
          <div className="flex items-baseline justify-between gap-3">
            <Link
              href={`/companies/${alert.ticker}`}
              className="text-[14px] font-semibold text-text-strong underline-offset-2 hover:text-primary-700 hover:underline"
            >
              {alert.headline}
            </Link>
            <time
              dateTime={alert.occurredAt}
              data-numeric
              className="shrink-0 font-mono text-[12px] text-text-muted"
            >
              {formatTime(alert.occurredAt)}
            </time>
          </div>
          <p className="text-[13px] text-text-body">{alert.detail}</p>
          <span className="self-start">
            <RiskBadge band={alert.band} size="sm" />
          </span>
        </li>
      ))}
    </ol>
  );
}

function formatTime(iso: string): string {
  // Fixed locale and timezone: the evidence screenshots must be byte-stable
  // regardless of where the run happens.
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(new Date(iso));
}
