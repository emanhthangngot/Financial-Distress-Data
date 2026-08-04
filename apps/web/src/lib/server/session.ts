import "server-only";
import type { Role } from "@distresslens/contracts";
import type { RequestContext } from "../data/port";

/**
 * Resolves who is making the request and what the evidence plane can currently
 * do. Every route reads its context from here rather than from headers or
 * cookies directly, so the Supabase implementation replaces one function.
 *
 * Fixture mode exists because Docker networking is unavailable in this
 * environment, so the Playwright evidence run needs a deterministic identity.
 * It is gated on an explicit environment variable and refuses to run outside
 * development: an accidental production deploy must fail closed rather than
 * silently serve everyone a synthetic analyst session.
 */

export const FIXTURE_SESSION_ENV = "DISTRESSLENS_DATA_SOURCE";

export interface SessionUser {
  displayName: string;
  role: Role;
}

export interface ResolvedSession {
  context: RequestContext;
  user: SessionUser;
}

function isFixtureMode(): boolean {
  return process.env[FIXTURE_SESSION_ENV] === "fixture";
}

/**
 * Fixture identity, overridable per Playwright run so one suite can exercise
 * every role and both plane states without a live Supabase project.
 */
function fixtureSession(): ResolvedSession {
  const role = (process.env.DISTRESSLENS_FIXTURE_ROLE ?? "analyst") as Role;
  const planeReady = process.env.DISTRESSLENS_FIXTURE_PLANE !== "off";
  const signedOut = process.env.DISTRESSLENS_FIXTURE_ROLE === "signed_out";

  return {
    context: {
      userId: signedOut ? null : "fixture-analyst",
      role: signedOut ? null : role,
      aal: process.env.DISTRESSLENS_FIXTURE_AAL === "aal1" ? "aal1" : "aal2",
      planeReady,
    },
    user: {
      displayName: process.env.DISTRESSLENS_FIXTURE_NAME ?? "Nguyễn Minh Anh",
      role: signedOut ? "analyst" : role,
    },
  };
}

export async function resolveSession(): Promise<ResolvedSession> {
  if (isFixtureMode()) {
    if (process.env.NODE_ENV === "production" && process.env.VERCEL_ENV === "production") {
      throw new Error(
        "fixture session mode is not permitted in a production deployment; configure Supabase auth",
      );
    }
    return fixtureSession();
  }

  // The Supabase-backed implementation lands with the server boundary work; it
  // must read the signed session and role claim rather than trusting anything
  // the browser sends. Failing loudly here is deliberate: silently downgrading
  // to an anonymous or fixture identity would be an authentication bypass.
  throw new Error(
    `no session provider configured: set ${FIXTURE_SESSION_ENV}=fixture for local/evidence runs`,
  );
}
