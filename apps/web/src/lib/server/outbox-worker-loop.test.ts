import { describe, expect, it } from "vitest";
import { DEFAULT_LOOP_CONFIG, ShutdownController, nextBackoffMs, nextDelayMs } from "./outbox-worker-loop";

describe("nextBackoffMs", () => {
  it("doubles each attempt starting at the base", () => {
    expect(nextBackoffMs(0)).toBe(1000);
    expect(nextBackoffMs(1)).toBe(2000);
    expect(nextBackoffMs(2)).toBe(4000);
  });

  it("caps at backoffCapMs", () => {
    expect(nextBackoffMs(10)).toBe(DEFAULT_LOOP_CONFIG.backoffCapMs);
  });

  it("never returns zero for a negative attempt", () => {
    expect(nextBackoffMs(-1)).toBe(1000);
  });
});

describe("nextDelayMs", () => {
  it("sleeps the poll interval after an empty batch", () => {
    expect(nextDelayMs(0, 5)).toBe(DEFAULT_LOOP_CONFIG.pollIntervalMs);
  });

  it("sleeps the poll interval after a partial batch", () => {
    expect(nextDelayMs(3, 5)).toBe(DEFAULT_LOOP_CONFIG.pollIntervalMs);
  });

  it("does not sleep after a full batch — more work is likely queued", () => {
    expect(nextDelayMs(5, 5)).toBe(0);
  });
});

describe("ShutdownController", () => {
  it("stays running until a shutdown is requested", () => {
    const controller = new ShutdownController();
    expect(controller.shouldStop).toBe(false);
  });

  it("finishes the in-flight batch before stopping", () => {
    const controller = new ShutdownController();
    controller.requestShutdown();
    expect(controller.shouldStop).toBe(true);
    expect(controller.isStopped).toBe(false);

    controller.finishBatch();
    expect(controller.isStopped).toBe(true);
  });

  it("a second shutdown request has no further effect", () => {
    const controller = new ShutdownController();
    controller.requestShutdown();
    controller.finishBatch();
    controller.requestShutdown();
    expect(controller.isStopped).toBe(true);
  });
});
