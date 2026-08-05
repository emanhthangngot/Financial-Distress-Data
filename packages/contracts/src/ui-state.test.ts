import { describe, expect, it } from "vitest";
import { UI_STATES, isNonSuccessState, isUiState, validateStateCopy, type StateCopy } from "./ui-state";
import { DISCLAIMER_SURFACES, DISCLAIMER_TEXT, requiresDisclaimer } from "./disclaimer";

const goodCopy: StateCopy = {
  unavailable: "Không tải được dữ liệu doanh nghiệp.",
  lastKnown: "Đang hiển thị kết quả lưu lúc 22/05/2025 08:46.",
  nextAction: "Tải lại trang hoặc xem báo cáo đã lưu.",
};

describe("validateStateCopy", () => {
  it("accepts copy answering all three questions", () => {
    expect(validateStateCopy(goodCopy)).toEqual([]);
  });

  it("rejects copy that never says what is unavailable", () => {
    expect(validateStateCopy({ ...goodCopy, unavailable: "" })).toContain(
      "state copy must say what is unavailable",
    );
  });

  it("rejects copy with no safe next action", () => {
    expect(validateStateCopy({ ...goodCopy, nextAction: "   " })).toContain(
      "state copy must offer a safe next action",
    );
  });

  it("accepts a null lastKnown when genuinely nothing is cached", () => {
    expect(validateStateCopy({ ...goodCopy, lastKnown: null })).toEqual([]);
  });

  it("rejects an empty-string lastKnown, which skips the question rather than answering it", () => {
    expect(validateStateCopy({ ...goodCopy, lastKnown: "" })).toHaveLength(1);
  });
});

describe("isNonSuccessState", () => {
  it("treats every state except success and loading as needing copy", () => {
    const needCopy = UI_STATES.filter(isNonSuccessState);
    expect(needCopy).toEqual([
      "empty",
      "stale",
      "degraded",
      "forbidden",
      "timeout",
      "policy_blocked",
      "error",
    ]);
  });
});

describe("disclaimer", () => {
  it("pins the exact coursework wording", () => {
    expect(DISCLAIMER_TEXT).toBe(
      "Nội dung phục vụ mục đích học tập, không phải khuyến nghị đầu tư.",
    );
  });

  it("covers every decision-support surface named by phase-02", () => {
    expect([...DISCLAIMER_SURFACES]).toEqual([
      "company",
      "model_explanation",
      "agent_chat",
      "compare",
      "report_export",
    ]);
  });

  it("does not require the disclaimer on operations surfaces", () => {
    expect(requiresDisclaimer("ops_evidence")).toBe(false);
    expect(requiresDisclaimer("company")).toBe(true);
  });
});

describe("isUiState", () => {
  it("accepts every known state", () => {
    for (const state of UI_STATES) expect(isUiState(state)).toBe(true);
  });

  it("rejects a value outside the known union, including non-strings", () => {
    expect(isUiState("mystery")).toBe(false);
    expect(isUiState(42)).toBe(false);
  });
});
