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

/** Demo-account credentials read from `.env.local`, never hardcoded in a spec file. */
export interface DemoAccountEnv {
  analystEmail: string;
  analystPassword: string;
  operatorEmail: string;
  operatorPassword: string;
}

function readEnvLocal(): Record<string, string> {
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
  return values;
}

function requireKey(values: Record<string, string>, key: string): string {
  const value = values[key];
  if (value === undefined || value === "") {
    throw new Error(`${key} is missing from apps/web/.env.local`);
  }
  return value;
}

export function loadLiveEnv(): LiveEnv {
  const values = readEnvLocal();
  return {
    url: requireKey(values, "NEXT_PUBLIC_SUPABASE_URL"),
    anonKey: requireKey(values, "NEXT_PUBLIC_SUPABASE_ANON_KEY"),
    serviceKey: requireKey(values, "SUPABASE_SERVICE_ROLE_KEY"),
  };
}

/**
 * The two seeded demo accounts used by `auth-lifecycle.spec.ts` (profile
 * switch and platform_operator reach). Never hardcoded in the spec: these
 * are real, working credentials on the live project, so they live only in
 * the untracked `.env.local`, the same file `seed-demo-accounts.ts` reads
 * its passwords from.
 */
export function loadDemoAccountEnv(): DemoAccountEnv {
  const values = readEnvLocal();
  return {
    analystEmail: requireKey(values, "DEMO_ANALYST_EMAIL"),
    analystPassword: requireKey(values, "DEMO_ANALYST_PASSWORD"),
    operatorEmail: requireKey(values, "DEMO_OPERATOR_EMAIL"),
    operatorPassword: requireKey(values, "DEMO_OPERATOR_PASSWORD"),
  };
}
