import type { PromotionCandidate, PromotionStatus, Role } from "@distresslens/contracts";
import { ExternalLinkIcon } from "@/components/shell/icons";
import { EmptyState } from "@/components/ui/state-panel";
import { RoleActionButton } from "./role-action-button";

/**
 * Model, adapter and agent versions waiting to be promoted.
 *
 * Promotion happens by opening a pull request against the GitOps repository,
 * not by mutating the cluster from this page. The queue therefore links to the
 * PR and offers the promote action only to a role that may request it — the
 * desired state lives in Git, and this surface is where it gets proposed.
 */

const STATUS_LABEL: Record<PromotionStatus, string> = {
  AWAITING_REVIEW: "Chờ duyệt",
  APPROVED: "Đã duyệt",
  REJECTED: "Bị từ chối",
  MERGED: "Đã merge",
};

const STATUS_TONE: Record<PromotionStatus, string> = {
  AWAITING_REVIEW: "border-risk-watch-fill/35 bg-risk-watch-soft text-risk-watch-ink",
  APPROVED: "border-risk-stable-fill/35 bg-risk-stable-soft text-risk-stable-ink",
  REJECTED: "border-risk-high-fill/35 bg-risk-high-soft text-risk-high-ink",
  MERGED: "border-line-strong bg-paper-2 text-text-body",
};

export function PromotionQueue({
  promotions,
  role,
  aal,
}: {
  promotions: readonly PromotionCandidate[];
  role: Role | null;
  aal: "aal1" | "aal2";
}) {
  if (promotions.length === 0) {
    return (
      <EmptyState
        title="Không có ứng viên chờ promote"
        description="Mọi mô hình và agent đang chạy đều trùng với phiên bản đã được duyệt."
      />
    );
  }

  return (
    <ul className="flex flex-col divide-y divide-line-hairline">
      {promotions.map((promotion) => (
        <li
          key={promotion.id}
          className="flex flex-wrap items-start justify-between gap-x-4 gap-y-3 py-3 first:pt-0 last:pb-0"
        >
          <div className="min-w-0">
            <p className="flex flex-wrap items-center gap-2">
              <span className="text-[14px] font-semibold text-text-strong">
                {promotion.candidate}
              </span>
              <span
                className={`rounded-sm border px-1.5 py-0.5 text-[12px] font-medium ${STATUS_TONE[promotion.status]}`}
              >
                {STATUS_LABEL[promotion.status]}
              </span>
            </p>
            <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-text-muted">
              <span>{promotion.kind}</span>
              <span aria-hidden="true">·</span>
              <span>{promotion.owner}</span>
              <span aria-hidden="true">·</span>
              <span data-numeric className="font-mono text-[12px]">
                {promotion.revision}
              </span>
            </p>
          </div>

          <div className="flex flex-wrap items-start gap-3">
            {promotion.pullRequestUrl === null ? null : (
              <a
                href={promotion.pullRequestUrl}
                rel="noreferrer noopener"
                target="_blank"
                className="tap-target inline-flex items-center gap-1 text-[13px] font-medium text-primary-600 underline-offset-2 hover:underline"
              >
                Mở PR promotion
                <ExternalLinkIcon />
                <span className="sr-only">(mở tab mới)</span>
              </a>
            )}
            <RoleActionButton
              action="session.promote"
              role={role}
              aal={aal}
              label="Promote"
              blockedReason={
                promotion.status === "AWAITING_REVIEW"
                  ? null
                  : "Chỉ ứng viên đang chờ duyệt mới promote được."
              }
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
