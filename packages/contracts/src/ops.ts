import type { Provenance } from "./provenance";
import type { SessionState } from "./session-state";

/**
 * Admin operations contracts for `/ops/evidence`: plane health, cost control,
 * GitOps revisions, pipelines, promotion queue, A/B summary and audit trail.
 */

export const PLANE_COMPONENTS = ["WEB", "SUPABASE", "EKS_AI"] as const;
export type PlaneComponent = (typeof PLANE_COMPONENTS)[number];

export const PLANE_HEALTH = ["ONLINE", "DEGRADED", "OFFLINE", "UNKNOWN"] as const;
export type PlaneHealth = (typeof PLANE_HEALTH)[number];

export interface PlaneStatus {
  component: PlaneComponent;
  health: PlaneHealth;
  checkedAt: string;
  /** Set when health is not ONLINE, so the operator sees why, not just a dot. */
  detail: string | null;
}

/**
 * A hard cap, not a warning threshold: spend stops at `capUsd`. `projectedUsd`
 * is what the requested action would add on top of `spentUsd`.
 */
export interface CostBudget {
  label: string;
  currency: "USD";
  spentUsd: number;
  capUsd: number;
  periodLabel: string;
}

export interface CostProjection {
  budgetLabel: string;
  projectedUsd: number;
  /** Human-readable basis, e.g. "2 giờ EKS + 1 GPU Vast". */
  basis: string;
  estimatedDurationMinutes: number;
}

export const COST_GATE_RESULTS = ["ALLOW", "DENY_CAP_EXCEEDED"] as const;
export type CostGateResult = (typeof COST_GATE_RESULTS)[number];

export interface CostGateDecision {
  result: CostGateResult;
  projectedTotalUsd: number;
  remainingUsd: number;
  reason: string | null;
}

/**
 * Preflight cost gate, evaluated server-side before a provision request reaches
 * the outbox. Destroy is deliberately never routed through this gate: blocking
 * teardown at the cap would strand the exact session that is burning the money.
 */
export function evaluateCostGate(
  budget: CostBudget,
  projection: CostProjection,
): CostGateDecision {
  const projectedTotalUsd = round2(budget.spentUsd + projection.projectedUsd);
  const remainingUsd = round2(budget.capUsd - budget.spentUsd);

  if (projectedTotalUsd > budget.capUsd) {
    return {
      result: "DENY_CAP_EXCEEDED",
      projectedTotalUsd,
      remainingUsd,
      reason: `Chi phí dự kiến ${projectedTotalUsd} USD vượt hạn mức ${budget.capUsd} USD của ${budget.periodLabel}`,
    };
  }

  return { result: "ALLOW", projectedTotalUsd, remainingUsd, reason: null };
}

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}

export const ARGO_SYNC_HEALTH = ["HEALTHY", "PROGRESSING", "DEGRADED", "UNKNOWN"] as const;
export type ArgoSyncHealth = (typeof ARGO_SYNC_HEALTH)[number];

export interface GitRevisionCardData {
  desiredRevision: string;
  desiredBranch: string;
  liveRevision: string;
  liveBranch: string;
  syncHealth: ArgoSyncHealth;
  lastSyncedAt: string;
  appRepoUrl: string;
  gitopsRepoUrl: string;
}

/** Desired and live diverging is the operator's cue that a sync is pending. */
export function isGitOpsDrifted(revision: GitRevisionCardData): boolean {
  return revision.desiredRevision !== revision.liveRevision;
}

export const PIPELINE_STATUSES = ["SUCCEEDED", "RUNNING", "DEGRADED", "FAILED", "IDLE"] as const;
export type PipelineStatus = (typeof PIPELINE_STATUSES)[number];

export interface PipelineRow {
  id: string;
  name: string;
  description: string;
  owner: string;
  revision: string;
  status: PipelineStatus;
  lastRunAt: string;
  evidenceUrl: string | null;
}

export const PROMOTION_STATUSES = ["AWAITING_REVIEW", "APPROVED", "REJECTED", "MERGED"] as const;
export type PromotionStatus = (typeof PROMOTION_STATUSES)[number];

export interface PromotionCandidate {
  id: string;
  kind: string;
  candidate: string;
  revision: string;
  owner: string;
  status: PromotionStatus;
  pullRequestUrl: string | null;
}

export interface AbVariant {
  name: string;
  trafficShare: number;
  callCount24h: number;
  successRate: number;
  p95LatencyMs: number;
  toolErrorRate: number;
}

export interface AbExperimentSummary {
  id: string;
  startedAt: string;
  variants: readonly AbVariant[];
  dashboardUrl: string | null;
}

export interface AuditEvent {
  id: string;
  occurredAt: string;
  category: string;
  /** Already-redacted detail: never a prompt, token or credential. */
  detail: string;
  actor: string;
  result: "SUCCESS" | "DENIED" | "FAILED";
}

export interface ObservabilityLink {
  label: string;
  href: string;
  /** False when the evidence plane is off and the target cannot answer. */
  available: boolean;
}

export interface EvidenceSessionView {
  id: string | null;
  state: SessionState;
  version: number;
  actor: string | null;
  leaseExpiry: string | null;
  costSnapshotUsd: number | null;
  gitSha: string | null;
  updatedAt: string | null;
  /**
   * The current concurrency guard the operator observed when this view was
   * rendered. Lifecycle mutations echo it back to `request_session_transition`;
   * a page that renders a stale token (because another operator already moved
   * the session) is rejected with a fencing error instead of clobbering it.
   *
   * This is a freshness guard, not a credential: RLS already limits who may
   * read the session row. It is null only when no session exists.
   */
  fencingToken: string | null;
  /** Transition history, newest first. */
  history: readonly SessionTransitionView[];
}

export interface SessionTransitionView {
  fromState: SessionState;
  toState: SessionState;
  version: number;
  actor: string;
  occurredAt: string;
}

export interface OpsDashboard {
  environmentLabel: string;
  planes: readonly PlaneStatus[];
  budgets: readonly CostBudget[];
  session: EvidenceSessionView;
  nextSessionAt: string | null;
  revision: GitRevisionCardData;
  pipelines: readonly PipelineRow[];
  promotions: readonly PromotionCandidate[];
  experiments: readonly AbExperimentSummary[];
  auditEvents: readonly AuditEvent[];
  observability: readonly ObservabilityLink[];
  provenance: Provenance;
}
