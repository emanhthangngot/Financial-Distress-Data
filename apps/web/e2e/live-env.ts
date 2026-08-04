import { readFileSync, existsSync } from "node:fs";
import path from "node:path";

/**
 * Load the live Supabase configuration for the smoke run.
 *
 * Playwright's own process does not load `.env.local`, and the smoke run must
 * never fall back to fixtures — proving the real Supabase session path is the
 * entire point. This parser mirrors the KEY=VALUE subset Next.js reads and is
 * deliberately tiny: full dotenv parsing belongs to the framework, not here.
 */

export interface LiveEnv {
  url: string;
  anonKey: string;
  serviceKey: string;
}

export function loadLiveEnv(): LiveEnv {
  const envPath = path.join(process.cwd(), ".env.local");
  if (!existsSync(envPath)) {
    throw new Error(
      `apps/web/.env.local is required for the live smoke run; configure Supabase before running e2e:live`,
    );
  }

  const values: Record<string, string> = {};
  for (const line of readFileSync(envPath, "utf8").split("\n")) {
    const match = /^([A-Z0-9_]+)=(.*)$/.exec(line.trim());
    if (match === null) {
      continue;
    }
    const [, key, raw] = match;
    values[key] = raw.trim().replace(/^"(.*)"$/, "$1");
  }

  const required: Record<keyof LiveEnv, string> = {
    url: "NEXT_PUBLIC_SUPABASE_URL",
    anonKey: "NEXT_PUBLIC_SUPABASE_ANON_KEY",
    serviceKey: "SUPABASE_SERVICE_ROLE_KEY",
  };
  const env = {} as LiveEnv;
  for (const [field, key] of Object.entries(required)) {
    const value = values[key];
    if (value === undefined || value === "") {
      throw new Error(`${key} is missing from apps/web/.env.local`);
    }
    env[field as keyof LiveEnv] = value;
  }
  return env;
}
