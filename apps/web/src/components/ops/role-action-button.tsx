"use client";

import { useActionState } from "react";
import {
  authorize,
  type Role,
  type SessionAction,
  type SessionState,
} from "@distresslens/contracts";
import { Button, type ButtonVariant } from "@/components/ui/button";
import {
  requestSessionTransition,
  type ActionResult,
} from "@/lib/server/session-actions";

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
 *
 * When `transition` is set, the control posts a `requestSessionTransition`
 * carrying the target state, session id, idempotency key and the fencing token
 * the page observed. The idempotency key is minted per render, so retrying the
 * same rendered form replays the same request while a fresh render (after the
 * page revalidates) mints a new one. A stale fencing token is rejected by the
 * database with a fencing error, never silently applied.
 */

const INITIAL_ACTION: ActionResult = { ok: true, message: "" };

export interface RoleActionTransition {
  targetState: SessionState;
  sessionId: string;
  fencingToken: string;
}

export interface RoleActionButtonProps {
  action: SessionAction;
  role: Role | null;
  aal: "aal1" | "aal2";
  label: string;
  variant?: ButtonVariant;
  /** Set when the action is blocked by something other than authorization. */
  blockedReason?: string | null;
  /**
   * When set, the enabled control submits a lifecycle transition. Omitting it
   * (e.g. for export, which is not a state transition) renders a plain control.
   */
  transition?: RoleActionTransition | null;
}

export function RoleActionButton({
  action,
  role,
  aal,
  label,
  variant = "secondary",
  blockedReason = null,
  transition = null,
}: RoleActionButtonProps) {
  const [result, formAction, pending] = useActionState<ActionResult, FormData>(
    requestSessionTransition,
    INITIAL_ACTION,
  );

  const decision = authorize({ role, aal }, action);
  const reason = decision.allowed ? blockedReason : decision.reason;
  const disabled = reason !== null;

  if (!disabled && transition !== null) {
    const idempotencyKey = crypto.randomUUID();

    return (
      <span className="flex flex-col gap-1">
        <form action={formAction}>
          <input type="hidden" name="targetState" value={transition.targetState} />
          <input type="hidden" name="sessionId" value={transition.sessionId} />
          <input type="hidden" name="idempotencyKey" value={idempotencyKey} />
          <input type="hidden" name="fencingToken" value={transition.fencingToken} />
          <Button type="submit" variant={variant} disabled={pending}>
            {pending ? "Đang gửi…" : label}
          </Button>
        </form>
        {result.message !== "" ? (
          <span
            aria-live="polite"
            className={`max-w-[26ch] text-[12px] ${result.ok ? "text-text-muted" : "text-risk-high-ink"}`}
          >
            {result.message}
          </span>
        ) : null}
      </span>
    );
  }

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