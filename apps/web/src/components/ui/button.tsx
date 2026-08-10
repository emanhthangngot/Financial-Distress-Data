import type { ButtonHTMLAttributes, AnchorHTMLAttributes, ReactNode } from "react";

/**
 * Buttons and button-shaped links.
 *
 * One place decides height, radius, focus and disabled treatment, so a control
 * added later cannot ship its own. Every variant meets the 44px touch target
 * through `tap-target` rather than through padding that varies per caller.
 */

export type ButtonVariant = "primary" | "secondary" | "ghost" | "assistant";

const VARIANT: Record<ButtonVariant, string> = {
  primary:
    "bg-primary-600 text-paper-0 hover:bg-primary-700 disabled:bg-paper-3 disabled:text-text-muted",
  secondary:
    "border border-line-strong bg-paper-0 text-text-body hover:bg-paper-2 disabled:text-text-muted",
  ghost: "text-primary-600 hover:bg-primary-050 disabled:text-text-muted",
  assistant: "bg-ai-500 text-paper-0 hover:bg-ai-600 disabled:bg-paper-3 disabled:text-text-muted",
};

const BASE =
  "tap-target inline-flex items-center justify-center gap-2 rounded-md px-4 py-2.5 text-[14px] font-semibold transition-colors duration-(--duration-fast) ease-(--ease-standard) disabled:cursor-not-allowed";

export function Button({
  variant = "primary",
  className = "",
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  children: ReactNode;
}) {
  return (
    <button className={`${BASE} ${VARIANT[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}

export function ButtonLink({
  variant = "secondary",
  className = "",
  children,
  ...props
}: AnchorHTMLAttributes<HTMLAnchorElement> & {
  variant?: ButtonVariant;
  children: ReactNode;
}) {
  return (
    <a className={`${BASE} ${VARIANT[variant]} ${className}`} {...props}>
      {children}
    </a>
  );
}
