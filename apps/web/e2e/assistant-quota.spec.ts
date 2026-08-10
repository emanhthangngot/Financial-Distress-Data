import { expect, test } from "@playwright/test";

async function openAssistant(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Mở trợ lý phân tích" }).click();
  await expect(page.getByRole("dialog", { name: /Trợ lý phân tích/ })).toBeVisible();
}

test("refuses a question when the AI quota is exhausted, with the reset copy", async ({ page }) => {
  await openAssistant(page);
  await page.getByLabel("Câu hỏi cho trợ lý phân tích").fill("Vì sao NVL có nguy cơ cao?");
  await page.getByRole("button", { name: "Gửi câu hỏi" }).click();

  await expect(page.getByText("Bị chính sách chặn")).toBeVisible();
  await expect(page.getByText(/Hạn mức được đặt lại/)).toBeVisible();
  // No stream ever opens: the analyst sees a refusal, never a fabricated answer.
  await expect(page.getByText("Đang trả lời")).toBeHidden();
});
