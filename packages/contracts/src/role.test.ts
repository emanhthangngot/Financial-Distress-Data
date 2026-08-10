import { describe, expect, it } from "vitest";
import { roleAllows, isPrivilegedRole, isRole } from "./role";

describe("roleAllows", () => {
  it("denies platform operations to analyst", () => {
    expect(roleAllows("analyst", "session.provision")).toBe(false);
    expect(roleAllows("analyst", "analyst.run_ai_request")).toBe(true);
  });

  it("denies mutation to platform_viewer", () => {
    expect(roleAllows("platform_viewer", "session.provision")).toBe(false);
    expect(roleAllows("platform_viewer", "session.destroy")).toBe(false);
    expect(roleAllows("platform_viewer", "session.read")).toBe(true);
  });

  it("denies role/security changes to platform_operator", () => {
    expect(roleAllows("platform_operator", "session.manage_roles")).toBe(false);
    expect(roleAllows("platform_operator", "session.promote")).toBe(false);
    expect(roleAllows("platform_operator", "session.provision")).toBe(true);
  });

  it("grants full lifecycle + governance to platform_admin", () => {
    expect(roleAllows("platform_admin", "session.manage_roles")).toBe(true);
    expect(roleAllows("platform_admin", "session.promote")).toBe(true);
  });

  it("flags all non-analyst roles as privileged (AAL2-required)", () => {
    expect(isPrivilegedRole("analyst")).toBe(false);
    expect(isPrivilegedRole("platform_viewer")).toBe(true);
    expect(isPrivilegedRole("platform_operator")).toBe(true);
    expect(isPrivilegedRole("platform_admin")).toBe(true);
  });

  it("denies (not throws) for a role string outside the known union", () => {
    expect(roleAllows("nonexistent_role" as never, "session.read")).toBe(false);
  });
});

describe("isRole", () => {
  it("accepts every known role", () => {
    expect(isRole("analyst")).toBe(true);
    expect(isRole("platform_admin")).toBe(true);
  });

  it("rejects a value outside the known union, including non-strings", () => {
    expect(isRole("superuser")).toBe(false);
    expect(isRole(null)).toBe(false);
  });
});
