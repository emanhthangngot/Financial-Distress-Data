import type { ReactNode } from "react";
import { BrandMark } from "@/components/shell/brand-mark";

/**
 * The centred card shared by `/sign-in` and `/sign-up`.
 *
 * Extracted so the two pages cannot drift apart visually -- before this, the
 * card was inlined once in `sign-in/page.tsx` and would have been copy-pasted
 * a second time for sign-up.
 */
export function AuthCard({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  /** Cross-link to the sibling auth page, rendered below the form. */
  footer?: ReactNode;
}) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-paper-1 px-4 py-10">
      {/* BrandLockup is dark-background-only (white wordmark text) -- this
          page is light, so the mark and wordmark are composed directly with
          the same ink-900 tone the compact header lockup uses. */}
      <span className="flex items-center gap-2.5 text-ink-900">
        <BrandMark size={32} />
        <span className="text-[17px] font-bold tracking-tight">DistressLens</span>
      </span>

      <div className="flex w-full max-w-[400px] flex-col gap-5 rounded-md border border-line-hairline bg-paper-0 px-6 py-7 shadow-(--shadow-popover)">
        <div className="flex flex-col gap-1 text-center">
          <h1 className="text-[20px] font-semibold text-text-strong">{title}</h1>
          {description !== undefined ? (
            <p className="text-[14px] text-text-muted">{description}</p>
          ) : null}
        </div>

        {children}
      </div>

      {footer !== undefined ? <div className="text-[14px] text-text-body">{footer}</div> : null}
    </main>
  );
}
