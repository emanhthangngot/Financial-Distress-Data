import { isPrivilegedRole, roleAllows, type Role, type SessionAction } from "./role";

/**
 * The single authorization decision the server boundary calls before any
 * mutation. It is a pure function so the same rule is testable in isolation and
 * cannot drift from what the route handler actually enforces.
 *
 * This is the Next.js half of a two-layer control: Supabase RLS enforces the
 * same rules at the database. Neither layer trusts the client.
 */

export const AUTHORIZATION_DENIALS = [
  "UNAUTHENTICATED",
  "ROLE_NOT_PERMITTED",
  "AAL2_REQUIRED",
  "QUOTA_EXHAUSTED",
  "RATE_LIMITED",
] as const;

export type AuthorizationDenial = (typeof AUTHORIZATION_DENIALS)[number];

export interface AuthorizationContext {
  role: Role | null;
  /** Supabase assurance level of the current session. */
  aal: "aal1" | "aal2";
}

export type AuthorizationDecision =
  | { allowed: true }
  | { allowed: false; denial: AuthorizationDenial; reason: string };

/**
 * Privileged roles must clear AAL2 before mutating anything. Reads stay at AAL1
 * so a viewer can still inspect the control room with a single factor.
 */
const AAL2_EXEMPT_ACTIONS: readonly SessionAction[] = ["session.read", "analyst.query"];

export function authorize(
  context: AuthorizationContext,
  action: SessionAction,
): AuthorizationDecision {
  if (context.role === null) {
    return {
      allowed: false,
      denial: "UNAUTHENTICATED",
      reason: "Phiên đăng nhập không hợp lệ. Đăng nhập lại để tiếp tục.",
    };
  }

  if (!roleAllows(context.role, action)) {
    return {
      allowed: false,
      denial: "ROLE_NOT_PERMITTED",
      // Names the action, never the protected row: a denial must not leak what
      // exists behind it.
      reason: `Vai trò hiện tại không được phép thực hiện ${action}.`,
    };
  }

  if (
    isPrivilegedRole(context.role) &&
    !AAL2_EXEMPT_ACTIONS.includes(action) &&
    context.aal !== "aal2"
  ) {
    return {
      allowed: false,
      denial: "AAL2_REQUIRED",
      reason: "Thao tác này yêu cầu xác thực hai lớp (AAL2). Bật MFA rồi thử lại.",
    };
  }

  return { allowed: true };
}
