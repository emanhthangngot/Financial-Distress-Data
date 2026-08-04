import type {
  AgentLifecycle,
  AgentRegistryEntry,
  Role,
  SandboxPolicy,
} from "@distresslens/contracts";
import { EmptyState } from "@/components/ui/state-panel";
import { RoleActionButton } from "./role-action-button";

/**
 * Registered agents, their sandbox policy and their running replicas.
 *
 * The sandbox policy is shown in full rather than summarised as "restricted":
 * which hosts an agent may reach and whether it can touch a filesystem are the
 * facts a reviewer needs, and a reassuring adjective is not one of them.
 *
 * `ready: 0` with a null heartbeat means the plane is off and the count is
 * unknown, not that the agent scaled to zero. The two are rendered differently
 * because confusing them would make a healthy registry look like an outage.
 */

const LIFECYCLE_LABEL: Record<AgentLifecycle, string> = {
  DRAFT: "Bản nháp",
  CANDIDATE: "Ứng viên",
  PRODUCTION: "Production",
  RETIRED: "Đã ngừng",
};

const LIFECYCLE_TONE: Record<AgentLifecycle, string> = {
  DRAFT: "border-line-strong bg-paper-2 text-text-body",
  CANDIDATE: "border-risk-watch-fill/35 bg-risk-watch-soft text-risk-watch-ink",
  PRODUCTION: "border-risk-stable-fill/35 bg-risk-stable-soft text-risk-stable-ink",
  RETIRED: "border-line-strong bg-paper-2 text-text-muted",
};

const FILESYSTEM_LABEL: Record<SandboxPolicy["filesystemAccess"], string> = {
  NONE: "Không truy cập",
  READ_ONLY: "Chỉ đọc",
  READ_WRITE: "Đọc và ghi",
};

export function AgentRegistryList({
  entries,
  role,
  aal,
  /** False when the plane is off and replica counts cannot be read. */
  replicaCountsKnown,
}: {
  entries: readonly AgentRegistryEntry[];
  role: Role | null;
  aal: "aal1" | "aal2";
  replicaCountsKnown: boolean;
}) {
  if (entries.length === 0) {
    return (
      <EmptyState
        title="Chưa có agent nào được đăng ký"
        description="Đăng ký một phiên bản agent để nó xuất hiện trong sổ đăng ký và được triển khai."
      />
    );
  }

  return (
    <ul className="flex flex-col gap-4">
      {entries.map((entry) => (
        <li
          key={entry.id}
          className="rounded-lg border border-line-hairline bg-paper-0 px-5 py-4 shadow-(--shadow-card)"
        >
          <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-3">
            <div className="min-w-0">
              <h3 className="flex flex-wrap items-center gap-2 text-[16px]">
                {entry.name}
                <span
                  className={`rounded-sm border px-1.5 py-0.5 text-[12px] font-medium ${LIFECYCLE_TONE[entry.lifecycle]}`}
                >
                  {LIFECYCLE_LABEL[entry.lifecycle]}
                </span>
              </h3>
              <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-text-muted">
                <span data-numeric className="font-mono">
                  {entry.version}
                </span>
                <span aria-hidden="true">·</span>
                <span data-numeric className="font-mono">
                  {entry.modelVersion}
                </span>
              </p>
            </div>

            <div className="flex flex-wrap items-start gap-2">
              <RoleActionButton
                action="session.promote"
                role={role}
                aal={aal}
                label="Promote lên production"
                blockedReason={
                  entry.lifecycle === "CANDIDATE"
                    ? null
                    : "Chỉ phiên bản ứng viên mới promote được."
                }
              />
            </div>
          </div>

          <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-3 border-t border-line-hairline pt-3 text-[13px] sm:grid-cols-2 lg:grid-cols-4">
            <Field
              label="Bản sao"
              value={
                replicaCountsKnown
                  ? `${entry.replicas.ready}/${entry.replicas.desired} sẵn sàng`
                  : `Không đọc được (mong muốn ${entry.replicas.desired})`
              }
            />
            <Field
              label="Nhịp tim gần nhất"
              value={
                entry.replicas.lastHeartbeatAt === null
                  ? "Không có — mặt phẳng ngoại tuyến"
                  : formatTimestamp(entry.replicas.lastHeartbeatAt)
              }
            />
            <Field
              label="Hệ thống tệp"
              value={FILESYSTEM_LABEL[entry.sandbox.filesystemAccess]}
            />
            <Field
              label="Giới hạn mỗi yêu cầu"
              value={`${entry.sandbox.maxToolCallsPerRequest} lượt gọi tool · ${entry.sandbox.timeoutMs / 1000}s`}
            />
          </dl>

          <div className="mt-3 border-t border-line-hairline pt-3">
            <h4 className="text-[13px] font-medium text-text-muted">Egress được phép</h4>
            {entry.sandbox.allowedEgress.length === 0 ? (
              <p className="mt-1 text-[13px] text-text-body">
                Không có — agent này không gọi được ra ngoài.
              </p>
            ) : (
              <ul className="mt-1.5 flex flex-wrap gap-1.5">
                {entry.sandbox.allowedEgress.map((host) => (
                  <li
                    key={host}
                    className="rounded-sm border border-line-hairline bg-paper-2 px-1.5 py-0.5 font-mono text-[12px] text-text-body"
                  >
                    {host}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {entry.promotedAt !== null ? (
            <p className="mt-3 text-[12px] text-text-muted">
              Promote bởi {entry.promotedBy ?? "—"} lúc{" "}
              <time dateTime={entry.promotedAt} data-numeric className="font-mono">
                {formatTimestamp(entry.promotedAt)}
              </time>
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-text-muted">{label}</dt>
      <dd className="text-text-body">{value}</dd>
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
