import { DISCLAIMER_TEXT, type DisclaimerSurface } from "@distresslens/contracts";
import { InfoIcon } from "./icons";

/**
 * The educational/non-investment disclaimer.
 *
 * It takes the surface it is rendered on as a required prop so a Playwright
 * assertion can target the exact surface, and so adding a decision-support page
 * without a disclaimer is a type error rather than an omission nobody notices.
 *
 * The block variant is a single-line notice, not a panel: it must be
 * unmissable on every decision surface and still cost almost no vertical space
 * on a dense dashboard.
 */
export function DisclaimerBanner({
  surface,
  variant = "block",
}: {
  surface: DisclaimerSurface;
  variant?: "block" | "inline";
}) {
  if (variant === "inline") {
    return (
      <p
        data-disclaimer-surface={surface}
        className="text-[12px] leading-relaxed text-text-muted"
      >
        {DISCLAIMER_TEXT}
      </p>
    );
  }

  return (
    <aside
      data-disclaimer-surface={surface}
      className="flex items-center gap-2.5 rounded-md border border-line-hairline bg-paper-2 px-3.5 py-2 text-[13px] leading-relaxed text-text-body"
    >
      <span aria-hidden="true" className="shrink-0 text-primary-600">
        <InfoIcon />
      </span>
      {DISCLAIMER_TEXT}
    </aside>
  );
}
