import type { AuditEvent } from "@distresslens/contracts";
import { EmptyState } from "@/components/ui/state-panel";

/**
 * Who did what, and whether it worked.
 *
 * Denied and failed entries are as prominent as successful ones — an audit
 * trail that highlights only what succeeded is a marketing timeline. Detail
 * text arrives already redacted from the server; nothing here reconstructs a
 * prompt, token or credential.
 */

const RESULT_LABEL: Record<AuditEvent["result"], string> = {
  SUCCESS: "Thành công",
  DENIED: "Bị từ chối",
  FAILED: "Thất bại",
};

const RESULT_TONE: Record<AuditEvent["result"], string> = {
  SUCCESS: "border-risk-stable-fill/35 bg-risk-stable-soft text-risk-stable-ink",
  DENIED: "border-risk-watch-fill/35 bg-risk-watch-soft text-risk-watch-ink",
  FAILED: "border-risk-high-fill/35 bg-risk-high-soft text-risk-high-ink",
};

export function AuditTimeline({ events }: { events: readonly AuditEvent[] }) {
  if (events.length === 0) {
    return (
      <EmptyState
        title="Chưa có sự kiện audit"
        description="Chưa có thao tác nào được ghi nhận trong khoảng thời gian đang xem."
      />
    );
  }

  return (
    <ol className="flex flex-col divide-y divide-line-hairline">
      {events.map((event) => (
        <li key={event.id} className="flex flex-col gap-1.5 py-3 first:pt-0 last:pb-0">
          <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
            <span className="flex flex-wrap items-center gap-2">
              <span className="text-[13px] font-semibold text-text-strong">{event.category}</span>
              <span
                className={`rounded-sm border px-1.5 py-0.5 text-[12px] font-medium ${RESULT_TONE[event.result]}`}
              >
                {RESULT_LABEL[event.result]}
              </span>
            </span>
            <time
              dateTime={event.occurredAt}
              data-numeric
              className="shrink-0 font-mono text-[12px] text-text-muted"
            >
              {formatTimestamp(event.occurredAt)}
            </time>
          </div>
          <p className="text-[13px] text-text-body">{event.detail}</p>
          <p className="text-[12px] text-text-muted">{event.actor}</p>
        </li>
      ))}
    </ol>
  );
}

function formatTimestamp(iso: string): string {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(new Date(iso));
}
