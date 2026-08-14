import "server-only";
import { cookies } from "next/headers";
import { isRole, type Role } from "@distresslens/contracts";
import type { RequestContext } from "../data/port";
import { ACCESS_TOKEN_COOKIE } from "./auth-cookies";
import { readAssuranceLevel } from "./jwt-claims";
import { createRequestClient, isSupabaseConfigured } from "./supabase";

/**
 * Resolves who is making the request and what the evidence plane can currently
 * do. Every route reads its context from here rather than from headers or
 * cookies directly, so the identity decision exists in exactly one place.
 *
 * The role comes from the `profiles` table keyed by the verified user id, never
 * from a client-supplied claim: a JWT the browser can edit is not an
 * authorization source. Supabase verifies the token; this function verifies
 * what that user is allowed to be.
 *
 * Fixture mode exists because the evidence run needs a deterministic identity
 * without a live Supabase project. It is gated on an explicit environment
 * variable and refuses to run in a production deployment: an accidental deploy
 * must fail closed rather than silently serve everyone a synthetic session.
 */

export const FIXTURE_SESSION_ENV = "DISTRESSLENS_DATA_SOURCE";

export interface SessionUser {
  displayName: string;
  /** Null for a guest -- never defaulted to "analyst". See RC2 in the auth plan. */
  role: Role | null;
}

export interface ResolvedSession {
  context: RequestContext;
  user: SessionUser;
  /** Supabase access token for this request, null in fixture mode. */
  accessToken: string | null;
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
      displayName: signedOut ? "Khách" : (process.env.DISTRESSLENS_FIXTURE_NAME ?? "Nguyễn Minh Anh"),
      role: signedOut ? null : role,
    },
    accessToken: null,
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

  if (!isSupabaseConfigured()) {
    // Failing loudly is deliberate: silently downgrading to an anonymous or
    // fixture identity would be an authentication bypass.
    throw new Error(
      `no session provider configured: set Supabase env vars, or ${FIXTURE_SESSION_ENV}=fixture for local/evidence runs`,
    );
  }

  const accessToken = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value ?? null;
  const client = createRequestClient(accessToken);
  const { data, error } = await client.auth.getUser();
  const authUser = error === null ? data.user : null;

  if (authUser === null) {
    // Signed out is a legitimate state, not an error: `/` renders a landing
    // page for it, and every other route renders its own forbidden copy.
    // Guest is a guest everywhere -- no analyst role fallback (RC2).
    return {
      context: { userId: null, role: null, aal: "aal1", planeReady: await readPlaneReady() },
      user: { displayName: "Khách", role: null },
      accessToken: null,
    };
  }

  const profile = await client
    .from("profiles")
    .select("role, display_name")
    .eq("user_id", authUser.id)
    .maybeSingle();

  // A signed-in user with no profile row has no role, and no role means no
  // access — not a default of `analyst`.
  const role = isRole(profile.data?.role) ? profile.data.role : null;
  const aal = readAssuranceLevel(accessToken);

  return {
    context: { userId: authUser.id, role, aal, planeReady: await readPlaneReady() },
    user: {
      displayName: displayNameOf(authUser, profile.data?.display_name),
      role,
    },
    accessToken,
  };
}

/**
 * Whether the EKS inference plane can serve live requests. Read from the
 * environment for now; the plane-status probe replaces this without changing
 * any caller.
 */
async function readPlaneReady(): Promise<boolean> {
  return process.env.DISTRESSLENS_PLANE_READY !== "off";
}

interface AuthUserLike {
  id: string;
  email?: string | null;
  user_metadata?: Record<string, unknown> | null;
}

/**
 * The self-service rename in `updateDisplayName` (profile-actions.ts) writes
 * `profiles.display_name`, so that column -- not the signup-time metadata
 * snapshot -- is the header's source of truth once it is set. Falls back to
 * the `full_name` signup metadata, then the email local part.
 */
function displayNameOf(user: AuthUserLike, profileDisplayName?: string | null): string {
  if (typeof profileDisplayName === "string" && profileDisplayName.trim() !== "") {
    return profileDisplayName;
  }
  const metadataName = user.user_metadata?.full_name;
  if (typeof metadataName === "string" && metadataName.trim() !== "") {
    return metadataName;
  }
  // The local part only: a full address in the header is more PII on screen
  // than the header needs.
  return user.email?.split("@")[0] ?? "Người dùng";
}
