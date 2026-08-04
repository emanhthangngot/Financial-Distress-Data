import {
  SESSION_STATES,
  type EvidenceSessionView,
  type SessionState,
} from "@distresslens/contracts";

/**
 * Where the evidence session is, and how it got there.
 *
 * The lifecycle is drawn as the full nine-state machine rather than only the
 * states this session has visited, because an operator deciding whether to wait
 * or to tear down needs to know what comes next. Terminal failure states sit
 * apart from the happy path: `FAILED` and `EXPIRED` are not steps along the way
 * to `READY`, and drawing them inline would imply they are.
 */

const HAPPY_PATH: readonly SessionState[] = [
  "OFF",
  "REQUESTED",
  "PROVISIONING",
  "SYNCING",
  "READY",
  "CAPTURING",
  "DESTROYING",
];

const TERMINAL: readonly SessionState[] = ["FAILED", "EXPIRED"];

export const SESSION_STATE_LABELS: Record<SessionState, string> = {
  OFF: "Tắt",
  REQUESTED: "Đã yêu cầu",
  PROVISIONING: "Đang cấp phát",
  SYNCING: "Đang đồng bộ",
  READY: "Sẵn sàng",
  CAPTURING: "Đang thu thập",
  DESTROYING: "Đang hủy",
  FAILED: "Thất bại",
  EXPIRED: "Hết hạn",
};

/** Non-color signal for the current state, so the step is not only a colour. */
const CURRENT_MARK = "●";

export function SessionStateTimeline({ session }: { session: EvidenceSessionView }) {
  const currentIndex = HAPPY_PATH.indexOf(session.state);
  const isTerminal = TERMINAL.includes(session.state);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-3">
        <ol className="flex flex-wrap gap-1.5">
          {HAPPY_PATH.map((state, index) => {
            const current = state === session.state;
            const passed = currentIndex >= 0 && index < currentIndex;

            return (
              <li key={state}>
                <span
                  aria-current={current ? "step" : undefined}
                  className={[
                    "flex items-center gap-1.5 rounded-sm border px-2 py-1 text-[12px] font-medium",
                    current
                      ? "border-primary-600 bg-primary-050 text-ink-900"
                      : passed
                        ? "border-line-strong bg-paper-2 text-text-body"
                        : "border-line-hairline bg-paper-0 text-text-muted",
                  ].join(" ")}
                >
                  {current ? <span aria-hidden="true">{CURRENT_MARK}</span> : null}
                  {SESSION_STATE_LABELS[state]}
                  {current ? <span className="sr-only">(trạng thái hiện tại)</span> : null}
                </span>
              </li>
            );
          })}
        </ol>

        <p className="flex flex-wrap items-center gap-2 text-[13px] text-text-muted">
          {isTerminal ? (
            <span className="rounded-sm border border-risk-high-fill/35 bg-risk-high-soft px-2 py-1 font-medium text-risk-high-ink">
              {CURRENT_MARK} {SESSION_STATE_LABELS[session.state]}
            </span>
          ) : null}
          <span>
            Trạng thái kết thúc có thể xảy ra:{" "}
            {TERMINAL.map((state) => SESSION_STATE_LABELS[state]).join(", ")}.
          </span>
        </p>
      </div>

      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-[13px] lg:grid-cols-4">
        <Field label="Mã phiên" value={session.id ?? "chưa có phiên"} mono={session.id !== null} />
        <Field label="Phiên bản" value={String(session.version)} mono />
        <Field label="Người thao tác" value={session.actor ?? "—"} />
        <Field
          label="Hết hạn lease"
          value={session.leaseExpiry === null ? "—" : formatTimestamp(session.leaseExpiry)}
        />
      </dl>

      <div>
        <h3 className="text-[14px] font-semibold text-text-strong">Lịch sử chuyển trạng thái</h3>
        {session.history.length === 0 ? (
          <p className="mt-2 text-[13px] text-text-muted">
            Chưa có chuyển trạng thái nào được ghi nhận cho phiên hiện tại.
          </p>
        ) : (
          <ol className="mt-2 flex flex-col divide-y divide-line-hairline">
            {session.history.map((entry) => (
              <li
                key={`${entry.version}-${entry.occurredAt}`}
                className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 py-2 text-[13px]"
              >
                <span className="text-text-body">
                  {SESSION_STATE_LABELS[entry.fromState]} → {SESSION_STATE_LABELS[entry.toState]}
                </span>
                <span className="flex items-center gap-3 text-text-muted">
                  <span data-numeric className="font-mono text-[12px]">
                    v{entry.version}
                  </span>
                  <span>{entry.actor}</span>
                  <time dateTime={entry.occurredAt} data-numeric className="font-mono text-[12px]">
                    {formatTimestamp(entry.occurredAt)}
                  </time>
                </span>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}

/** Every lifecycle state the product can render, for the evidence manifest. */
export const ALL_SESSION_STATES = SESSION_STATES;

function Field({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-text-muted">{label}</dt>
      <dd className={`truncate text-text-body ${mono ? "font-mono text-[12px]" : ""}`}>{value}</dd>
    </div>
  );
}

function formatTimestamp(iso: string): string {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(new Date(iso));
}
