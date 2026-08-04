import type { Provenance } from "./provenance";

/**
 * Agent surface contracts for `/agents/chat` and `/agents/registry`.
 *
 * Nothing here carries a prompt, token or credential: the tool trace exposes
 * what ran and whether it succeeded, never the text sent to the model. That is
 * a security boundary, so the absence of those fields is deliberate.
 */

export interface Citation {
  /** Display number rendered as an inline chip, 1-based and stable per answer. */
  ordinal: number;
  sourceId: string;
  title: string;
  publisher: string;
  url: string | null;
}

export const TOOL_CALL_STATUSES = ["RUNNING", "SUCCEEDED", "FAILED", "BLOCKED"] as const;
export type ToolCallStatus = (typeof TOOL_CALL_STATUSES)[number];

export interface ToolTraceEntry {
  id: string;
  /** MCP tool name, e.g. feature-rag-mcp. */
  toolName: string;
  status: ToolCallStatus;
  /** One-line description of what the call did, already redacted. */
  summary: string;
  startedAt: string;
  durationMs: number;
}

export const AGENT_MESSAGE_STATES = [
  "complete",
  "streaming",
  "tool_running",
  "timeout",
  "policy_blocked",
  "error",
] as const;
export type AgentMessageState = (typeof AGENT_MESSAGE_STATES)[number];

export interface AgentMessage {
  id: string;
  role: "user" | "agent";
  /** Rendered markdown-free text; citation chips are placed by ordinal. */
  body: string;
  createdAt: string;
  state: AgentMessageState;
  citations: readonly Citation[];
  toolTrace: readonly ToolTraceEntry[];
  agentVersion: string | null;
  modelVersion: string | null;
}

export interface AgentConversation {
  id: string;
  agentId: string;
  messages: readonly AgentMessage[];
  provenance: Provenance;
}

export const AGENT_LIFECYCLE = ["DRAFT", "CANDIDATE", "PRODUCTION", "RETIRED"] as const;
export type AgentLifecycle = (typeof AGENT_LIFECYCLE)[number];

export interface SandboxPolicy {
  /** Hostnames the agent may reach; empty means no egress. */
  allowedEgress: readonly string[];
  filesystemAccess: "NONE" | "READ_ONLY" | "READ_WRITE";
  maxToolCallsPerRequest: number;
  timeoutMs: number;
}

export interface ReplicaHealth {
  desired: number;
  ready: number;
  /** Null when the evidence plane is off and replica counts are unknowable. */
  lastHeartbeatAt: string | null;
}

export interface AgentRegistryEntry {
  id: string;
  name: string;
  version: string;
  lifecycle: AgentLifecycle;
  modelVersion: string;
  sandbox: SandboxPolicy;
  replicas: ReplicaHealth;
  promotedAt: string | null;
  promotedBy: string | null;
}

export interface AgentRegistryView {
  entries: readonly AgentRegistryEntry[];
  provenance: Provenance;
}

/**
 * Per-user AI quota, enforced at the product boundary before any inference
 * request. Rendered so the analyst sees the remaining budget rather than
 * discovering it through a failure.
 */
export interface QuotaState {
  used: number;
  limit: number;
  /** ISO timestamp the window resets. */
  resetsAt: string;
}

export function quotaRemaining(quota: QuotaState): number {
  return Math.max(0, quota.limit - quota.used);
}

export function isQuotaExhausted(quota: QuotaState): boolean {
  return quotaRemaining(quota) === 0;
}
