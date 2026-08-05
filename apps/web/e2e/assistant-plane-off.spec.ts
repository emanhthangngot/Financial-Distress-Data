import { expect, test } from "@playwright/test";

async function openAssistant(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Mở trợ lý phân tích" }).click();
  await expect(page.getByRole("dialog", { name: /Trợ lý phân tích/ })).toBeVisible();
}

test("answers with the plane-off state instead of inventing an analysis", async ({ page }) => {
  await openAssistant(page);
  await page.getByRole("button", { name: "Tóm tắt rủi ro danh mục" }).click();

  await expect(page.getByText("Chưa kết nối dịch vụ")).toBeVisible();
  await expect(page.getByText(/phân tích AI trực tiếp tạm chưa bật/)).toBeVisible();
  await expect(page.getByText("Xem số liệu và nguồn dữ liệu ngay trên trang.")).toBeVisible();
});
