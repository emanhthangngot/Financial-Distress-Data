import { describe, expect, it } from "vitest";
import { authorize } from "./authorization";
import { ROLES, ROLE_ACTIONS, type SessionAction } from "./role";

const ALL_ACTIONS: readonly SessionAction[] = [
  "session.read",
  "session.provision",
  "session.destroy",
  "session.retry",
  "session.export_evidence",
  "session.promote",
  "session.rollback",
  "session.manage_roles",
  "analyst.query",
  "analyst.run_ai_request",
  "analyst.save_report",
];

describe("authorize", () => {
  it("denies every action to a signed-out caller", () => {
    for (const action of ALL_ACTIONS) {
      const decision = authorize({ role: null, aal: "aal2" }, action);
      expect(decision.allowed).toBe(false);
      expect(decision.allowed === false && decision.denial).toBe("UNAUTHENTICATED");
    }
  });

  it("denies lifecycle mutation to platform_viewer even at AAL2", () => {
    const decision = authorize({ role: "platform_viewer", aal: "aal2" }, "session.provision");
    expect(decision).toEqual({
      allowed: false,
      denial: "ROLE_NOT_PERMITTED",
      reason: "Vai trò hiện tại không được phép thực hiện session.provision.",
    });
  });

  it("allows a permitted mutation at AAL1 under the demo-environment step-up relaxation", () => {
    // STEP_UP_REQUIRED = false mirrors meets_step_up() in the database: this
    // deployment has no MFA enrollment path, so gating on AAL2 would only
    // lock every privileged role out. See authorization.ts for the revert.
    const decision = authorize({ role: "platform_operator", aal: "aal1" }, "session.provision");
    expect(decision.allowed).toBe(true);
  });

  it("allows privileged reads at AAL1 so the control room stays inspectable", () => {
    expect(authorize({ role: "platform_viewer", aal: "aal1" }, "session.read").allowed).toBe(true);
  });

  it("does not force AAL2 on analyst work", () => {
    expect(authorize({ role: "analyst", aal: "aal1" }, "analyst.run_ai_request").allowed).toBe(
      true,
    );
    expect(authorize({ role: "analyst", aal: "aal1" }, "analyst.save_report").allowed).toBe(true);
  });

  it("matches the role/action contract for every role and action pair", () => {
    for (const role of ROLES) {
      for (const action of ALL_ACTIONS) {
        const permitted = ROLE_ACTIONS[role].includes(action);
        // AAL2 supplied so the only variable under test is the role grant.
        expect(authorize({ role, aal: "aal2" }, action).allowed).toBe(permitted);
      }
    }
  });

  it("never leaks the protected resource in a denial reason", () => {
    const decision = authorize({ role: "analyst", aal: "aal2" }, "session.promote");
    expect(decision.allowed).toBe(false);
    expect(decision.allowed === false && decision.reason).not.toMatch(/session-|ev-|uuid/i);
  });
});
