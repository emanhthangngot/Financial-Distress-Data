import { expect, test } from "@playwright/test";
import { captureEvidence, FORBIDDEN_PATTERNS } from "./evidence-manifest";

/**
 * Platform surfaces as an operator, with the evidence plane off.
 *
 * Two things are being proved together. First, that an operator sees what they
 * may do and is told why they may not do the rest — a hidden control makes a
 * missing permission look like a missing feature. Second, that with the plane
 * down the product stays useful and never lets a cached reading pass for a live
 * one.
 */

test.describe("evidence control room", () => {
  test("shows lifecycle, cost and GitOps state to an operator", async ({ page }, testInfo) => {
    await page.goto("/ops/evidence");

    await expect(page.getByRole("heading", { name: "Vận hành & Evidence" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Phiên evidence" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Chi phí và hạn mức" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Trạng thái GitOps" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Lịch sử audit" })).toBeVisible();

    await captureEvidence(page, testInfo, {
      route: "/ops/evidence",
      state: "degraded",
      role: "platform_operator",
      planeReady: false,
      expected: "lifecycle timeline, cost gauges, GitOps drift, pipelines, promotions, audit",
    });
  });

  test("enables what an operator may do and explains what they may not", async ({ page }) => {
    await page.goto("/ops/evidence");

    // Operator actions.
    await expect(page.getByRole("button", { name: "Tạo phiên evidence" })).toBeEnabled();
    await expect(page.getByRole("button", { name: "Hủy phiên" })).toBeEnabled();
    await expect(page.getByRole("button", { name: "Xuất evidence" })).toBeEnabled();

    // Admin-only actions, visible and disabled with a stated reason.
    const rollback = page.getByRole("button", { name: "Yêu cầu rollback" });
    await expect(rollback).toBeDisabled();
    await expect(page.getByText(/không được phép thực hiện session\.rollback/).first()).toBeVisible();

    const promote = page.getByRole("button", { name: "Promote" }).first();
    await expect(promote).toBeDisabled();
  });

  test("labels the offline plane rather than showing a healthy one", async ({ page }) => {
    await page.goto("/ops/evidence");
    await expect(page.getByText("Ngoại tuyến").first()).toBeVisible();
    await expect(page.getByText("Chưa có phiên evidence nào đang chạy")).toBeVisible();
    // Observability targets that cannot answer say so instead of linking.
    await expect(page.getByText("Xem Grafana (ngoại tuyến)")).toBeVisible();
  });

  test("shows the cost projection before provision, against the cap", async ({ page }) => {
    await page.goto("/ops/evidence");
    await expect(page.getByText(/Dự kiến thêm 12\.50 USD/)).toBeVisible();
    await expect(page.getByText(/còn lại/)).toBeVisible();
  });
});

test.describe("agent registry", () => {
  test("lists sandbox policy and marks replica counts unknown when the plane is off", async ({
    page,
  }, testInfo) => {
    await page.goto("/agents/registry");

    await expect(page.getByRole("heading", { name: "Sổ đăng ký agent" })).toBeVisible();
    await expect(page.getByText("Egress được phép").first()).toBeVisible();
    // Unknown is not zero: a plane that cannot be read must not look scaled down.
    await expect(page.getByText(/Không đọc được/).first()).toBeVisible();
    await expect(page.getByText("Không có — mặt phẳng ngoại tuyến").first()).toBeVisible();

    await captureEvidence(page, testInfo, {
      route: "/agents/registry",
      state: "degraded",
      role: "platform_operator",
      planeReady: false,
      expected: "agent versions, sandbox policy, unknown replica counts, denied promotion",
    });
  });

  test("denies an unauthorized mutation from the registry", async ({ page }) => {
    await page.goto("/agents/registry");
    await expect(page.getByRole("button", { name: "Promote lên production" }).first()).toBeDisabled();
  });
});

test("an operator cannot reach analyst content", async ({ page }, testInfo) => {
  // The separation is an authorization property, not a navigation one: typing
  // the URL must deny, and the denial must not name the protected rows.
  await page.goto("/companies/NVL");
  await expect(page.getByText(/không được cấp quyền xem doanh nghiệp này/)).toBeVisible();

  await captureEvidence(page, testInfo, {
    route: "/companies/[ticker]",
    state: "forbidden",
    role: "platform_operator",
    planeReady: false,
    expected: "denial that names the permission, not the company",
  });
});

test("no platform surface renders a secret", async ({ page }) => {
  for (const route of ["/ops/evidence", "/agents/registry"]) {
    await page.goto(route);
    const body = (await page.locator("body").innerText()).toString();
    for (const pattern of FORBIDDEN_PATTERNS) {
      expect(body, `${route} leaked ${pattern}`).not.toMatch(pattern);
    }
  }
});
