import "server-only";
import { cookies } from "next/headers";
import { isRole, type Role } from "@distresslens/contracts";
import type { RequestContext } from "../data/port";
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
  role: Role;
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
      displayName: process.env.DISTRESSLENS_FIXTURE_NAME ?? "Nguyễn Minh Anh",
      role: signedOut ? "analyst" : role,
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

  const accessToken = (await cookies()).get("sb-access-token")?.value ?? null;
  const client = createRequestClient(accessToken);
  const { data, error } = await client.auth.getUser();
  const authUser = error === null ? data.user : null;

  if (authUser === null) {
    // Signed out is a legitimate state, not an error: `/` renders a landing
    // page for it, and every other route renders its own forbidden copy.
    return {
      context: { userId: null, role: null, aal: "aal1", planeReady: await readPlaneReady() },
      user: { displayName: "Khách", role: "analyst" },
      accessToken: null,
    };
  }

  const profile = await client
    .from("profiles")
    .select("role")
    .eq("user_id", authUser.id)
    .maybeSingle();

  // A signed-in user with no profile row has no role, and no role means no
  // access — not a default of `analyst`.
  const role = isRole(profile.data?.role) ? profile.data.role : null;
  const aal = readAssuranceLevel(authUser);

  return {
    context: { userId: authUser.id, role, aal, planeReady: await readPlaneReady() },
    user: {
      displayName: displayNameOf(authUser),
      role: role ?? "analyst",
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
  aal?: string | null;
}

function readAssuranceLevel(user: AuthUserLike): "aal1" | "aal2" {
  // Supabase reports the achieved assurance level on the session; anything we
  // cannot positively read as aal2 is treated as aal1, so an unknown value
  // fails closed and blocks privileged writes.
  return user.aal === "aal2" ? "aal2" : "aal1";
}

function displayNameOf(user: AuthUserLike): string {
  const metadataName = user.user_metadata?.full_name;
  if (typeof metadataName === "string" && metadataName.trim() !== "") {
    return metadataName;
  }
  // The local part only: a full address in the header is more PII on screen
  // than the header needs.
  return user.email?.split("@")[0] ?? "Người dùng";
}
