import { expect, test } from "@playwright/test";
import { createClient } from "@supabase/supabase-js";
import { FORBIDDEN_PATTERNS } from "./evidence-manifest";
import { loadLiveEnv } from "./live-env";

/**
 * Live Supabase smoke run.
 *
 * Proves the real session path end to end against the live project: a real
 * operator signs in, the product resolves their role from `profiles`, the
 * evidence control room renders for them, and every lifecycle mutation stays
 * disabled because a password-only session is AAL1, not AAL2. That AAL2 wall is
 * the security boundary, not a bug — the fixture run proves the enabled UI, the
 * RLS suite proves the database, and this run proves the live wiring in
 * between.
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

test("a real AAL1 operator sees the control room and is fenced off every mutation", async ({
  page,
}) => {
  await signInAsOperator(page);
  await page.goto("/ops/evidence");

  // Read path: the live session resolved and the control room rendered.
  await expect(page.getByRole("heading", { name: "Vận hành & Evidence" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Phiên evidence" })).toBeVisible();
  await expect(page.getByText("Smoke Operator").first()).toBeVisible();

  // AAL2 boundary: password-only sessions cannot mutate, and the product says
  // why instead of silently hiding the control.
  const provision = page.getByRole("button", { name: "Tạo phiên evidence" });
  await expect(provision).toBeDisabled();
  await expect(page.getByText(/yêu cầu xác thực hai lớp/).first()).toBeVisible();

  const destroy = page.getByRole("button", { name: "Hủy phiên" });
  await expect(destroy).toBeDisabled();
  await expect(page.getByText(/yêu cầu xác thực hai lớp/).nth(1)).toBeVisible();
});

test("a signed-out visitor is denied the control room, not shown one", async ({ page }) => {
  await page.goto("/ops/evidence");

  // The shell renders for everyone, but the content area must deny with a
  // reason — never the live controls, cost gauges or audit trail.
  await expect(page.getByText("Tài khoản hiện tại không có quyền vào trung tâm vận hành.")).toBeVisible();
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

test("registration is intentionally not exposed", async ({ page }) => {
  const response = await page.request.get("/sign-up");
  expect(response.status()).toBe(404);

  await page.goto("/sign-in");
  await expect(page.getByRole("link", { name: /đăng ký|sign up|register/i })).toHaveCount(0);
});
