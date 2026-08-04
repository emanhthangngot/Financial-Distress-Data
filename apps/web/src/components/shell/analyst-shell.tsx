import type { Provenance, Role } from "@distresslens/contracts";
import type { ReactNode } from "react";
import { BrandLockup, BrandMark } from "./brand-mark";
import { EvidenceRibbon } from "./evidence-ribbon";
import { HeaderSearch } from "./header-search";
import {
  AgentIcon,
  CompaniesIcon,
  MenuIcon,
  OverviewIcon,
  ReportIcon,
  SettingsIcon,
  SignOutIcon,
  WatchlistIcon,
} from "./icons";
import { NavRail, type NavItem } from "./nav-rail";
import { UserMenu } from "./user-menu";

/**
 * The analyst workspace shell: persistent navy rail, light working canvas.
 *
 * Watchlist and Settings appear in the rail because the approved reference and
 * the product contract both name them, but they are marked unavailable rather
 * than linked: the phase-02 route inventory does not include them, and a nav
 * item that 404s is worse than one that admits it has not shipped.
 */

const ANALYST_NAV: readonly NavItem[] = [
  { label: "Tổng quan", href: "/", icon: <OverviewIcon /> },
  { label: "Doanh nghiệp", href: "/companies", icon: <CompaniesIcon /> },
  { label: "Danh sách theo dõi", href: null, icon: <WatchlistIcon />, unavailableNote: "Sắp có" },
  { label: "AI Phân tích", href: "/agents/chat", icon: <AgentIcon /> },
  { label: "Báo cáo", href: "/reports", icon: <ReportIcon /> },
];

const ANALYST_NAV_FOOTER: readonly NavItem[] = [
  { label: "Cài đặt", href: null, icon: <SettingsIcon />, unavailableNote: "Sắp có" },
  { label: "Đăng xuất", href: "/sign-out", icon: <SignOutIcon /> },
];

export interface AnalystShellProps {
  user: { displayName: string; role: Role };
  provenance: Provenance;
  /** Header freshness line, e.g. "Đồng bộ lần cuối: 23/05/2025 08:46". */
  freshnessLabel: string;
  searchDefaultValue?: string;
  notificationCount?: number;
  children: ReactNode;
}

export function AnalystShell({
  user,
  provenance,
  freshnessLabel,
  searchDefaultValue,
  notificationCount = 0,
  children,
}: AnalystShellProps) {
  return (
    <div className="flex min-h-dvh flex-col lg:flex-row">
      <a href="#main-content" className="skip-link">
        Bỏ qua điều hướng, tới nội dung chính
      </a>

      {/* Desktop rail. Fixed width so dense tables get a predictable canvas. */}
      <div className="hidden w-[248px] shrink-0 flex-col bg-ink-900 lg:flex">
        <div className="px-4 py-4">
          <BrandLockup />
        </div>
        <div className="flex-1">
          <NavRail items={ANALYST_NAV} footerItems={ANALYST_NAV_FOOTER} label="Điều hướng phân tích" />
        </div>
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-line-hairline bg-paper-0">
          <div className="flex items-center gap-3 px-4 py-2.5 lg:px-6">
            {/* Mobile navigation. A <details> drawer keeps the rail reachable
                without shipping a client bundle just to open a menu. */}
            <details className="lg:hidden">
              <summary className="tap-target flex list-none items-center justify-center rounded-md px-2 text-text-body hover:bg-paper-2 [&::-webkit-details-marker]:hidden">
                <MenuIcon />
                <span className="sr-only">Mở điều hướng</span>
              </summary>
              <div className="absolute inset-x-0 top-[57px] z-(--z-drawer) bg-ink-900 shadow-(--shadow-overlay)">
                <NavRail
                  items={ANALYST_NAV}
                  footerItems={ANALYST_NAV_FOOTER}
                  label="Điều hướng phân tích"
                />
              </div>
            </details>

            <span className="text-ink-900 lg:hidden">
              <BrandLockupCompact />
            </span>

            <div className="hidden min-w-0 flex-1 justify-center lg:flex">
              <HeaderSearch defaultValue={searchDefaultValue} />
            </div>

            <div className="ml-auto flex items-center gap-3">
              <span className="hidden text-[13px] text-text-muted xl:block">{freshnessLabel}</span>
              <UserMenu
                displayName={user.displayName}
                role={user.role}
                notificationCount={notificationCount}
              />
            </div>
          </div>

          {/* Search drops below the header row on narrow screens rather than
              competing with the brand and account controls. */}
          <div className="px-4 pb-2.5 lg:hidden">
            <HeaderSearch defaultValue={searchDefaultValue} />
          </div>
        </header>

        <EvidenceRibbon provenance={provenance} />

        <main id="main-content" className="min-w-0 flex-1 px-4 py-5 lg:px-6 lg:py-6">
          {children}
        </main>
      </div>
    </div>
  );
}

function BrandLockupCompact() {
  return (
    <span className="flex items-center gap-2 font-semibold text-text-strong">
      <span className="text-ink-900">
        <BrandMark size={26} />
      </span>
      <span className="text-[15px]">DistressLens</span>
    </span>
  );
}
