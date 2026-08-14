import "server-only";
import { isRole, type Role } from "@distresslens/contracts";

/**
 * The switchable demo profiles shown in the account menu, read from a single
 * env var so no credential and no address is hardcoded in the repo.
 *
 * `DISTRESSLENS_DEMO_ACCOUNTS` is a JSON array of `{email, role, label}`.
 * Never a password: switching is a real sign-out followed by a real sign-in
 * (per the accepted decision), so the switcher only ever needs the email to
 * prefill and a label to display.
 *
 * Empty, unset, or malformed -> the switcher renders nothing, and normal
 * sign-in keeps working -- a misconfigured env var must never break auth.
 */

const ENV_VAR = "DISTRESSLENS_DEMO_ACCOUNTS";

export interface DemoAccount {
  email: string;
  role: Role;
  label: string;
}

function isDemoAccount(value: unknown): value is DemoAccount {
  if (value === null || typeof value !== "object") {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.email === "string" &&
    candidate.email.trim() !== "" &&
    isRole(candidate.role) &&
    typeof candidate.label === "string" &&
    candidate.label.trim() !== ""
  );
}

export function listDemoAccounts(): readonly DemoAccount[] {
  const raw = process.env[ENV_VAR];
  if (raw === undefined || raw.trim() === "") {
    return [];
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return [];
  }

  if (!Array.isArray(parsed)) {
    return [];
  }

  return parsed.filter(isDemoAccount);
}
