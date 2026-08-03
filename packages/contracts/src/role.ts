export const ROLES = [
  "analyst",
  "platform_viewer",
  "platform_operator",
  "platform_admin",
] as const;

export type Role = (typeof ROLES)[number];

export const PRIVILEGED_ROLES: readonly Role[] = [
  "platform_viewer",
  "platform_operator",
  "platform_admin",
];

/**
 * Runtime guard for values crossing a trust boundary. `Role` is erased at
 * runtime, but role values arrive from JWT claims and database rows, so a
 * renamed or unexpected role must be rejected here rather than flowing into an
 * authorization decision.
 */
export function isRole(value: unknown): value is Role {
  return typeof value === "string" && (ROLES as readonly string[]).includes(value);
}

export function isPrivilegedRole(role: Role): boolean {
  return PRIVILEGED_ROLES.includes(role);
}

export type SessionAction =
  | "session.read"
  | "session.provision"
  | "session.destroy"
  | "session.retry"
  | "session.export_evidence"
  | "session.promote"
  | "session.rollback"
  | "session.manage_roles"
  | "analyst.query"
  | "analyst.run_ai_request"
  | "analyst.save_report";

export const ROLE_ACTIONS: Record<Role, readonly SessionAction[]> = {
  analyst: ["analyst.query", "analyst.run_ai_request", "analyst.save_report"],
  platform_viewer: ["session.read"],
  platform_operator: [
    "session.read",
    "session.provision",
    "session.destroy",
    "session.retry",
    "session.export_evidence",
  ],
  platform_admin: [
    "session.read",
    "session.provision",
    "session.destroy",
    "session.retry",
    "session.export_evidence",
    "session.promote",
    "session.rollback",
    "session.manage_roles",
  ],
};

export function roleAllows(role: Role, action: SessionAction): boolean {
  const actions = ROLE_ACTIONS[role];
  return actions !== undefined && actions.includes(action);
}
