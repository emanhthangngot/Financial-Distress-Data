import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { listDemoAccounts } from "./demo-accounts";

const ENV_VAR = "DISTRESSLENS_DEMO_ACCOUNTS";
const original = process.env[ENV_VAR];

describe("listDemoAccounts", () => {
  beforeEach(() => {
    delete process.env[ENV_VAR];
  });

  afterEach(() => {
    if (original === undefined) {
      delete process.env[ENV_VAR];
    } else {
      process.env[ENV_VAR] = original;
    }
  });

  it("returns an empty list when the env var is unset", () => {
    expect(listDemoAccounts()).toEqual([]);
  });

  it("returns an empty list when the env var is an empty string", () => {
    process.env[ENV_VAR] = "";
    expect(listDemoAccounts()).toEqual([]);
  });

  it("returns an empty list on malformed JSON instead of throwing", () => {
    process.env[ENV_VAR] = "{not json";
    expect(listDemoAccounts()).toEqual([]);
  });

  it("returns an empty list when the JSON is not an array", () => {
    process.env[ENV_VAR] = JSON.stringify({ email: "a@b.c", role: "analyst", label: "A" });
    expect(listDemoAccounts()).toEqual([]);
  });

  it("parses a well-formed list", () => {
    process.env[ENV_VAR] = JSON.stringify([
      { email: "analyst@distresslens.local", role: "analyst", label: "Analyst demo" },
      { email: "operator@distresslens.local", role: "platform_operator", label: "Operator demo" },
    ]);

    expect(listDemoAccounts()).toEqual([
      { email: "analyst@distresslens.local", role: "analyst", label: "Analyst demo" },
      { email: "operator@distresslens.local", role: "platform_operator", label: "Operator demo" },
    ]);
  });

  it("filters out an entry with an invalid role instead of failing the whole list", () => {
    process.env[ENV_VAR] = JSON.stringify([
      { email: "good@distresslens.local", role: "analyst", label: "Good" },
      { email: "bad@distresslens.local", role: "superuser", label: "Bad" },
    ]);

    expect(listDemoAccounts()).toEqual([
      { email: "good@distresslens.local", role: "analyst", label: "Good" },
    ]);
  });

  it("filters out an entry missing a required field", () => {
    process.env[ENV_VAR] = JSON.stringify([{ email: "no-role@distresslens.local", label: "Missing role" }]);

    expect(listDemoAccounts()).toEqual([]);
  });
});
