import { authorize, type Role, type SessionAction } from "@distresslens/contracts";
import { Button, type ButtonVariant } from "@/components/ui/button";

/**
 * A lifecycle control that knows why it is unavailable.
 *
 * The decision is the same `authorize` the server action calls, so a control
 * the UI enables is a control the server will accept, and vice versa. This is
 * presentation only — the server re-runs the identical check on the request,
 * because a disabled button stops nobody who can send an HTTP request.
 *
 * A denied control renders disabled with its reason rather than disappearing:
 * an operator who cannot see the promote button cannot tell whether they lack
 * the role or the feature is missing.
 */

export interface RoleActionButtonProps {
  action: SessionAction;
  role: Role | null;
  aal: "aal1" | "aal2";
  label: string;
  variant?: ButtonVariant;
  /** Set when the action is blocked by something other than authorization. */
  blockedReason?: string | null;
}

export function RoleActionButton({
  action,
  role,
  aal,
  label,
  variant = "secondary",
  blockedReason = null,
}: RoleActionButtonProps) {
  const decision = authorize({ role, aal }, action);
  const reason = decision.allowed ? blockedReason : decision.reason;
  const disabled = reason !== null;

  return (
    <span className="flex flex-col gap-1">
      <Button
        type="button"
        variant={variant}
        disabled={disabled}
        aria-describedby={disabled ? `${action}-reason` : undefined}
      >
        {label}
      </Button>
      {disabled ? (
        <span id={`${action}-reason`} className="max-w-[26ch] text-[12px] text-text-muted">
          {reason}
        </span>
      ) : null}
    </span>
  );
}
