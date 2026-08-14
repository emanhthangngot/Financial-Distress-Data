import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/**
 * Accessibility proof for the route inventory.
 *
 * The same spec runs under two configs: `playwright.a11y.config.ts` (analyst,
 * plane on) and `playwright.a11y-roles.config.ts` (platform operator, plane
 * off). Visiting every route under both identities means a route this role
 * cannot reach still gets checked — in its forbidden/degraded state, which
 * must be as accessible as the success state.
 *
 * Zero serious or critical violations is the bar; a moderate violation is
 * accepted only when `docs/phase2/evidence/product/accessibility.md` names it
 * and says why.
 */

const ROUTES = [
  "/",
  "/sign-in",
  "/sign-up",
  "/companies",
  "/companies/NVL",
  "/compare?ticker=NVL",
  "/reports",
  "/agents/registry",
  "/ops/evidence",
];

for (const route of ROUTES) {
  test(`${route} has no serious or critical accessibility violation`, async ({ page }) => {
    // "networkidle" never resolves on a route the assistant keeps a
    // connection open on; the default "load" wait plus a short settle for the
    // fixture data to render is what the existing evidence specs rely on too.
    await page.goto(route, { waitUntil: "load" });
    await page.waitForTimeout(500);

    const results = await new AxeBuilder({ page }).analyze();
    const serious = results.violations.filter(
      (violation) => violation.impact === "serious" || violation.impact === "critical",
    );

    expect(
      serious,
      serious.map((v) => `${v.id}: ${v.help} (${v.nodes.length} node(s))`).join("\n"),
    ).toEqual([]);
  });
}

test("respects prefers-reduced-motion: no animated transform on the primary route", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");

  const animatedTransforms = await page.evaluate(() => {
    const offenders: string[] = [];
    for (const el of Array.from(document.querySelectorAll("*"))) {
      const style = getComputedStyle(el);
      if (
        style.transitionProperty.includes("transform") &&
        parseFloat(style.transitionDuration) > 0
      ) {
        offenders.push(el.tagName.toLowerCase() + (el.className ? `.${el.className}` : ""));
      }
    }
    return offenders;
  });

  expect(animatedTransforms).toEqual([]);
});

test("the primary action on the overview route has a visible focus style", async ({ page }) => {
  await page.goto("/");
  // The overview route renders a different primary action per role — an
  // analyst sees a company link, a platform operator sees a forbidden-state
  // control — so this asserts the property every role's first focusable
  // control must have, not one role's specific label.
  const firstFocusable = page.locator("a, button").first();
  await firstFocusable.focus();

  const outline = await firstFocusable.evaluate((el) => getComputedStyle(el).outlineStyle);
  const boxShadow = await firstFocusable.evaluate((el) => getComputedStyle(el).boxShadow);
  // Tailwind's focus-visible utilities land as either an outline or a
  // box-shadow ring; either is an acceptable visible indicator, "none" for
  // both is not.
  expect(outline !== "none" || boxShadow !== "none").toBe(true);
});
