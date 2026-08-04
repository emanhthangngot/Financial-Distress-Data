import type {
  AbExperimentSummary,
  AuditEvent,
  CostBudget,
  GitRevisionCardData,
  ObservabilityLink,
  PipelineRow,
  PlaneStatus,
  PromotionCandidate,
} from "@distresslens/contracts";

/**
 * Operations fixtures matching UI-APPROVED-03. The evidence-session row itself
 * is not fixed here: it comes from the session state machine so the lifecycle
 * states render from real transition data rather than a hard-coded label.
 */

export const FIXTURE_ENVIRONMENT_LABEL = "AWS Evidence";

export function fixturePlanes(planeReady: boolean): readonly PlaneStatus[] {
  return [
    { component: "WEB", health: "ONLINE", checkedAt: "2025-05-22T18:32:00+07:00", detail: null },
    {
      component: "SUPABASE",
      health: "ONLINE",
      checkedAt: "2025-05-22T18:32:00+07:00",
      detail: null,
    },
    {
      component: "EKS_AI",
      health: planeReady ? "ONLINE" : "OFFLINE",
      checkedAt: "2025-05-22T18:32:00+07:00",
      detail: planeReady ? null : "Chưa có phiên evidence nào đang chạy",
    },
  ];
}

export const FIXTURE_BUDGETS: readonly CostBudget[] = [
  { label: "Chi phí AWS", currency: "USD", spentUsd: 36.42, capUsd: 100, periodLabel: "tháng 05" },
  {
    label: "Chi phí Vast",
    currency: "USD",
    spentUsd: 4.35,
    capUsd: 10,
    periodLabel: "toàn khóa học",
  },
];

export const FIXTURE_NEXT_SESSION_AT = "2025-05-23T10:00:00+07:00";

export function fixtureRevision(planeReady: boolean): GitRevisionCardData {
  return {
    desiredRevision: "a1b2c3d",
    desiredBranch: "main",
    // With the plane off, the last observed live revision is all Argo can
    // report; it is rendered beside a LIVE_UNAVAILABLE label.
    liveRevision: planeReady ? "a1b2c3d" : "9f8e7d6",
    liveBranch: "main",
    syncHealth: planeReady ? "HEALTHY" : "UNKNOWN",
    lastSyncedAt: "2025-05-22T18:32:00+07:00",
    appRepoUrl: "https://github.com/dl/infra-apps",
    gitopsRepoUrl: "https://github.com/dl/gitops-config",
  };
}

export const FIXTURE_PIPELINES: readonly PipelineRow[] = [
  {
    id: "data-sync",
    name: "Data sync",
    description: "Đồng bộ dữ liệu từ nguồn",
    owner: "data-team",
    revision: "a1b2c3d",
    status: "SUCCEEDED",
    lastRunAt: "2025-05-22T17:58:00+07:00",
    evidenceUrl: "/ops/evidence#pipeline-data-sync",
  },
  {
    id: "feast-materialization",
    name: "Feast materialization",
    description: "Tính toán features",
    owner: "ml-platform",
    revision: "a1b2c3d",
    status: "SUCCEEDED",
    lastRunAt: "2025-05-22T18:05:00+07:00",
    evidenceUrl: "/ops/evidence#pipeline-feast",
  },
  {
    id: "ml-training",
    name: "ML training",
    description: "Huấn luyện mô hình",
    owner: "ml-team",
    revision: "a1b2c3d",
    status: "SUCCEEDED",
    lastRunAt: "2025-05-22T18:12:00+07:00",
    evidenceUrl: "/ops/evidence#pipeline-training",
  },
  {
    id: "rag-indexing",
    name: "RAG indexing",
    description: "Lập chỉ mục tri thức",
    owner: "nlp-team",
    revision: "a1b2c3d",
    status: "SUCCEEDED",
    lastRunAt: "2025-05-22T18:15:00+07:00",
    evidenceUrl: "/ops/evidence#pipeline-rag",
  },
  {
    id: "mcp-publish",
    name: "MCP publish",
    description: "Xuất bản MCP tools",
    owner: "platform-team",
    revision: "a1b2c3d",
    status: "DEGRADED",
    lastRunAt: "2025-05-22T18:20:00+07:00",
    evidenceUrl: "/ops/evidence#pipeline-mcp",
  },
  {
    id: "agent-publish",
    name: "Agent publish",
    description: "Xuất bản Agent",
    owner: "agent-team",
    revision: "a1b2c3d",
    status: "FAILED",
    lastRunAt: "2025-05-22T18:22:00+07:00",
    evidenceUrl: "/ops/evidence#pipeline-agent",
  },
];

export const FIXTURE_PROMOTIONS: readonly PromotionCandidate[] = [
  {
    id: "promo-ml-model",
    kind: "ML model",
    candidate: "DL-Score v2.2.0",
    revision: "c4d5e6f",
    owner: "ml-team",
    status: "AWAITING_REVIEW",
    pullRequestUrl: "https://github.com/dl/gitops-config/pull/128",
  },
  {
    id: "promo-qwen-lora",
    kind: "Qwen LoRA",
    candidate: "Qwen3-14B-LoRA-v1.3",
    revision: "b7c8d9e",
    owner: "nlp-team",
    status: "AWAITING_REVIEW",
    pullRequestUrl: "https://github.com/dl/gitops-config/pull/129",
  },
  {
    id: "promo-coordinator",
    kind: "Coordinator agent",
    candidate: "coordinator-exp-20250522",
    revision: "f1a2b3c",
    owner: "agent-team",
    status: "AWAITING_REVIEW",
    pullRequestUrl: "https://github.com/dl/gitops-config/pull/130",
  },
];

export const FIXTURE_EXPERIMENTS: readonly AbExperimentSummary[] = [
  {
    id: "exp-20250514",
    startedAt: "2025-05-14T00:00:00+07:00",
    variants: [
      {
        name: "Coordinator A — Qwen base",
        trafficShare: 50,
        callCount24h: 12_432,
        successRate: 91.2,
        p95LatencyMs: 2310,
        toolErrorRate: 3.2,
      },
      {
        name: "Coordinator B — Qwen LoRA",
        trafficShare: 50,
        callCount24h: 12_087,
        successRate: 93.6,
        p95LatencyMs: 2045,
        toolErrorRate: 1.8,
      },
    ],
    dashboardUrl: "https://grafana.internal/d/ab-coordinator",
  },
];

export const FIXTURE_AUDIT_EVENTS: readonly AuditEvent[] = [
  {
    id: "audit-1832",
    occurredAt: "2025-05-22T18:32:00+07:00",
    category: "Argo Sync",
    detail: "Synced revision a1b2c3d -> live",
    actor: "argo-bot",
    result: "SUCCESS",
  },
  {
    id: "audit-1820",
    occurredAt: "2025-05-22T18:20:00+07:00",
    category: "Approval",
    detail: "PR #128 approved",
    actor: "trang.nguyen",
    result: "SUCCESS",
  },
  {
    id: "audit-1818",
    occurredAt: "2025-05-22T18:18:00+07:00",
    category: "GitHub PR",
    detail: "PR #128 opened: feat(agent) cập nhật coordinator prompt",
    actor: "dat.le",
    result: "SUCCESS",
  },
  {
    id: "audit-1758",
    occurredAt: "2025-05-22T17:58:00+07:00",
    category: "Admin Action",
    detail: "Tạo phiên evidence: ev-20250522-1000",
    actor: "minhanh.nguyen",
    result: "SUCCESS",
  },
  {
    id: "audit-1655",
    occurredAt: "2025-05-22T16:55:00+07:00",
    category: "Admin Action",
    detail: "Cập nhật hạn mức Vast: 10 -> 10",
    actor: "minhanh.nguyen",
    result: "SUCCESS",
  },
];

export function fixtureObservabilityLinks(planeReady: boolean): readonly ObservabilityLink[] {
  return [
    { label: "Xem Grafana", href: "https://grafana.internal", available: planeReady },
    { label: "Xem Kibana", href: "https://kibana.internal", available: planeReady },
    { label: "Xem Jaeger", href: "https://jaeger.internal", available: planeReady },
    { label: "Mở Agent Registry", href: "/agents/registry", available: true },
  ];
}
