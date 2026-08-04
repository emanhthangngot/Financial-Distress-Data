import type { Role } from "@distresslens/contracts";
import { BellIcon, ChevronDownIcon, SignOutIcon } from "./icons";

/**
 * User and notification controls.
 *
 * Built on `<details>` rather than a JS popover: it is keyboard-operable and
 * screen-reader-announced without hydration, which matters because the header
 * must stay usable on a degraded page where a client bundle failed to load.
 */

const ROLE_LABELS: Record<Role, string> = {
  analyst: "Chuyên viên phân tích",
  platform_viewer: "Nền tảng — chỉ đọc",
  platform_operator: "Nền tảng — vận hành",
  platform_admin: "Quản trị viên",
};

export interface UserMenuProps {
  displayName: string;
  role: Role;
  /** Unread notification count; 0 renders no badge. */
  notificationCount?: number;
  /** Rendered on the navy admin chrome rather than the light analyst header. */
  onInk?: boolean;
}

export function UserMenu({
  displayName,
  role,
  notificationCount = 0,
  onInk = false,
}: UserMenuProps) {
  const controlTone = onInk
    ? "text-paper-1 hover:bg-ink-800"
    : "text-text-body hover:bg-paper-2";

  return (
    <div className="flex min-w-0 shrink items-center gap-1">
      <button
        type="button"
        className={`tap-target relative flex items-center justify-center rounded-md px-2 ${controlTone}`}
      >
        <BellIcon />
        <span className="sr-only">
          Thông báo{notificationCount > 0 ? `: ${notificationCount} chưa đọc` : ": không có mới"}
        </span>
        {notificationCount > 0 ? (
          <span
            aria-hidden="true"
            className="absolute right-1.5 top-1.5 min-w-[16px] rounded-full bg-risk-high-fill px-1 text-center font-mono text-[10px] font-semibold leading-4 text-paper-0"
          >
            {notificationCount}
          </span>
        ) : null}
      </button>

      <details className="relative">
        <summary
          className={`tap-target flex list-none items-center gap-2 rounded-md px-2 py-1.5 ${controlTone} [&::-webkit-details-marker]:hidden`}
        >
          <span
            aria-hidden="true"
            className="flex h-8 w-8 items-center justify-center rounded-full bg-ink-700 font-mono text-[13px] font-semibold text-paper-0"
          >
            {initials(displayName)}
          </span>
          <span className="hidden text-left text-[14px] font-medium lg:block">{displayName}</span>
          <ChevronDownIcon width={16} height={16} />
          <span className="sr-only">Mở menu tài khoản</span>
        </summary>

        {/* Capped to the viewport: a fixed 240px panel anchored to the right
            edge of a 390px header pushes the document wider than the screen. */}
        <div className="absolute right-0 z-(--z-overlay) mt-1 w-60 max-w-[calc(100vw-2rem)] rounded-md border border-line-hairline bg-paper-0 p-1.5 shadow-(--shadow-popover)">
          <p className="px-2.5 py-2">
            <span className="block text-[14px] font-semibold text-text-strong">{displayName}</span>
            <span className="block text-[13px] text-text-muted">{ROLE_LABELS[role]}</span>
          </p>
          <hr className="my-1 border-line-hairline" />
          <a
            href="/sign-out"
            className="tap-target flex items-center gap-2.5 rounded-sm px-2.5 py-2 text-[14px] text-text-body hover:bg-paper-2"
          >
            <SignOutIcon />
            Đăng xuất
          </a>
        </div>
      </details>
    </div>
  );
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  const last = parts.at(-1) ?? "";
  const first = parts.at(0) ?? "";
  // Vietnamese names put the given name last, so the trailing word is the one
  // a reader identifies the person by.
  return `${last.charAt(0)}${first.charAt(0)}`.toUpperCase();
}
