import "server-only";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * Supabase clients.
 *
 * Two kinds, deliberately separated:
 *
 * - `createRequestClient` carries the caller's access token, so every query runs
 *   as that user and RLS applies. This is what routes read through.
 * - `createServiceClient` uses the service-role key and bypasses RLS. Only the
 *   outbox worker may use it, because it acts on behalf of no user. It refuses
 *   to construct in the browser, and the key is never referenced from client
 *   code — an accidental import would fail the build rather than ship a
 *   database master key to a browser.
 */

const URL_ENV = "NEXT_PUBLIC_SUPABASE_URL";
const ANON_ENV = "NEXT_PUBLIC_SUPABASE_ANON_KEY";
const SERVICE_ENV = "SUPABASE_SERVICE_ROLE_KEY";

export function isSupabaseConfigured(): boolean {
  return required(URL_ENV) !== null && required(ANON_ENV) !== null;
}

/**
 * A client scoped to one caller. Without a token it is an anonymous client, and
 * RLS will deny anything that requires a signed session — which is the correct
 * behavior, not a bug to work around.
 */
export function createRequestClient(accessToken: string | null): SupabaseClient {
  const url = requireEnv(URL_ENV);
  const anonKey = requireEnv(ANON_ENV);

  return createClient(url, anonKey, {
    auth: { persistSession: false, autoRefreshToken: false },
    global:
      accessToken === null
        ? undefined
        : { headers: { Authorization: `Bearer ${accessToken}` } },
  });
}

/**
 * The worker's client. Never call this from a request handler: it has no user
 * and therefore no RLS, so anything it reads it reads in full.
 */
export function createServiceClient(): SupabaseClient {
  if (typeof window !== "undefined") {
    throw new Error("the service-role client must never be constructed in a browser");
  }

  return createClient(requireEnv(URL_ENV), requireEnv(SERVICE_ENV), {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

function required(name: string): string | null {
  const value = process.env[name];
  return value === undefined || value.trim() === "" ? null : value;
}

function requireEnv(name: string): string {
  const value = required(name);
  if (value === null) {
    // Failing loudly beats falling back to fixtures: a misconfigured deployment
    // that silently serves synthetic data is worse than one that will not start.
    throw new Error(`${name} is not set; configure Supabase before using this client`);
  }
  return value;
}
