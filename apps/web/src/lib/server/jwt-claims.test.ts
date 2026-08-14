import { describe, expect, it } from "vitest";
import { decodeJwtPayload, readAssuranceLevel } from "./jwt-claims";

const AAL2_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhYWwiOiJhYWwyIiwic3ViIjoidTEifQ.sig";
const AAL1_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhYWwiOiJhYWwxIiwic3ViIjoidTEifQ.sig";
const NO_CLAIM_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1MSJ9.sig";

describe("decodeJwtPayload", () => {
  it("decodes a well-formed payload", () => {
    expect(decodeJwtPayload(AAL2_TOKEN)).toEqual({ aal: "aal2", sub: "u1" });
  });

  it("returns null for a null token", () => {
    expect(decodeJwtPayload(null)).toBeNull();
  });

  it("returns null for a token with the wrong number of segments", () => {
    expect(decodeJwtPayload("not-a-jwt")).toBeNull();
  });

  it("returns null for a segment that is not valid base64url JSON", () => {
    expect(decodeJwtPayload("header.%%%not-base64%%%.sig")).toBeNull();
  });
});

describe("readAssuranceLevel", () => {
  it("reports aal2 when the verified claim says aal2", () => {
    expect(readAssuranceLevel(AAL2_TOKEN)).toBe("aal2");
  });

  it("reports aal1 for an explicit aal1 claim", () => {
    expect(readAssuranceLevel(AAL1_TOKEN)).toBe("aal1");
  });

  it("fails closed to aal1 when the claim is missing", () => {
    expect(readAssuranceLevel(NO_CLAIM_TOKEN)).toBe("aal1");
  });

  it("fails closed to aal1 for a null token", () => {
    expect(readAssuranceLevel(null)).toBe("aal1");
  });

  it("fails closed to aal1 for a malformed token", () => {
    expect(readAssuranceLevel("garbage")).toBe("aal1");
  });
});
