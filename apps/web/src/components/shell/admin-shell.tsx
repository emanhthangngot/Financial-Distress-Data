import type { PlaneHealth, Provenance, Role } from "@distresslens/contracts";
import type { ReactNode } from "react";
import { listDemoAccounts } from "@/lib/server/demo-accounts";
import { BrandLockup, BrandMark } from "./brand-mark";
import {
  AgentIcon,
  CostIcon,
  DataIcon,
  ExperimentIcon,
  MenuIcon,
  OperationsIcon,
  SettingsIcon,
  UsersIcon,
} from "./icons";
import { NavRail, type NavGroup, type NavItem } from "./nav-rail";
import { PlaneStatusPill } from "./plane-status";
import { SystemStatus } from "./system-status";
import { UserMenu } from "./user-menu";

/**
 * The operations shell. Deliberately a different product from the analyst
 * workspace: its own wordmark, its own navigation, an environment selector and
 * a plane-status pill in the chrome. The separation is a safety property — an
 * operator must never be unsure which plane a destructive action lands on — so
 * it is expressed in the shell, not just in the route path.
 */

const ADMIN_NAV: readonly NavGroup[] = [
  {
    label: "Vận hành",
    items: [
      { label: "Evidence & GitOps", href: "/ops/evidence", icon: <OperationsIcon /> },
      { label: "Dữ liệu", href: null, icon: <DataIcon />, unavailableNote: "Sắp có" },
    ],
  },
  {
    label: "Mô hình",
    items: [
      { label: "Sổ đăng ký agent", href: "/agents/registry", icon: <AgentIcon /> },
      { label: "Thử nghiệm A/B", href: null, icon: <ExperimentIcon />, unavailableNote: "Sắp có" },
    ],
  },
  {
    label: "Quản trị",
    items: [
      { label: "Người dùng", href: null, icon: <UsersIcon />, unavailableNote: "Sắp có" },
      { label: "Chi phí & Audit", href: null, icon: <CostIcon />, unavailableNote: "Sắp có" },
    ],
  },
];

const ADMIN_NAV_FOOTER: readonly NavItem[] = [
  { label: "Cài đặt", href: null, icon: <SettingsIcon />, unavailableNote: "Sắp có" },
];

export interface AdminShellProps {
  user: { displayName: string; role: Role | null };
  provenance: Provenance;
  environmentLabel: string;
  planeHealth: PlaneHealth;
  /** Sync time shown in the header status, e.g. "23/05/2025 08:46". */
  syncedAtLabel: string;
  /** Desired GitOps commit, shown in the chrome so it is never a click away. */
  desiredCommit: string;
  notificationCount?: number;
  children: ReactNode;
}

export function AdminShell({
  user,
  provenance,
  environmentLabel,
  planeHealth,
  syncedAtLabel,
  desiredCommit,
  notificationCount = 0,
  children,
}: AdminShellProps) {
  // A guest reaching an admin route directly (typed URL) is denied by every
  // platform action, so the platform destinations are dead clicks for them --
  // the rail offers nothing rather than a wall of "not permitted" links.
  const isGuest = user.role === null;
  const navGroups = isGuest ? [] : ADMIN_NAV;
  const navFooter = isGuest ? [] : ADMIN_NAV_FOOTER;
  const demoAccounts = listDemoAccounts();

  return (
    <div className="flex min-h-dvh flex-col lg:flex-row">
      <a href="#main-content" className="skip-link">
        Bỏ qua điều hướng, tới nội dung chính
      </a>

      <div className="hidden w-[248px] shrink-0 flex-col bg-ink-900 lg:flex">
        <div className="px-4 py-4">
          <BrandLockup suffix="Admin" />
        </div>
        <div className="flex-1">
          <NavRail groups={navGroups} footerItems={navFooter} label="Điều hướng vận hành" />
        </div>
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-line-hairline bg-paper-0">
          <div className="flex flex-wrap items-center gap-3 px-4 py-2.5 lg:px-6">
            <details className="lg:hidden">
              <summary className="tap-target flex list-none items-center justify-center rounded-md px-2 text-text-body hover:bg-paper-2 [&::-webkit-details-marker]:hidden">
                <MenuIcon />
                <span className="sr-only">Mở điều hướng vận hành</span>
              </summary>
              <div className="absolute inset-x-0 top-[57px] z-(--z-drawer) bg-ink-900 shadow-(--shadow-overlay)">
                <NavRail groups={navGroups} footerItems={navFooter} label="Điều hướng vận hành" />
              </div>
            </details>

            <span className="flex items-center gap-2 font-semibold text-text-strong lg:hidden">
              <span className="text-ink-900">
                <BrandMark size={26} />
              </span>
              <span className="text-[15px]">
                DistressLens <span className="text-text-muted">Admin</span>
              </span>
            </span>

            <label className="flex items-center gap-2">
              <span className="sr-only">Chọn môi trường</span>
              <select
                defaultValue={environmentLabel}
                className="tap-target rounded-md border border-line-hairline bg-paper-0 px-2.5 py-2 text-[14px] font-medium text-text-strong focus:border-ink-500 focus:outline-none"
              >
                <option>{environmentLabel}</option>
              </select>
            </label>

            <div className="ml-auto flex flex-wrap items-center gap-3">
              <PlaneStatusPill health={planeHealth} />
              <span className="hidden items-baseline gap-1.5 text-[13px] text-text-muted xl:flex">
                Desired commit:
                <code className="font-mono text-text-body">{desiredCommit}</code>
              </span>
              <SystemStatus provenance={provenance} syncedAtLabel={syncedAtLabel} />
              <UserMenu
                displayName={user.displayName}
                role={user.role}
                notificationCount={notificationCount}
                demoAccounts={demoAccounts}
              />
            </div>
          </div>
        </header>

        <main id="main-content" className="min-w-0 flex-1 px-4 py-5 lg:px-6 lg:py-6">
          {children}
        </main>
      </div>
    </div>
  );
}
