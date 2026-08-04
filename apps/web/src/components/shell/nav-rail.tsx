"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { LockIcon } from "./icons";

/**
 * The left rail shared by both shells. It is a client component only because
 * the active item is derived from the current path; nothing else here needs
 * browser state.
 *
 * A `href: null` item is a surface the product names but has not shipped. It
 * renders visibly disabled with a reason rather than as a link that 404s — the
 * information architecture stays honest about what exists.
 */

export interface NavItem {
  label: string;
  href: string | null;
  icon: ReactNode;
  /** Shown when href is null, e.g. "Sắp có". */
  unavailableNote?: string;
}

export interface NavRailProps {
  items: readonly NavItem[];
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
        className="tap-target flex items-center gap-3 rounded-md px-3 py-2.5 text-[15px] text-paper-3/70"
      >
        <span className="shrink-0">{item.icon}</span>
        <span>{item.label}</span>
        {/* A lock glyph rather than a "Sắp có" chip: the chip crowded the rail
            and truncated the label, and the label is the reference information
            architecture. The reason still reaches assistive tech and hover. */}
        {item.unavailableNote !== undefined ? (
          <span className="ml-auto shrink-0" title={item.unavailableNote}>
            <LockIcon />
            <span className="sr-only">{item.unavailableNote}</span>
          </span>
        ) : null}
      </span>
    );
  }

  const active = isActive(pathname, item.href);

  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={[
        "tap-target flex items-center gap-3 rounded-md px-3 py-2.5 text-[15px]",
        "transition-colors duration-(--duration-fast) ease-(--ease-standard)",
        active
          ? // Active state carries a left marker as well as a fill, so it does
            // not rely on color alone.
            "bg-paper-0 font-semibold text-ink-900 shadow-[inset_3px_0_0_0_var(--color-ink-600)]"
          : "text-paper-2 hover:bg-ink-800",
      ].join(" ")}
    >
      <span className="shrink-0">{item.icon}</span>
      <span className="truncate">{item.label}</span>
    </Link>
  );
}

export function NavRail({ items, footerItems, label }: NavRailProps) {
  const pathname = usePathname();

  return (
    <nav aria-label={label} className="on-ink flex h-full flex-col gap-1 p-3">
      <ul className="flex flex-col gap-1">
        {items.map((item) => (
          <li key={item.label}>
            <NavLink item={item} pathname={pathname} />
          </li>
        ))}
      </ul>

      {footerItems !== undefined && footerItems.length > 0 ? (
        <ul className="mt-auto flex flex-col gap-1 border-t border-ink-800 pt-3">
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
