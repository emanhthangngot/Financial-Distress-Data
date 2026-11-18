import "server-only";
import type {
  AgentLifecycle,
  AgentRegistryEntry,
  AgentRegistryView,
  Provenance,
  ViewState,
} from "@distresslens/contracts";
import { absoluteHttpUrl } from "../server/http-endpoint";
import { copyFor, denied, guard } from "./fixture-adapter";
import type { RequestContext } from "./port";

const REQUEST_TIMEOUT_MS = 3_000;

interface LiveRegistryPayload {
  agents?: unknown;
}

interface LiveRegistryAgent {
  name?: unknown;
  version?: unknown;
  status?: unknown;
  modelConfig?: unknown;
  tool?: unknown;
  specialists?: unknown;
  replicas?: unknown;
  maxHops?: unknown;
}

function registryUnavailable(state: "degraded" | "error"): ViewState<AgentRegistryView> {
  return { state, copy: copyFor("/agents/registry", state), data: null };
}

/** Read the configured live registry without falling back to product fixtures. */
export async function getLiveAgentRegistry(
  context: RequestContext,
  liveEnabled = true,
): Promise<ViewState<AgentRegistryView>> {
  if (context.userId === null) return denied("/agents/registry", null);
  const rejection = guard<AgentRegistryView>(context, "session.read", "/agents/registry");
  if (rejection !== null) return rejection;
  if (!liveEnabled || !context.planeReady) return registryUnavailable("degraded");

  const env = process["env"];
  const rawUrl = env["DISTRESSLENS_AGENT_REGISTRY_URL"];
  const token = env["DISTRESSLENS_AGENT_REGISTRY_TOKEN"];
  if (rawUrl === undefined) return registryUnavailable("degraded");
  const url = absoluteHttpUrl(rawUrl, token);
  const provenance = liveProvenance(env);
  if (url === null || provenance === null) {
    return registryUnavailable("error");
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      headers: { accept: "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      cache: "no-store",
      redirect: "error",
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`registry returned ${response.status}`);
    const payload = (await response.json()) as LiveRegistryPayload;
    if (!Array.isArray(payload.agents)) throw new Error("registry agents must be an array");

    const entries = payload.agents.map((raw) => normalizeEntry(raw));
    const data: AgentRegistryView = { entries, provenance };
    // The registry route has no empty-state copy contract; an empty live
    // registry is still a successful, truthful response with zero entries.
    return { state: "success", data };
  } catch {
    return registryUnavailable("error");
  } finally {
    clearTimeout(timer);
  }
}

function normalizeEntry(raw: unknown): AgentRegistryEntry {
  if (raw === null || typeof raw !== "object") throw new Error("registry entry must be an object");
  const item = raw as LiveRegistryAgent;
  const name = requiredText(item.name, "name");
  const version = requiredText(item.version, "version");
  const status = String(item.status ?? "active").toLowerCase();
  const modelConfig = requiredText(item.modelConfig, "modelConfig");
  const replicas = item.replicas && typeof item.replicas === "object"
    ? (item.replicas as { min?: unknown; ready?: unknown; lastHeartbeatAt?: unknown })
    : {};
  const desired = replicaCount(replicas.min);
  const ready = replicaCount(replicas.ready);
  const allowedEgress = [item.tool, ...(Array.isArray(item.specialists) ? item.specialists : [])]
    .filter((value): value is string => typeof value === "string" && value.trim() !== "")
    .map((value) => value.trim());

  return {
    id: name,
    name,
    version,
    lifecycle: lifecycleFor(status),
    modelVersion: modelConfig,
    sandbox: {
      allowedEgress,
      filesystemAccess: "NONE",
      maxToolCallsPerRequest: positiveInteger(item.maxHops, 1),
      timeoutMs: 30_000,
    },
    replicas: {
      desired,
      ready,
      lastHeartbeatAt:
        typeof replicas.lastHeartbeatAt === "string" ? replicas.lastHeartbeatAt : null,
    },
    promotedAt: null,
    promotedBy: null,
  };
}

function replicaCount(value: unknown): number | null {
  return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : null;
}

function lifecycleFor(status: string): AgentLifecycle {
  if (status === "retired") return "RETIRED";
  if (status === "candidate") return "CANDIDATE";
  if (status === "draft") return "DRAFT";
  return "PRODUCTION";
}

function requiredText(value: unknown, field: string): string {
  if (typeof value !== "string" || value.trim() === "") throw new Error(`registry ${field} is required`);
  return value.trim();
}

function positiveInteger(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isInteger(value) && value > 0 ? value : fallback;
}

function liveProvenance(env: NodeJS.ProcessEnv): Provenance | null {
  const sourceSha = env["DISTRESSLENS_SOURCE_SHA"];
  const gitopsSha = env["DISTRESSLENS_GITOPS_SHA"];
  const validSha = (value: string | undefined): value is string =>
    value !== undefined && /^[0-9a-f]{7,40}$/i.test(value);
  if (!validSha(sourceSha) || (gitopsSha !== undefined && !validSha(gitopsSha))) return null;
  return {
    freshness: "LIVE",
    planeAvailability: "LIVE_AVAILABLE",
    origin: "EVIDENCE_PLANE",
    cachedAt: null,
    sourceSha,
    gitopsSha: gitopsSha ?? null,
    dataVersion: env["DISTRESSLENS_DATA_VERSION"] ?? "platform-live",
    modelVersion: env["DISTRESSLENS_MODEL_VERSION"] ?? null,
    agentVersion: env["DISTRESSLENS_AGENT_VERSION"] ?? null,
    runId: env["DISTRESSLENS_RUN_ID"] ?? null,
  };
}
