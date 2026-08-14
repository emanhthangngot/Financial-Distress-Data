import { expect, test } from "@playwright/test";
import { createClient } from "@supabase/supabase-js";
import { FORBIDDEN_PATTERNS } from "./evidence-manifest";
import { loadLiveEnv } from "./live-env";

/**
 * Live Supabase smoke run.
 *
 * Proves the real session path end to end against the live project: a real
 * operator signs in, the product resolves their role from `profiles`, and the
 * evidence control room renders for them. Lifecycle mutations are enabled at a
 * password-only (AAL1) session -- this deployment relaxes the AAL2 step-up
 * requirement (`STEP_UP_REQUIRED` in `@distresslens/contracts`, mirrored by
 * `meets_step_up()` in `supabase/migrations/20260814200100_phase2_step_up_relaxation.sql`)
 * because it has no MFA enrollment path. `auth-lifecycle.spec.ts` covers the
 * signup/signin/refresh/switch/signout loop this plan added; this file stays
 * focused on the pre-existing operator-role read/write proof.
 *
 * Opt-in only: `pnpm e2e:live`. It provisions one disposable operator on the
 * configured project and must never run in CI or against a production project
 * without review.
 */

const OPERATOR_EMAIL = "smoke.operator@example.com";
const OPERATOR_PASSWORD = "SmokeTest-Operator-2026!";

function operatorClient(env: ReturnType<typeof loadLiveEnv>) {
  return createClient(env.url, env.anonKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

/** Stamp the session cookie onto the page, keyed to whatever origin it is on. */
async function signInAsOperator(page: import("@playwright/test").Page) {
  const env = loadLiveEnv();
  const { data, error } = await operatorClient(env).auth.signInWithPassword({
    email: OPERATOR_EMAIL,
    password: OPERATOR_PASSWORD,
  });
  expect(error, "live sign-in").toBeNull();
  const token = data.session?.access_token;
  expect(token, "access token").toBeDefined();

  // The product reads the token from this cookie (apps/web/src/lib/server/session.ts).
  // Visit once first so the origin of the running server is known, then stamp
  // the cookie keyed to that origin and reload.
  await page.goto("/");
  const origin = new URL(page.url()).origin;
  await page.context().addCookies([{ name: "sb-access-token", value: token!, url: origin }]);
  return token;
}

async function signInThroughForm(page: import("@playwright/test").Page) {
  await page.goto("/sign-in");
  await expect(page.getByRole("heading", { name: "Đăng nhập DistressLens" })).toBeVisible();
  await page.getByLabel("Email").fill(OPERATOR_EMAIL);
  await page.getByLabel("Mật khẩu").fill(OPERATOR_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page).toHaveURL(/\/$/);
}

test.describe.configure({ mode: "serial" });

test.beforeAll(async () => {
  const env = loadLiveEnv();
  const admin = createClient(env.url, env.serviceKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  const { data: existing } = await admin.auth.admin.listUsers({ page: 1, perPage: 100 });
  let operatorId = existing?.users.find((user) => user.email === OPERATOR_EMAIL)?.id;

  if (operatorId === undefined) {
    const { data: created, error: createError } = await admin.auth.admin.createUser({
      email: OPERATOR_EMAIL,
      password: OPERATOR_PASSWORD,
      email_confirm: true,
      user_metadata: { full_name: "Smoke Operator" },
    });
    expect(createError, "operator user creation").toBeNull();
    operatorId = created?.user?.id;
  } else {
    // Keep the display identity deterministic across re-runs, even when the
    // user already exists without the full-name metadata.
    const { error: metadataError } = await admin.auth.admin.updateUserById(operatorId, {
      user_metadata: { full_name: "Smoke Operator" },
    });
    expect(metadataError, "operator display-name refresh").toBeNull();
  }
  expect(operatorId, "operator user id").toBeDefined();

  // The role lives in profiles, and only the profiles row decides what the
  // product lets this user do.
  const { error: roleError } = await admin
    .from("profiles")
    .upsert({ user_id: operatorId!, role: "platform_operator" });
  expect(roleError, "operator role assignment").toBeNull();
});

test("a real AAL1 operator sees the control room and can mutate under the step-up relaxation", async ({
  page,
}) => {
  await signInAsOperator(page);
  await page.goto("/ops/evidence");

  // Read path: the live session resolved and the control room rendered.
  await expect(page.getByRole("heading", { name: "Vận hành & Evidence" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Phiên evidence" })).toBeVisible();
  await expect(page.getByText("Smoke Operator").first()).toBeVisible();

  // STEP_UP_REQUIRED = false: a password-only (AAL1) operator session is
  // enough to mutate the evidence lifecycle in this deployment -- the control
  // is not gated behind a step-up this environment cannot satisfy.
  //
  // "Tạo phiên evidence" is not the right control to prove this with:
  // `getOpsDashboard` stays fixture-delegated (see the class doc in
  // supabase-adapter.ts) and the fixture session is always READY, so
  // provision is legitimately blocked by the state graph (READY -> REQUESTED
  // is not a legal transition) regardless of AAL. "Hủy phiên" (READY ->
  // DESTROYING) is legal from that same fixture state, so it isolates the
  // AAL question.
  const destroy = page.getByRole("button", { name: "Hủy phiên" });
  await expect(destroy).toBeEnabled();
});

test("a signed-out visitor is denied the control room with a sign-in call to action, not shown one", async ({
  page,
}) => {
  await page.goto("/ops/evidence");

  // A guest is not forbidden, they are anonymous (RC1/RC2): the content area
  // invites sign-in rather than reporting a role denial, and never renders
  // the live controls, cost gauges or audit trail either way.
  await expect(page.getByText("Đăng nhập để vào trung tâm vận hành.")).toBeVisible();
  // Two "Đăng nhập" links render for a guest here -- the header control and
  // this denial panel's call to action -- so scope to the content area.
  await expect(
    page.locator("#main-content").getByRole("link", { name: "Đăng nhập" }),
  ).toHaveAttribute("href", "/sign-in");
  await expect(page.getByRole("heading", { name: "Phiên evidence" })).not.toBeVisible();
  await expect(page.getByRole("heading", { name: "Lịch sử audit" })).not.toBeVisible();
});

test("no live surface leaks a secret", async ({ page }) => {
  await signInAsOperator(page);
  await page.goto("/ops/evidence");
  const body = (await page.locator("body").innerText()).toString();
  for (const pattern of FORBIDDEN_PATTERNS) {
    expect(body, `leaked ${pattern}`).not.toMatch(pattern);
  }
});

test("the sign-in form rejects invalid credentials without leaving the page", async ({ page }) => {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill(OPERATOR_EMAIL);
  await page.getByLabel("Mật khẩu").fill("definitely-not-the-password");
  await page.getByRole("button", { name: "Đăng nhập" }).click();

  await expect(page).toHaveURL(/\/sign-in$/);
  await expect(page.locator("form").getByRole("alert")).toHaveText("Invalid login credentials");
});

test("the supported login and logout flow clears the session", async ({ page }) => {
  await signInThroughForm(page);

  await page.locator("details").filter({ has: page.getByText("Smoke Operator") }).locator("summary").click();
  await page.locator("details").getByRole("link", { name: "Đăng xuất" }).click();

  await expect(page).toHaveURL(/\/sign-in$/);
  await expect(page.getByRole("heading", { name: "Đăng nhập DistressLens" })).toBeVisible();
  expect((await page.context().cookies()).some((cookie) => cookie.name === "sb-access-token")).toBe(false);
});

test("registration is open and reachable from sign-in (supersedes the one-demo-account contract)", async ({
  page,
}) => {
  const response = await page.request.get("/sign-up");
  expect(response.status()).toBe(200);

  await page.goto("/sign-in");
  await expect(page.getByRole("link", { name: "Đăng ký" })).toHaveAttribute("href", "/sign-up");
});
