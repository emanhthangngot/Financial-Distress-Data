import type { StateCopy } from "@distresslens/contracts";
import type { ReactNode } from "react";

/**
 * The one renderer for every non-success state.
 *
 * It takes a `StateCopy` rather than free text, which is what forces each state
 * to answer the same three questions the contract requires: what is
 * unavailable, what is being shown instead, and what to do next. A blank area
 * where data failed to load is never an acceptable outcome, so this is what
 * fills it.
 */

export function StatePanel({
  copy,
  tone = "neutral",
  action,
}: {
  copy: StateCopy;
  tone?: "neutral" | "warning" | "critical";
  /** Retry, sign-in or navigation control matching `copy.nextAction`. */
  action?: ReactNode;
}) {
  const toneClass = {
    neutral: "border-line-hairline bg-paper-1",
    warning: "border-risk-watch-fill/30 bg-risk-watch-soft",
    critical: "border-risk-high-fill/30 bg-risk-high-soft",
  }[tone];

  return (
    <div className={`rounded-md border px-4 py-5 text-[14px] ${toneClass}`}>
      <p className="font-medium text-text-strong">{copy.unavailable}</p>
      {copy.lastKnown !== null ? (
        <p className="mt-1.5 text-text-body">{copy.lastKnown}</p>
      ) : null}
      <p className="mt-1.5 text-text-muted">{copy.nextAction}</p>
      {action !== undefined ? <div className="mt-3.5">{action}</div> : null}
    </div>
  );
}

/**
 * Empty state for a section that loaded correctly and has nothing to show.
 * Distinct from `StatePanel` because an empty list is an invitation to act, not
 * a failure to report.
 */
export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
      <p className="text-[15px] font-semibold text-text-strong">{title}</p>
      <p className="max-w-[42ch] text-[14px] text-text-muted">{description}</p>
      {action !== undefined ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

/**
 * Loading placeholder. Shaped like the content it replaces so the page does not
 * reflow when data arrives.
 */
export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={`block animate-pulse rounded-sm bg-paper-2 ${className}`}
    />
  );
}

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div role="status" className="flex flex-col gap-3 px-5 py-4">
      <span className="sr-only">Đang tải dữ liệu</span>
      <Skeleton className="h-4 w-1/3" />
      {Array.from({ length: lines }, (_, index) => (
        <Skeleton key={index} className="h-3.5 w-full" />
      ))}
    </div>
  );
}
