import { expect, test } from "@playwright/test";
import { createClient } from "@supabase/supabase-js";
import { loadDemoAccountEnv, loadLiveEnv } from "./live-env";

/**
 * Live auth lifecycle: signup, admin-confirmed signin, refresh-token
 * survival, demo-profile switch, platform_operator AAL1 reach, and signout.
 *
 * `GET /auth/v1/settings` on the configured project reports
 * `mailer_autoconfirm: false` -- confirmation is required, unlike the local
 * `supabase/config.toml`. The hosted SMTP is rate-limited to a handful of
 * mails an hour, so this suite never sends or waits on a real confirmation
 * email: it uses one fixed disposable address, provisions/confirms it
 * through the service-role admin API (exactly like `seed-demo-accounts.ts`
 * does), and tears it down in `afterAll`.
 *
 * The demo-account credentials (cases 4-6) are read from `.env.local` via
 * `loadDemoAccountEnv()`, never hardcoded here -- they are real, working
 * passwords on the live project.
 *
 * Opt-in only: `pnpm e2e:live`. Never run in CI or against a production
 * project without review.
 */

const TEST_EMAIL = "distresslens.auth-lifecycle@example.com";
const TEST_PASSWORD = "AuthLifecycle-2026!";

const demo = loadDemoAccountEnv();

function adminClient(env: ReturnType<typeof loadLiveEnv>) {
  return createClient(env.url, env.serviceKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

async function deleteTestUserIfPresent(): Promise<void> {
  const env = loadLiveEnv();
  const admin = adminClient(env);
  const { data } = await admin.auth.admin.listUsers({ page: 1, perPage: 200 });
  const existing = data?.users.find((user) => user.email === TEST_EMAIL);
  if (existing !== undefined) {
    await admin.auth.admin.deleteUser(existing.id);
  }
}

test.describe.configure({ mode: "serial" });

test.beforeAll(deleteTestUserIfPresent);
test.afterAll(deleteTestUserIfPresent);

test("1. sign-up with a disposable address shows the email-confirmation state, not a session", async ({
  page,
}) => {
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(TEST_EMAIL);
  await page.getByLabel("Mật khẩu", { exact: true }).fill(TEST_PASSWORD);
  await page.getByLabel("Xác nhận mật khẩu").fill(TEST_PASSWORD);
  await page.getByRole("button", { name: "Đăng ký" }).click();

  // No redirect to "/" -- the account exists but is not confirmed yet.
  await expect(page.getByRole("status")).toContainText("Kiểm tra hộp thư");
  await expect(page).toHaveURL(/\/sign-up$/);
});

test("2. admin-confirming the account lets it sign in as analyst", async ({ page }) => {
  const env = loadLiveEnv();
  const admin = adminClient(env);
  const { data } = await admin.auth.admin.listUsers({ page: 1, perPage: 200 });
  const user = data?.users.find((candidate) => candidate.email === TEST_EMAIL);
  expect(user, "signup from test 1 created the account").toBeDefined();

  const { error: confirmError } = await admin.auth.admin.updateUserById(user!.id, {
    email_confirm: true,
  });
  expect(confirmError, "admin confirmation").toBeNull();

  await page.goto("/sign-in");
  await page.getByLabel("Email").fill(TEST_EMAIL);
  await page.getByLabel("Mật khẩu").fill(TEST_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page).toHaveURL(/\/$/);

  const { data: profile } = await admin
    .from("profiles")
    .select("role")
    .eq("user_id", user!.id)
    .maybeSingle();
  expect(profile?.role).toBe("analyst");
});

test("3. token-expiry survival: middleware rotates the session when only the refresh cookie remains", async ({
  page,
  context,
}) => {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill(TEST_EMAIL);
  await page.getByLabel("Mật khẩu").fill(TEST_PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page).toHaveURL(/\/$/);

  const beforeCookies = await context.cookies();
  expect(beforeCookies.some((cookie) => cookie.name === "sb-refresh-token")).toBe(true);

  // Simulate access-token expiry without waiting out a real 3600s window:
  // drop only the access cookie, keep the refresh cookie, and reload.
  await context.clearCookies({ name: "sb-access-token" });
  await page.reload();

  // The middleware must have rotated a fresh pair before the page rendered --
  // still no guest sign-in link, and a fresh access-token cookie is present.
  await expect(page.getByRole("link", { name: "Đăng nhập" })).toHaveCount(0);
  const afterCookies = await context.cookies();
  expect(afterCookies.some((cookie) => cookie.name === "sb-access-token")).toBe(true);
});

test("4. demo profile switch: picking a profile signs out and prefills the chosen email", async ({
  page,
}) => {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill(demo.analystEmail);
  await page.getByLabel("Mật khẩu").fill(demo.analystPassword);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page).toHaveURL(/\/$/);

  // <summary> is the disclosure trigger; its implicit ARIA role is not
  // reliably "button" across engines, so this targets it by content instead.
  await page.locator("summary").filter({ hasText: "Mở menu tài khoản" }).click();
  await page.getByRole("link", { name: /Nền tảng — vận hành/ }).click();

  const expectedNext = `/sign-in?email=${encodeURIComponent(demo.operatorEmail)}`;
  await expect(page).toHaveURL(new RegExp(expectedNext.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  await expect(page.getByLabel("Email")).toHaveValue(demo.operatorEmail);
});

test("5. platform_operator reaches /ops/evidence and can mutate at AAL1 (step-up relaxation)", async ({
  page,
}) => {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill(demo.operatorEmail);
  await page.getByLabel("Mật khẩu").fill(demo.operatorPassword);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page).toHaveURL(/\/$/);

  await page.goto("/ops/evidence");
  await expect(page.getByRole("heading", { name: "Vận hành & Evidence" })).toBeVisible();

  // "Tạo phiên evidence" is blocked by the (fixture-delegated, always-READY)
  // session state graph regardless of AAL -- see live-smoke.spec.ts for why.
  // "Hủy phiên" (READY -> DESTROYING) isolates the AAL question.
  const destroy = page.getByRole("button", { name: "Hủy phiên" });
  await expect(destroy).toBeEnabled();
});

test("6. sign-out clears both session cookies", async ({ page, context }) => {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill(demo.analystEmail);
  await page.getByLabel("Mật khẩu").fill(demo.analystPassword);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page).toHaveURL(/\/$/);

  await page.goto("/sign-out");
  await expect(page).toHaveURL(/\/sign-in$/);

  const cookies = await context.cookies();
  expect(cookies.some((cookie) => cookie.name === "sb-access-token")).toBe(false);
  expect(cookies.some((cookie) => cookie.name === "sb-refresh-token")).toBe(false);
});
