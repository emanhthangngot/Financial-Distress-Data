import { describe, expect, it } from "vitest";
import type { StateCopy, ViewState } from "@distresslens/contracts";
import { isFailureState, viewCopy, viewData } from "./view-state";

const loading: StateCopy = {
  unavailable: "Đang tải.",
  lastKnown: null,
  nextAction: "Chờ vài giây.",
};

const degradedCopy: StateCopy = {
  unavailable: "Suy luận trực tiếp không khả dụng.",
  lastKnown: "Đang hiển thị kết quả đã lưu.",
  nextAction: "Đọc kết quả đã lưu.",
};

describe("view state reading", () => {
  it("gives a success state its data and no explanation", () => {
    const view: ViewState<number> = { state: "success", data: 42 };
    expect(viewData(view)).toBe(42);
    expect(viewCopy(view, loading)).toBeNull();
  });

  it("gives a loading state no data and the caller's own loading copy", () => {
    const view: ViewState<number> = { state: "loading" };
    expect(viewData(view)).toBeNull();
    expect(viewCopy(view, loading)).toBe(loading);
  });

  it("keeps the cached data a degraded state carries, alongside its explanation", () => {
    // This is the case the product depends on: the plane is off, there is still
    // a saved result to render, and it must render with the caveat attached.
    const view: ViewState<number> = { state: "degraded", copy: degradedCopy, data: 7 };
    expect(viewData(view)).toBe(7);
    expect(viewCopy(view, loading)).toBe(degradedCopy);
    expect(isFailureState(view)).toBe(false);
  });

  it("treats a denial as an explanation with nothing to render", () => {
    const view: ViewState<number> = { state: "forbidden", copy: degradedCopy, data: null };
    expect(viewData(view)).toBeNull();
    expect(isFailureState(view)).toBe(false);
  });

  it("marks only a hard error as a failure, so a denial is not styled as a crash", () => {
    const error: ViewState<number> = { state: "error", copy: degradedCopy, data: null };
    const empty: ViewState<number> = { state: "empty", copy: degradedCopy, data: null };
    expect(isFailureState(error)).toBe(true);
    expect(isFailureState(empty)).toBe(false);
  });
});
