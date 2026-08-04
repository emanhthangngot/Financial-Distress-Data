import type { AgentMessage, AgentRegistryEntry } from "@distresslens/contracts";

/**
 * Agent-surface fixtures matching UI-APPROVED-02's analysis panel and the
 * registry in UI-APPROVED-03.
 *
 * The trace records tool name, status and a redacted one-line summary. It holds
 * no prompt text, no credentials and no raw model output — that omission is the
 * security contract, not an oversight.
 */

export const FIXTURE_CONVERSATION_ID = "conv-20250522-0844";
export const FIXTURE_AGENT_ID = "coordinator";

export const FIXTURE_AGENT_MESSAGES: readonly AgentMessage[] = [
  {
    id: "msg-user-1",
    role: "user",
    body: "Vì sao NVL đang ở mức rủi ro rất cao?",
    createdAt: "2025-05-22T08:44:00+07:00",
    state: "complete",
    citations: [],
    toolTrace: [],
    agentVersion: null,
    modelVersion: null,
  },
  {
    id: "msg-agent-1",
    role: "agent",
    body: [
      "NVL đang ở mức rủi ro rất cao (xác suất distress 78.6%) chủ yếu do:",
      "• Đòn bẩy tài chính cao: Debt/Asset đạt 0.79, cao hơn trung vị ngành (0.58) và tăng liên tục 4 quý. [1]",
      "• Dòng tiền kinh doanh âm: -2.386 tỷ VND trong Q1/2025, phản ánh áp lực thanh khoản. [1]",
      "• Khả năng thanh toán ngắn hạn yếu: Current Ratio 0.66, thấp hơn ngưỡng an toàn 1.0. [1]",
      "• Hiệu quả sinh lời thấp: ROA -3.1%, duy trì âm trong 6 quý liên tiếp. [1]",
      "Ngoài ra, Z-score (Altman) ở mức -1.35, dưới ngưỡng cảnh báo 1.8, cho thấy rủi ro phá sản cao theo mô hình. [2]",
    ].join("\n"),
    createdAt: "2025-05-22T08:45:00+07:00",
    state: "complete",
    citations: [
      {
        ordinal: 1,
        sourceId: "src-bctc-q1-2025",
        title: "BCTC hợp nhất Q1/2025 – NVL",
        publisher: "HOSE",
        url: "https://www.hsx.vn",
      },
      {
        ordinal: 2,
        sourceId: "src-internal-dlscore",
        title: "Tính toán nội bộ DL-Score v2.1",
        publisher: "DistressLens",
        url: null,
      },
    ],
    toolTrace: [
      {
        id: "tool-1",
        toolName: "feature-rag-mcp",
        status: "SUCCEEDED",
        summary: "Truy vấn 42 đoạn dữ liệu tài chính mới nhất",
        startedAt: "2025-05-22T08:45:00+07:00",
        durationMs: 1840,
      },
      {
        id: "tool-2",
        toolName: "drift-mcp",
        status: "SUCCEEDED",
        summary: "Kiểm tra drift dữ liệu & mô hình",
        startedAt: "2025-05-22T08:45:02+07:00",
        durationMs: 920,
      },
    ],
    agentVersion: "coordinator-exp-20250522",
    modelVersion: "Qwen3-14B-LoRA-v1.3",
  },
];

export const FIXTURE_REGISTRY_ENTRIES: readonly AgentRegistryEntry[] = [
  {
    id: "coordinator",
    name: "Coordinator agent",
    version: "coordinator-exp-20250522",
    lifecycle: "CANDIDATE",
    modelVersion: "Qwen3-14B-LoRA-v1.3",
    sandbox: {
      allowedEgress: ["feature-rag-mcp.internal", "drift-mcp.internal"],
      filesystemAccess: "NONE",
      maxToolCallsPerRequest: 8,
      timeoutMs: 30_000,
    },
    replicas: { desired: 2, ready: 2, lastHeartbeatAt: "2025-05-22T18:20:00+07:00" },
    promotedAt: null,
    promotedBy: null,
  },
  {
    id: "coordinator-base",
    name: "Coordinator agent (base)",
    version: "coordinator-20250501",
    lifecycle: "PRODUCTION",
    modelVersion: "Qwen3-14B-base",
    sandbox: {
      allowedEgress: ["feature-rag-mcp.internal"],
      filesystemAccess: "NONE",
      maxToolCallsPerRequest: 6,
      timeoutMs: 30_000,
    },
    replicas: { desired: 2, ready: 2, lastHeartbeatAt: "2025-05-22T18:20:00+07:00" },
    promotedAt: "2025-05-01T09:00:00+07:00",
    promotedBy: "minhanh.nguyen",
  },
  {
    id: "explainer",
    name: "Explanation agent",
    version: "explainer-20250418",
    lifecycle: "PRODUCTION",
    modelVersion: "Qwen3-14B-base",
    sandbox: {
      allowedEgress: [],
      filesystemAccess: "READ_ONLY",
      maxToolCallsPerRequest: 3,
      timeoutMs: 15_000,
    },
    replicas: { desired: 1, ready: 1, lastHeartbeatAt: "2025-05-22T18:19:00+07:00" },
    promotedAt: "2025-04-18T14:30:00+07:00",
    promotedBy: "dat.le",
  },
  {
    id: "retired-scorer",
    name: "Scoring agent (cũ)",
    version: "scorer-20250210",
    lifecycle: "RETIRED",
    modelVersion: "Qwen2.5-7B",
    sandbox: {
      allowedEgress: [],
      filesystemAccess: "NONE",
      maxToolCallsPerRequest: 2,
      timeoutMs: 10_000,
    },
    replicas: { desired: 0, ready: 0, lastHeartbeatAt: null },
    promotedAt: "2025-02-10T10:00:00+07:00",
    promotedBy: "minhanh.nguyen",
  },
];

/** Per-user AI request budget enforced at the product boundary. */
export const FIXTURE_QUOTA = {
  used: 12,
  limit: 50,
  resetsAt: "2025-05-23T00:00:00+07:00",
};
