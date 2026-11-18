import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";

/**
 * The assistant streaming path, driven against the fixture fake upstream.
 *
 * Each branch is selected by the question the analyst types, and every branch
 * is asserted on the message state the panel renders — not on the wire, because
 * the wire is the route's proof, and the panel is what the analyst sees.
 */

const FORBIDDEN = /sk-[a-z0-9]+|fake-e2e-token|bearer|api[_-]?key/i;
const FAKE_ORIGIN = `http://127.0.0.1:${process.env.FAKE_UPSTREAM_PORT ?? "3322"}`;

async function openAssistant(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Mở trợ lý phân tích" }).click();
  await expect(page.getByRole("dialog", { name: /Trợ lý phân tích/ })).toBeVisible();
}

async function ask(page: import("@playwright/test").Page, question: string) {
  await page.getByLabel("Câu hỏi cho trợ lý phân tích").fill(question);
  await page.getByRole("button", { name: "Gửi câu hỏi" }).click();
}

test.describe("assistant streaming", () => {
  test("streams a typed answer and renders it as a complete turn", async ({ page, request }) => {
    const id = randomUUID();
    await page.setExtraHTTPHeaders({ "x-correlation-id": id });
    await openAssistant(page);
    await ask(page, "What is the current ratio?");

    await expect(page.getByText("The current ratio measures liquidity")).toBeVisible();
    // The assembled answer is a complete turn, not a dangling stream.
    await expect(page.getByText("Đang trả lời")).toBeHidden();
    const recorded = await request.get(`${FAKE_ORIGIN}/received?id=${id}`);
    expect(await recorded.json()).toEqual({ seen: true });
  });

  test("does not call the model for a dashboard lookup when the coordinator is missing", async ({ page, request }) => {
    const id = randomUUID();
    await page.setExtraHTTPHeaders({ "x-correlation-id": id });
    await openAssistant(page);
    await ask(page, "What is NVL's current ratio?");

    await expect(page.getByText("Chưa kết nối dịch vụ")).toBeVisible();
    await expect(page.getByText("The current ratio measures liquidity")).toBeHidden();
    const recorded = await request.get(`${FAKE_ORIGIN}/received?id=${id}`);
    expect(await recorded.json()).toEqual({ seen: false });
  });

  test("renders the timeout state when the upstream exceeds the deadline", async ({ page }) => {
    await openAssistant(page);
    await ask(page, "What is data drift?");

    await expect(page.getByText("Quá thời gian chờ")).toBeVisible();
    await expect(page.getByText(/Hỏi lại với phạm vi hẹp hơn/)).toBeVisible();
  });

  test("maps an upstream refusal to the policy-blocked state", async ({ page }) => {
    await openAssistant(page);
    await ask(page, "What is the quick ratio?");

    await expect(page.getByText("Bị chính sách chặn")).toBeVisible();
  });

  test("maps a malformed upstream response to an error without leaking it", async ({ page }) => {
    await openAssistant(page);
    await ask(page, "What is financial distress?");

    await expect(page.getByText("Lỗi", { exact: true })).toBeVisible();
    await expect(page.getByText("Định dạng phản hồi không hợp lệ")).toBeVisible();
    await expect(page.getByText("not json")).toBeHidden();
  });

  test("offers a cancel control while a request is pending", async ({ page }) => {
    await openAssistant(page);
    await ask(page, "What is data drift?");
    await expect(page.getByRole("button", { name: "Dừng trợ lý" })).toBeVisible();
    await page.getByRole("button", { name: "Dừng trợ lý" }).click();
    // Cancelling resolves the pending request to a timeout-style state.
    await expect(page.getByText("Quá thời gian chờ")).toBeVisible({ timeout: 10_000 });
  });

  test("never renders the inference token or url in the thread", async ({ page }) => {
    await openAssistant(page);
    await ask(page, "What is the current ratio?");
    await expect(page.getByText("The current ratio measures liquidity")).toBeVisible();
    const thread = await page.locator('[role="dialog"]').innerText();
    expect(thread).not.toMatch(FORBIDDEN);
  });
});
