import type { Provenance, Role } from "@distresslens/contracts";
import type { ReactNode } from "react";
import { AnalysisAssistant } from "@/components/assistant/analysis-assistant";
import type { AssistantContext } from "@/lib/assistant/assistant-context";
import { listDemoAccounts } from "@/lib/server/demo-accounts";
import { BrandLockup, BrandMark } from "./brand-mark";
import { HeaderSearch } from "./header-search";
import {
  CompaniesIcon,
  CompareIcon,
  MenuIcon,
  OperationsIcon,
  OverviewIcon,
  ReportIcon,
  SettingsIcon,
  SignOutIcon,
  WatchlistIcon,
} from "./icons";
import { NavRail, type NavGroup, type NavItem } from "./nav-rail";
import { SystemStatus } from "./system-status";
import { UserMenu } from "./user-menu";

/**
 * The analyst workspace shell: persistent navy rail, light working canvas.
 *
 * Navigation is grouped by what the analyst is doing — reading the portfolio,
 * managing their own working set, or crossing into platform surfaces — rather
 * than listed flat. Items the product names but has not shipped stay visible
 * with a "Sắp có" badge instead of linking to a 404.
 *
 * There is no AI entry in the rail. The assistant is a floating support panel
 * available on every surface with that surface's context, so promoting it to a
 * destination would make it a place the analyst has to go instead of a tool
 * they have to hand.
 */

const ANALYST_NAV: readonly NavGroup[] = [
  {
    label: "Phân tích",
    items: [
      { label: "Tổng quan", href: "/", icon: <OverviewIcon /> },
      { label: "Doanh nghiệp", href: "/companies", icon: <CompaniesIcon /> },
      { label: "So sánh mô hình", href: "/compare", icon: <CompareIcon /> },
    ],
  },
  {
    label: "Quản lý",
    items: [
      { label: "Báo cáo", href: "/reports", icon: <ReportIcon /> },
      // "Theo dõi" rather than "Danh sách theo dõi": the longer label truncates
      // in a 232px rail once the "Sắp có" badge takes its place on the row.
      { label: "Theo dõi", href: null, icon: <WatchlistIcon />, unavailableNote: "Sắp có" },
    ],
  },
  {
    label: "Hệ thống",
    items: [{ label: "Vận hành", href: "/ops/evidence", icon: <OperationsIcon /> }],
  },
];

const ANALYST_NAV_FOOTER: readonly NavItem[] = [
  { label: "Cài đặt", href: null, icon: <SettingsIcon />, unavailableNote: "Sắp có" },
  { label: "Đăng xuất", href: "/sign-out", icon: <SignOutIcon /> },
];

/**
 * A guest is denied `analyst.query` and `session.read` alike (both require a
 * signed-in caller), so every destination but the landing page is a dead
 * click for them. Rather than render each one into a "not permitted" state,
 * the rail only offers what a guest can actually open.
 */
const GUEST_NAV: readonly NavGroup[] = [
  { label: "Phân tích", items: [{ label: "Tổng quan", href: "/", icon: <OverviewIcon /> }] },
];

export interface AnalystShellProps {
  user: { displayName: string; role: Role | null };
  provenance: Provenance;
  /** Sync time shown in the header status, e.g. "23/05/2025 08:46". */
  syncedAtLabel: string;
  /** What the assistant is allowed to know about this page. */
  assistantContext: AssistantContext;
  searchDefaultValue?: string;
  notificationCount?: number;
  children: ReactNode;
}

export function AnalystShell({
  user,
  provenance,
  syncedAtLabel,
  assistantContext,
  searchDefaultValue,
  notificationCount = 0,
  children,
}: AnalystShellProps) {
  const isGuest = user.role === null;
  const navGroups = isGuest ? GUEST_NAV : ANALYST_NAV;
  const navFooter = isGuest ? [] : ANALYST_NAV_FOOTER;
  const demoAccounts = listDemoAccounts();

  return (
    <div className="flex min-h-dvh flex-col lg:flex-row">
      <a href="#main-content" className="skip-link">
        Bỏ qua điều hướng, tới nội dung chính
      </a>

      {/* Desktop rail. Fixed width so dense tables get a predictable canvas. */}
      <div data-print-hidden className="hidden w-[232px] shrink-0 flex-col bg-ink-900 lg:flex">
        <div className="px-4 py-4">
          <BrandLockup />
        </div>
        <div className="flex-1">
          <NavRail groups={navGroups} footerItems={navFooter} label="Điều hướng phân tích" />
        </div>
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <header data-print-hidden className="border-b border-line-hairline bg-paper-0">
          <div className="flex items-center gap-3 px-4 py-2.5 lg:px-6">
            {/* Mobile navigation. A <details> drawer keeps the rail reachable
                without shipping a client bundle just to open a menu. */}
            <details className="lg:hidden">
              <summary className="tap-target flex list-none items-center justify-center rounded-md px-2 text-text-body hover:bg-paper-2 [&::-webkit-details-marker]:hidden">
                <MenuIcon />
                <span className="sr-only">Mở điều hướng</span>
              </summary>
              <div className="absolute inset-x-0 top-[57px] z-(--z-drawer) bg-ink-900 shadow-(--shadow-overlay)">
                <NavRail groups={navGroups} footerItems={navFooter} label="Điều hướng phân tích" />
              </div>
            </details>

            {/* The wordmark yields before the account controls do: on a 390px
                header the controls are what the analyst reaches for, and the
                brand is already established by the page they are on. */}
            <span className="min-w-0 shrink text-ink-900 lg:hidden">
              <BrandLockupCompact />
            </span>

            <div className="hidden min-w-0 flex-1 lg:flex">
              <HeaderSearch defaultValue={searchDefaultValue} />
            </div>

            <div className="ml-auto flex items-center gap-1">
              <SystemStatus provenance={provenance} syncedAtLabel={syncedAtLabel} />
              <UserMenu
                displayName={user.displayName}
                role={user.role}
                notificationCount={notificationCount}
                demoAccounts={demoAccounts}
              />
            </div>
          </div>

          {/* Search drops below the header row on narrow screens rather than
              competing with the brand and account controls. */}
          <div className="px-4 pb-2.5 lg:hidden">
            <HeaderSearch defaultValue={searchDefaultValue} />
          </div>
        </header>

        <main id="main-content" className="min-w-0 flex-1 px-4 py-5 lg:px-6 lg:py-6">
          {children}
        </main>
      </div>

      <AnalysisAssistant context={assistantContext} />
    </div>
  );
}

function BrandLockupCompact() {
  return (
    <span className="flex min-w-0 items-center gap-2 font-semibold text-text-strong">
      <span className="shrink-0 text-ink-900">
        <BrandMark size={26} />
      </span>
      <span className="truncate text-[15px]">DistressLens</span>
    </span>
  );
}
