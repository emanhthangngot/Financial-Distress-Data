import { describe, expect, it } from "vitest";
import {
  evaluateCostGate,
  isGitOpsDrifted,
  type CostBudget,
  type CostProjection,
  type GitRevisionCardData,
} from "./ops";

const budget: CostBudget = {
  label: "Chi phí AWS",
  currency: "USD",
  spentUsd: 36.42,
  capUsd: 100,
  periodLabel: "tháng 05",
};

const projection: CostProjection = {
  budgetLabel: "Chi phí AWS",
  projectedUsd: 12.5,
  basis: "2 giờ EKS + 1 GPU Vast",
  estimatedDurationMinutes: 120,
};

describe("evaluateCostGate", () => {
  it("allows a provision that stays under the hard cap", () => {
    const decision = evaluateCostGate(budget, projection);
    expect(decision.result).toBe("ALLOW");
    expect(decision.projectedTotalUsd).toBe(48.92);
    expect(decision.remainingUsd).toBe(63.58);
    expect(decision.reason).toBeNull();
  });

  it("denies a provision that would cross the cap and says by how much", () => {
    const decision = evaluateCostGate(budget, { ...projection, projectedUsd: 80 });
    expect(decision.result).toBe("DENY_CAP_EXCEEDED");
    expect(decision.projectedTotalUsd).toBe(116.42);
    expect(decision.reason).toContain("100");
  });

  it("allows spend that lands exactly on the cap", () => {
    const decision = evaluateCostGate(budget, { ...projection, projectedUsd: 63.58 });
    expect(decision.result).toBe("ALLOW");
    expect(decision.projectedTotalUsd).toBe(100);
  });

  it("reports zero remaining once the budget is spent out", () => {
    const decision = evaluateCostGate({ ...budget, spentUsd: 100 }, projection);
    expect(decision.result).toBe("DENY_CAP_EXCEEDED");
    expect(decision.remainingUsd).toBe(0);
  });
});

describe("isGitOpsDrifted", () => {
  const revision: GitRevisionCardData = {
    desiredRevision: "a1b2c3d",
    desiredBranch: "main",
    liveRevision: "a1b2c3d",
    liveBranch: "main",
    syncHealth: "HEALTHY",
    lastSyncedAt: "2025-05-22T18:32:00Z",
    appRepoUrl: "https://github.com/dl/infra-apps",
    gitopsRepoUrl: "https://github.com/dl/gitops-config",
  };

  it("is false when desired and live agree", () => {
    expect(isGitOpsDrifted(revision)).toBe(false);
  });

  it("is true when live lags the desired revision", () => {
    expect(isGitOpsDrifted({ ...revision, liveRevision: "9f8e7d6" })).toBe(true);
  });
});
