import { describe, expect, it } from "vitest";
import { validateStateCopy } from "@distresslens/contracts";
import {
  ASSISTANT_STATE_COPY,
  PRODUCT_ROUTES,
  ROUTE_STATE_COPY,
  type ProductRoute,
} from "./route-states";

/**
 * The route/state inventory from phase-02. Listed here independently of the
 * catalog so a state silently dropped from the catalog fails rather than
 * quietly shrinking what the product promises to handle.
 */
const REQUIRED_STATES: Record<ProductRoute, readonly string[]> = {
  "/": ["error", "degraded"],
  "/companies": ["empty", "stale", "error"],
  "/companies/[ticker]": ["degraded", "empty", "forbidden", "error"],
  "/compare": ["empty", "error"],
  "/reports": ["forbidden", "empty", "error"],
  "/reports/[id]": ["forbidden", "error"],
  "/agents/registry": ["forbidden", "degraded", "error"],
  "/ops/evidence": ["forbidden", "degraded", "error"],
};

describe("route state catalog", () => {
  it("covers every route in the phase-02 inventory", () => {
    expect([...PRODUCT_ROUTES].sort()).toEqual(Object.keys(REQUIRED_STATES).sort());
  });

  it("defines copy for every required non-success state", () => {
    for (const route of PRODUCT_ROUTES) {
      for (const state of REQUIRED_STATES[route]) {
        expect(
          ROUTE_STATE_COPY[route][state as keyof (typeof ROUTE_STATE_COPY)[ProductRoute]],
          `${route} is missing copy for ${state}`,
        ).toBeDefined();
      }
    }
  });

  it("answers what is unavailable and what to do next in every state", () => {
    for (const route of PRODUCT_ROUTES) {
      for (const [state, copy] of Object.entries(ROUTE_STATE_COPY[route])) {
        expect(validateStateCopy(copy), `${route}/${state}`).toEqual([]);
      }
    }
  });

  it("never leaks a stack trace or raw error code into user copy", () => {
    for (const route of PRODUCT_ROUTES) {
      for (const [state, copy] of Object.entries(ROUTE_STATE_COPY[route])) {
        const text = `${copy.unavailable} ${copy.lastKnown ?? ""} ${copy.nextAction}`;
        expect(text, `${route}/${state}`).not.toMatch(/Error:|at \w+\.|undefined|null|500\b/);
      }
    }
  });

  it("gives every route forbidden copy, because the server guard can deny on any of them", () => {
    for (const route of PRODUCT_ROUTES) {
      expect(ROUTE_STATE_COPY[route].forbidden, `${route} cannot render a denial`).toBeDefined();
    }
  });

  it("keeps the assistant's own states, since it is a surface on every route", () => {
    // The assistant is not a route, but it can still be denied, degraded,
    // timed out or policy-blocked, and each of those owes the analyst copy.
    for (const state of ["forbidden", "degraded", "timeout", "policy_blocked", "error"] as const) {
      const copy = ASSISTANT_STATE_COPY[state];
      expect(copy, `assistant is missing copy for ${state}`).toBeDefined();
      expect(validateStateCopy(copy!), `assistant/${state}`).toEqual([]);
    }
  });

  it("explains the missing permission without naming the protected resource", () => {
    const forbidden = ROUTE_STATE_COPY["/companies/[ticker]"].forbidden;
    expect(forbidden?.unavailable).toContain("quyền");
    expect(forbidden?.unavailable).not.toMatch(/NVL|HPG/);
  });
});
