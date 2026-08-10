import { expect, test } from "@playwright/test";
import { captureEvidence, FORBIDDEN_PATTERNS } from "./evidence-manifest";

/**
 * The analyst surfaces, at every viewport the contract names.
 *
 * These are behavior assertions first and screenshots second: a frame that
 * looks right while the disclaimer is missing or a cached score is unlabelled
 * would still be filed as evidence, so each capture is preceded by the checks
 * that make the frame mean something.
 */

const DISCLAIMER = "Nội dung phục vụ mục đích học tập, không phải khuyến nghị đầu tư.";

test.describe("analyst overview", () => {
  test("renders the portfolio with its risk bands, attention table and alerts", async ({
    page,
  }, testInfo) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Tổng quan danh mục" })).toBeVisible();
    await expect(page.getByText("Nguy cơ cao").first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Doanh nghiệp cần chú ý" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Cảnh báo gần đây" })).toBeVisible();
    await expect(page.getByText(DISCLAIMER)).toBeVisible();

    await captureEvidence(page, testInfo, {
      route: "/",
      state: "success",
      role: "analyst",
      planeReady: true,
      expected: "risk band cards, sector chart, attention table, alert rail, disclaimer",
    });
  });

  test("never scrolls horizontally", async ({ page }) => {
    // A layout that only works by hiding overflow off the right edge has not
    // been made responsive, it has been made to look responsive in a frame.
    // The failure names the offending elements, because "72px too wide" without
    // a culprit is a bug report nobody can act on.
    await page.goto("/");
    const report = await page.evaluate(() => {
      const width = document.documentElement.clientWidth;
      const culprits = [...document.querySelectorAll<HTMLElement>("*")]
        .filter((element) => {
          const rect = element.getBoundingClientRect();
          return rect.width > 0 && rect.right > width + 1;
        })
        .slice(0, 5)
        .map((element) => `${element.tagName}.${String(element.className).slice(0, 60)}`);

      return {
        overflow: document.documentElement.scrollWidth - width,
        culprits,
      };
    });

    expect(report.overflow, `overflowing: ${report.culprits.join(" | ")}`).toBeLessThanOrEqual(1);
  });

  test("reaches the assistant by keyboard and returns focus when it closes", async ({ page }) => {
    await page.goto("/");
    const launcher = page.getByRole("button", { name: "Mở trợ lý phân tích" });

    await launcher.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("dialog", { name: /Trợ lý phân tích/ })).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: /Trợ lý phân tích/ })).toBeHidden();
    await expect(launcher).toBeFocused();
  });

  test("answers a quick action honestly when no inference endpoint is configured", async ({ page }, testInfo) => {
    // With no inference endpoint wired, the only honest answer is the plane-off
    // state: the assistant says live analysis is off and points at the data
    // that is still on the page. A fabricated risk explanation here would be
    // the worst thing this product could ship, so it is asserted against
    // rather than left to review.
    await page.goto("/");
    await page.getByRole("button", { name: "Mở trợ lý phân tích" }).click();
    await page.getByRole("button", { name: "Tóm tắt rủi ro danh mục" }).click();

    await expect(page.getByText("Chưa kết nối dịch vụ")).toBeVisible();
    await expect(page.getByText(/phân tích AI trực tiếp tạm chưa bật/)).toBeVisible();

    await captureEvidence(page, testInfo, {
      route: "/",
      state: "assistant-unavailable",
      role: "analyst",
      planeReady: true,
      expected: "assistant reports live analysis is off and offers the data that remains",
    });
  });
});

test.describe("company surfaces", () => {
  test("renders search results and a no-results state that explains itself", async ({
    page,
  }, testInfo) => {
    await page.goto("/companies");
    await expect(page.getByRole("heading", { name: "Doanh nghiệp", exact: true })).toBeVisible();

    await captureEvidence(page, testInfo, {
      route: "/companies",
      state: "success",
      role: "analyst",
      planeReady: true,
      expected: "full portfolio list with risk band, trend and data-through columns",
    });

    await page.goto("/companies?q=zzzznotacompany");
    await expect(page.getByText("Không có doanh nghiệp nào khớp từ khóa.")).toBeVisible();
    await expect(page.getByText(/Thử mã chứng khoán/)).toBeVisible();

    await captureEvidence(page, testInfo, {
      route: "/companies",
      state: "empty",
      role: "analyst",
      planeReady: true,
      expected: "no-results state naming the safe next action",
    });
  });

  test("renders the company detail with explanation, sources and provenance", async ({
    page,
  }, testInfo) => {
    await page.goto("/companies/NVL");

    await expect(page.getByRole("heading", { name: /NVL/ })).toBeVisible();
    await expect(page.getByText("Xác suất distress").first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Yếu tố tác động đến điểm rủi ro" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Nguồn dữ liệu" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Xuất xứ kết quả" })).toBeVisible();
    // Company and explanation are both disclaimer surfaces.
    expect(await page.getByText(DISCLAIMER).count()).toBeGreaterThanOrEqual(2);

    await captureEvidence(page, testInfo, {
      route: "/companies/[ticker]",
      state: "success",
      role: "analyst",
      planeReady: true,
      expected: "KPI strip, trend chart, indicators, SHAP drivers, sources, provenance, disclaimer",
    });
  });

  test("explains an unknown ticker instead of showing a blank page", async ({ page }, testInfo) => {
    await page.goto("/companies/ZZZ");
    await expect(page.getByText("Chưa có kết quả chấm điểm cho doanh nghiệp này.")).toBeVisible();

    await captureEvidence(page, testInfo, {
      route: "/companies/[ticker]",
      state: "empty",
      role: "analyst",
      planeReady: true,
      expected: "empty state with a route back to the company list",
    });
  });
});

test.describe("comparison and reports", () => {
  test("shows both model versions and the delta between them", async ({ page }, testInfo) => {
    await page.goto("/compare?ticker=NVL");

    // Headings, not text: the labels are uppercased by CSS, so the DOM still
    // reads "Phiên bản nền" and a literal uppercase match would never hit.
    await expect(page.getByRole("heading", { name: "Phiên bản nền" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Phiên bản ứng viên" })).toBeVisible();
    await expect(page.getByText("Chênh lệch")).toBeVisible();
    await expect(page.getByText(DISCLAIMER)).toBeVisible();

    await captureEvidence(page, testInfo, {
      route: "/compare",
      state: "success",
      role: "analyst",
      planeReady: true,
      expected: "two-version split with computed delta and disclaimer",
    });
  });

  test("opens a saved report with its provenance and export control", async ({
    page,
  }, testInfo) => {
    await page.goto("/reports");
    await expect(page.getByRole("heading", { name: "Báo cáo", exact: true })).toBeVisible();
    await page.getByRole("link", { name: /Đánh giá rủi ro NVL/ }).click();

    await expect(page.getByRole("button", { name: "Xuất báo cáo (PDF)" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Xuất xứ kết quả" })).toBeVisible();
    await expect(page.getByText(DISCLAIMER).first()).toBeVisible();

    await captureEvidence(page, testInfo, {
      route: "/reports/[id]",
      state: "success",
      role: "analyst",
      planeReady: true,
      expected: "persisted report with provenance, export control and disclaimer",
    });
  });

  test("denies a report the caller does not own without confirming it exists", async ({ page }) => {
    await page.goto("/reports/rpt-someone-else");
    await expect(page.getByText(/đã bị thu hồi hoặc không thuộc tài khoản này/)).toBeVisible();
  });
});

test("no analyst surface renders a secret", async ({ page }) => {
  for (const route of ["/", "/companies", "/companies/NVL", "/compare", "/reports"]) {
    await page.goto(route);
    const body = (await page.locator("body").innerText()).toString();
    for (const pattern of FORBIDDEN_PATTERNS) {
      expect(body, `${route} leaked ${pattern}`).not.toMatch(pattern);
    }
  }
});
