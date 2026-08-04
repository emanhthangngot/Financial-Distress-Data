import { DISCLAIMER_TEXT, type DisclaimerSurface } from "@distresslens/contracts";

/**
 * The educational/non-investment disclaimer. It takes the surface it is
 * rendered on as a required prop so a Playwright assertion can target the exact
 * surface, and so adding a decision-support page without a disclaimer is a type
 * error rather than an omission nobody notices.
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
      className="rounded-md border border-line-hairline bg-paper-2 px-3.5 py-2.5 text-[13px] leading-relaxed text-text-body shadow-[inset_3px_0_0_0_var(--color-line-strong)]"
    >
      {DISCLAIMER_TEXT}
    </aside>
  );
}
