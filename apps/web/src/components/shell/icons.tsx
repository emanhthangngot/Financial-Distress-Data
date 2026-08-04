import type { SVGProps } from "react";

/**
 * Inline icon set. Hand-drawn on a 24px grid with a 1.6 stroke to match the
 * engraved-hairline language; an icon dependency would arrive with its own
 * weight and corner radius and fight the token system.
 *
 * Icons are decorative here — every navigation item and control ships a text
 * label, so icons carry `aria-hidden` and never become the only signal.
 */

type IconProps = SVGProps<SVGSVGElement>;

function Icon({ children, ...props }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      width={20}
      height={20}
      {...props}
    >
      {children}
    </svg>
  );
}

export function OverviewIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 11 12 4l8 7" />
      <path d="M6 10v9h12v-9" />
      <path d="M10 19v-5h4v5" />
    </Icon>
  );
}

export function CompaniesIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <rect x="4" y="4" width="10" height="16" rx="1" />
      <path d="M14 9h6v11h-6" />
      <path d="M7 8h4M7 12h4M7 16h4M17 12h1M17 16h1" />
    </Icon>
  );
}

export function WatchlistIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m12 4 2.4 4.9 5.4.8-3.9 3.8.9 5.4-4.8-2.5-4.8 2.5.9-5.4L4.2 9.7l5.4-.8z" />
    </Icon>
  );
}

export function AgentIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 4v3" />
      <rect x="5" y="7" width="14" height="10" rx="2" />
      <path d="M9 12h.01M15 12h.01" />
      <path d="M9 20h6" />
    </Icon>
  );
}

export function ReportIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M7 3h7l4 4v14H7z" />
      <path d="M14 3v4h4" />
      <path d="M10 12h5M10 16h5" />
    </Icon>
  );
}

export function SettingsIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v2.5M12 18.5V21M4.2 7.5l2.2 1.3M17.6 15.2l2.2 1.3M4.2 16.5l2.2-1.3M17.6 8.8l2.2-1.3" />
    </Icon>
  );
}

export function SignOutIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M10 4H6a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h4" />
      <path d="M15 8l4 4-4 4" />
      <path d="M19 12h-9" />
    </Icon>
  );
}

export function SearchIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="11" cy="11" r="6" />
      <path d="m16 16 4 4" />
    </Icon>
  );
}

export function BellIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M6 9a6 6 0 1 1 12 0c0 4 1.5 5.5 1.5 5.5h-15S6 13 6 9Z" />
      <path d="M10 18a2 2 0 0 0 4 0" />
    </Icon>
  );
}

export function ChevronDownIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m6 9 6 6 6-6" />
    </Icon>
  );
}

export function MenuIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </Icon>
  );
}

export function OperationsIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 18h16" />
      <path d="M7 18v-5M12 18V7M17 18v-8" />
    </Icon>
  );
}

export function DataIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <ellipse cx="12" cy="6" rx="7" ry="2.6" />
      <path d="M5 6v12c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6V6" />
      <path d="M5 12c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6" />
    </Icon>
  );
}

export function ExperimentIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M9 3v6.5L4.6 17A2 2 0 0 0 6.3 20h11.4a2 2 0 0 0 1.7-3L15 9.5V3" />
      <path d="M8 3h8" />
      <path d="M7.5 14h9" />
    </Icon>
  );
}

export function UsersIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="9" cy="8" r="3" />
      <path d="M4 19a5 5 0 0 1 10 0" />
      <path d="M16 6.5a3 3 0 0 1 0 5.8" />
      <path d="M17 19a5 5 0 0 0-2.2-3.6" />
    </Icon>
  );
}

export function CostIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 7v10" />
      <path d="M14.5 9.5a2.5 2.5 0 0 0-5 .6c0 2.6 5 1.4 5 4a2.5 2.5 0 0 1-5 .4" />
    </Icon>
  );
}

export function InfoIcon(props: IconProps) {
  return (
    <Icon {...props} width={16} height={16}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 11v5.5" />
      <path d="M12 7.8h.01" />
    </Icon>
  );
}

export function CompareIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M5 6h6M5 6l2.5-2.5M5 6l2.5 2.5" />
      <path d="M19 18h-6M19 18l-2.5-2.5M19 18l-2.5 2.5" />
      <path d="M5 12h14" />
    </Icon>
  );
}

/**
 * The assistant glyph: a lens over a spark. It is the only icon allowed to
 * carry the AI accent colour, which is how the assistant stays recognisable
 * without a badge on every surface it touches.
 */
export function AssistantIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="10.5" cy="10.5" r="6" />
      <path d="m15 15 4.5 4.5" />
      <path d="M10.5 7.5 11.4 9.6 13.5 10.5 11.4 11.4 10.5 13.5 9.6 11.4 7.5 10.5 9.6 9.6Z" />
    </Icon>
  );
}

export function CloseIcon(props: IconProps) {
  return (
    <Icon {...props} width={18} height={18}>
      <path d="m6 6 12 12M18 6 6 18" />
    </Icon>
  );
}

export function MinimizeIcon(props: IconProps) {
  return (
    <Icon {...props} width={18} height={18}>
      <path d="M6 14h12" />
    </Icon>
  );
}

export function ExpandIcon(props: IconProps) {
  return (
    <Icon {...props} width={18} height={18}>
      <path d="M4 9V4h5" />
      <path d="M20 15v5h-5" />
      <path d="M4 4l6 6" />
      <path d="M20 20l-6-6" />
    </Icon>
  );
}

export function CollapseIcon(props: IconProps) {
  return (
    <Icon {...props} width={18} height={18}>
      <path d="M10 4v5H5" />
      <path d="M14 20v-5h5" />
      <path d="M4 3.5 9 9" />
      <path d="M20 20.5 15 15" />
    </Icon>
  );
}

export function SendIcon(props: IconProps) {
  return (
    <Icon {...props} width={18} height={18}>
      <path d="M5 12 20 5l-7 15-2.2-5.8Z" />
      <path d="M10.8 14.2 20 5" />
    </Icon>
  );
}

export function LockIcon(props: IconProps) {
  return (
    <Icon {...props} width={14} height={14}>
      <rect x="5" y="11" width="14" height="9" rx="1.5" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </Icon>
  );
}

export function ExternalLinkIcon(props: IconProps) {
  return (
    <Icon {...props} width={16} height={16}>
      <path d="M13 5h6v6" />
      <path d="M19 5 10 14" />
      <path d="M18 14v4a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h4" />
    </Icon>
  );
}
