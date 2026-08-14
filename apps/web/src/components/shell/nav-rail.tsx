"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

/**
 * The left rail shared by both shells. It is a client component only because
 * the active item is derived from the current path; nothing else here needs
 * browser state.
 *
 * Items are grouped under quiet section labels so the rail reads as an
 * information architecture rather than a flat list of links.
 *
 * A `href: null` item is a surface the product names but has not shipped. It
 * renders visibly disabled with a "Sắp có" badge rather than as a link that
 * 404s — the architecture stays honest about what exists, and the reason is
 * written out instead of hidden behind a lock glyph.
 */

export interface NavItem {
  label: string;
  href: string | null;
  icon: ReactNode;
  /** Shown as a badge when href is null, e.g. "Sắp có". */
  unavailableNote?: string;
}

export interface NavGroup {
  /** Section label, e.g. "Phân tích". Null renders the group unlabelled. */
  label: string | null;
  items: readonly NavItem[];
}

export interface NavRailProps {
  groups: readonly NavGroup[];
  footerItems?: readonly NavItem[];
  /** Accessible name for the landmark, e.g. "Điều hướng phân tích". */
  label: string;
}

function isActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavLink({ item, pathname }: { item: NavItem; pathname: string }) {
  if (item.href === null) {
    return (
      <span
        aria-disabled="true"
        className="tap-target flex items-center gap-3 rounded-md px-3 py-2 text-[14px] text-paper-3/60"
      >
        <span className="shrink-0">{item.icon}</span>
        <span className="truncate">{item.label}</span>
        {item.unavailableNote !== undefined ? (
          <span className="ml-auto shrink-0 rounded-sm border border-paper-3/25 px-1.5 py-0.5 text-[11px] font-medium text-paper-3/70">
            {item.unavailableNote}
          </span>
        ) : null}
      </span>
    );
  }

  const active = isActive(pathname, item.href);

  return (
    <Link
      href={item.href}
      // `/sign-out` is a GET route with a side effect (it clears both
      // session cookies and revokes the Supabase session). next/link
      // prefetches every link it renders by default, and a prefetch to a
      // route handler actually invokes its GET -- prefetching this one would
      // silently sign the visitor out the moment the rail renders it into
      // view, never on an actual click. No other item here has that hazard.
      prefetch={item.href === "/sign-out" ? false : undefined}
      aria-current={active ? "page" : undefined}
      className={[
        "tap-target relative flex items-center gap-3 rounded-md px-3 py-2 text-[14px]",
        "transition-colors duration-(--duration-fast) ease-(--ease-standard)",
        active
          ? // A translucent wash plus a left marker, not a solid white slab:
            // the rail keeps reading as one surface, and the active state does
            // not rely on colour alone.
            "bg-primary-500/18 font-semibold text-primary-300 shadow-[inset_3px_0_0_0_var(--color-primary-500)]"
          : "text-paper-2/85 hover:bg-paper-0/8 hover:text-paper-0",
      ].join(" ")}
    >
      <span className="shrink-0">{item.icon}</span>
      <span className="truncate">{item.label}</span>
    </Link>
  );
}

export function NavRail({ groups, footerItems, label }: NavRailProps) {
  const pathname = usePathname();

  return (
    <nav aria-label={label} className="on-ink flex h-full flex-col gap-5 p-3">
      {groups.map((group, index) => (
        <div key={group.label ?? `group-${index}`}>
          {group.label !== null ? (
            <h2 className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-paper-3/55">
              {group.label}
            </h2>
          ) : null}
          <ul className="flex flex-col gap-0.5">
            {group.items.map((item) => (
              <li key={item.label}>
                <NavLink item={item} pathname={pathname} />
              </li>
            ))}
          </ul>
        </div>
      ))}

      {footerItems !== undefined && footerItems.length > 0 ? (
        <ul className="mt-auto flex flex-col gap-0.5 border-t border-paper-0/10 pt-3">
          {footerItems.map((item) => (
            <li key={item.label}>
              <NavLink item={item} pathname={pathname} />
            </li>
          ))}
        </ul>
      ) : null}
    </nav>
  );
}
