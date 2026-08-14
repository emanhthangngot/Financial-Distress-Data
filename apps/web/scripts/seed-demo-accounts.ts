/**
 * Seed one working demo account per role.
 *
 * Passwords cannot be set from SQL, so this runs against the service-role
 * client with `auth.admin.createUser` (or updates the password of an existing
 * user with the same email). It reads every password from an env var and
 * prints none -- only the email + role + created/updated is logged.
 *
 * Manual, operator-run script. Never imported by app code (it would ship the
 * service-role key path into the app bundle).
 *
 * Usage: pnpm --filter @distresslens/web seed:demo-accounts
 * Required env: NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY,
 *   DEMO_ANALYST_EMAIL, DEMO_ANALYST_PASSWORD,
 *   DEMO_PLATFORM_VIEWER_EMAIL, DEMO_PLATFORM_VIEWER_PASSWORD,
 *   DEMO_PLATFORM_OPERATOR_EMAIL, DEMO_PLATFORM_OPERATOR_PASSWORD,
 *   DEMO_PLATFORM_ADMIN_EMAIL, DEMO_PLATFORM_ADMIN_PASSWORD
 */
import { createServiceClient } from "@/lib/server/supabase";

type AppRole = "analyst" | "platform_viewer" | "platform_operator" | "platform_admin";

const ROLES: readonly AppRole[] = ["analyst", "platform_viewer", "platform_operator", "platform_admin"];

const REQUIRED_ENV = ["NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"] as const;

function envKey(role: AppRole, suffix: "EMAIL" | "PASSWORD"): string {
  return `DEMO_${role.toUpperCase()}_${suffix}`;
}

function assertEnv(): void {
  const missing = [...REQUIRED_ENV, ...ROLES.flatMap((role) => [envKey(role, "EMAIL"), envKey(role, "PASSWORD")])].filter(
    (name) => (process.env[name] ?? "").trim() === "",
  );
  if (missing.length > 0) {
    console.error(`seed-demo-accounts: missing required env var(s): ${missing.join(", ")}`);
    process.exit(1);
  }
}

async function main(): Promise<void> {
  assertEnv();

  const client = createServiceClient();

  for (const role of ROLES) {
    const email = process.env[envKey(role, "EMAIL")]!;
    const password = process.env[envKey(role, "PASSWORD")]!;

    const { data: existing } = await client.auth.admin.listUsers();
    const found = existing.users.find((u) => u.email?.toLowerCase() === email.toLowerCase());

    if (found === undefined) {
      const { error } = await client.auth.admin.createUser({
        email,
        password,
        email_confirm: true,
      });
      if (error !== null) {
        console.error(`seed-demo-accounts: create failed for ${email}: ${error.message}`);
        process.exitCode = 1;
        continue;
      }
      console.log(`created: ${email} (${role})`);
    } else {
      const { error } = await client.auth.admin.updateUserById(found.id, { password, email_confirm: true });
      if (error !== null) {
        console.error(`seed-demo-accounts: password update failed for ${email}: ${error.message}`);
        process.exitCode = 1;
        continue;
      }
      console.log(`updated: ${email} (${role})`);
    }

    const { error: roleError } = await client
      .from("profiles")
      .update({ role })
      .eq("email", email);
    if (roleError !== null) {
      console.error(`seed-demo-accounts: role upsert failed for ${email}: ${roleError.message}`);
      process.exitCode = 1;
    }
  }
}

main().catch((cause) => {
  console.error("seed-demo-accounts: unexpected failure", cause);
  process.exit(1);
});
