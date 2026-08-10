import { afterEach, describe, expect, it, vi } from "vitest";
import { getLiveAgentRegistry } from "./live-registry-adapter";

const viewer = {
  userId: "platform-viewer",
  role: "platform_viewer" as const,
  aal: "aal2" as const,
  planeReady: true,
};

const envKeys = [
  "DISTRESSLENS_AGENT_REGISTRY_URL",
  "DISTRESSLENS_SOURCE_SHA",
  "DISTRESSLENS_GITOPS_SHA",
  "DISTRESSLENS_LIVE_PLANE",
];

afterEach(() => {
  vi.unstubAllGlobals();
  for (const key of envKeys) delete process["env"][key];
});

describe("live agent registry adapter", () => {
  it("maps the GitOps registry and stamps evidence-plane provenance", async () => {
    process["env"]["DISTRESSLENS_SOURCE_SHA"] = "f".repeat(40);
    process["env"]["DISTRESSLENS_GITOPS_SHA"] = "a".repeat(40);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            agents: [
              {
                name: "coordinator",
                version: "1.0.0",
                status: "active",
                modelConfig: "fd-global-model-config",
                replicas: { min: 2, max: 3 },
                specialists: ["feature-agent", "drift-agent"],
                maxHops: 2,
              },
            ],
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      ),
    );

    const result = await getLiveAgentRegistry(viewer);

    expect(result).toMatchObject({ state: "success" });
    if (result.state !== "success") return;
    expect(result.data.entries[0]).toMatchObject({
      id: "coordinator",
      lifecycle: "PRODUCTION",
      replicas: { desired: 2, ready: 0 },
    });
    expect(result.data.provenance).toMatchObject({
      origin: "EVIDENCE_PLANE",
      freshness: "LIVE",
      planeAvailability: "LIVE_AVAILABLE",
    });
  });

  it("returns an error state instead of serving fixture entries when the cluster is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connection refused")));

    const result = await getLiveAgentRegistry(viewer);

    expect(result).toMatchObject({ state: "error", data: null });
  });

  it("reports the live plane as degraded without touching the registry", async () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);

    const result = await getLiveAgentRegistry({ ...viewer, planeReady: false });

    expect(result).toMatchObject({ state: "degraded", data: null });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("maps lifecycle, egress and optional replica metadata from the registry", async () => {
    process["env"]["DISTRESSLENS_SOURCE_SHA"] = "f".repeat(40);
    process["env"]["DISTRESSLENS_GITOPS_SHA"] = "a".repeat(40);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            agents: [
              { name: "retired", version: "1", status: "retired", modelConfig: "model" },
              { name: "candidate", version: "1", status: "candidate", modelConfig: "model" },
              { name: "draft", version: "1", status: "draft", modelConfig: "model" },
              {
                name: "healthy",
                version: "1",
                status: "active",
                modelConfig: "model",
                tool: "feature.lookup",
                specialists: ["feature-agent", 3, ""],
                maxHops: 3,
                replicas: { min: 2, ready: 2, lastHeartbeatAt: "2026-08-10T00:00:00Z" },
              },
            ],
          }),
          { status: 200 },
        ),
      ),
    );

    const result = await getLiveAgentRegistry(viewer);

    expect(result.state).toBe("success");
    if (result.state !== "success") return;
    expect(result.data.entries.map((entry) => entry.lifecycle)).toEqual([
      "RETIRED",
      "CANDIDATE",
      "DRAFT",
      "PRODUCTION",
    ]);
    expect(result.data.entries[3]).toMatchObject({
      sandbox: {
        allowedEgress: ["feature.lookup", "feature-agent"],
        maxToolCallsPerRequest: 3,
      },
      replicas: { desired: 2, ready: 2, lastHeartbeatAt: "2026-08-10T00:00:00Z" },
    });
  });

  it("returns an error for malformed payloads, HTTP failures and invalid provenance", async () => {
    process["env"]["DISTRESSLENS_SOURCE_SHA"] = "not-a-sha";
    process["env"]["DISTRESSLENS_GITOPS_SHA"] = "a".repeat(40);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("no", { status: 500 })));
    await expect(getLiveAgentRegistry(viewer)).resolves.toMatchObject({ state: "error", data: null });

    process["env"]["DISTRESSLENS_SOURCE_SHA"] = "f".repeat(40);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ agents: {} }), { status: 200 })),
    );
    await expect(getLiveAgentRegistry(viewer)).resolves.toMatchObject({
      state: "error",
      data: null,
    });
  });

  it("rejects registry entries without required identity fields", async () => {
    process["env"]["DISTRESSLENS_SOURCE_SHA"] = "f".repeat(40);
    process["env"]["DISTRESSLENS_GITOPS_SHA"] = "a".repeat(40);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ agents: [{ name: "missing-version" }] }), { status: 200 }),
      ),
    );

    await expect(getLiveAgentRegistry(viewer)).resolves.toMatchObject({ state: "error", data: null });
  });

  it("returns an empty live result without inventing fixture entries", async () => {
    process["env"]["DISTRESSLENS_SOURCE_SHA"] = "f".repeat(40);
    process["env"]["DISTRESSLENS_GITOPS_SHA"] = "a".repeat(40);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ agents: [] }), { status: 200 })),
    );

    const result = await getLiveAgentRegistry(viewer);

    expect(result).toMatchObject({ state: "success", data: { entries: [] } });
  });
});
