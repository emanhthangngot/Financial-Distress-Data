import { once } from "node:events";
import { createServer } from "node:http";
import { promisify } from "node:util";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getLiveAgentRegistry } from "./live-registry-adapter";

const viewer = {
  userId: "platform-viewer",
  role: "platform_viewer" as const,
  aal: "aal2" as const,
  planeReady: true,
};

const envKeys = [
  "DISTRESSLENS_AGENT_REGISTRY_URL",
  "DISTRESSLENS_AGENT_REGISTRY_TOKEN",
  "DISTRESSLENS_SOURCE_SHA",
  "DISTRESSLENS_GITOPS_SHA",
  "DISTRESSLENS_LIVE_PLANE",
];

beforeEach(() => {
  process["env"]["DISTRESSLENS_AGENT_REGISTRY_URL"] = "https://registry.example.test/region/v1/agents";
  process["env"]["DISTRESSLENS_SOURCE_SHA"] = "f".repeat(40);
  process["env"]["DISTRESSLENS_GITOPS_SHA"] = "a".repeat(40);
  delete process["env"]["DISTRESSLENS_AGENT_REGISTRY_TOKEN"];
});

afterEach(() => {
  vi.unstubAllGlobals();
  for (const key of envKeys) delete process["env"][key];
});

describe("live agent registry adapter", () => {
  it("maps the GitOps registry and stamps evidence-plane provenance", async () => {
    process["env"]["DISTRESSLENS_AGENT_REGISTRY_TOKEN"] = "test-registry-token";
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
                replicas: { min: 2, max: 3, ready: 0 },
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

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "https://registry.example.test/region/v1/agents",
      expect.objectContaining({
        cache: "no-store",
        redirect: "error",
        headers: { accept: "application/json", Authorization: "Bearer test-registry-token" },
      }),
    );
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
      sourceSha: "f".repeat(40),
      gitopsSha: "a".repeat(40),
    });
  });

  it("degrades without fetching when production live reads are disabled", async () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    await expect(getLiveAgentRegistry(viewer, false)).resolves.toMatchObject({
      state: "degraded",
      data: null,
    });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("uses the loopback registry HTTP transport without requiring a token", async () => {
    const seen: [string | undefined, string | undefined][] = [];
    const server = createServer((request, response) => {
      seen.push([request.url, request.headers.authorization]);
      response.writeHead(200, { "content-type": "application/json", connection: "close" });
      response.end(JSON.stringify({
        agents: [{ name: "coordinator", version: "1.0.0", modelConfig: "portable-model" }],
      }));
    });
    server.listen(0, "127.0.0.1");
    try {
      await once(server, "listening");
      const address = server.address();
      if (address === null || typeof address === "string") throw new Error("no test TCP address");
      process["env"]["DISTRESSLENS_AGENT_REGISTRY_URL"] =
        `http://127.0.0.1:${address.port}/registry/v1/agents`;

      await expect(getLiveAgentRegistry(viewer)).resolves.toMatchObject({
        state: "success",
        data: { entries: [{
          id: "coordinator",
          modelVersion: "portable-model",
          replicas: { desired: null, ready: null, lastHeartbeatAt: null },
        }] },
      });
      expect(seen).toEqual([["/registry/v1/agents", undefined]]);
    } finally {
      if (server.listening) await promisify(server.close).call(server);
    }
  });

  it("degrades without touching the network when the registry URL is unset", async () => {
    delete process["env"]["DISTRESSLENS_AGENT_REGISTRY_URL"];
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);

    await expect(getLiveAgentRegistry(viewer)).resolves.toMatchObject({ state: "degraded", data: null });
    expect(fetch).not.toHaveBeenCalled();
  });

  it.each([
    ["DISTRESSLENS_AGENT_REGISTRY_URL", "https://regional.example.test:invalid/v1/agents"],
    ["DISTRESSLENS_AGENT_REGISTRY_URL", "https://user:secret@regional.example.test/v1/agents"],
    ["DISTRESSLENS_AGENT_REGISTRY_TOKEN", "bad token"],
    ["DISTRESSLENS_SOURCE_SHA", "not-a-sha"],
    ["DISTRESSLENS_GITOPS_SHA", ""],
  ])("refuses invalid %s without fetching or falling back", async (key, value) => {
    process["env"][key] = value;
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);

    await expect(getLiveAgentRegistry(viewer)).resolves.toMatchObject({ state: "error", data: null });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("preserves live provenance when the registry has no GitOps control repository", async () => {
    delete process["env"]["DISTRESSLENS_GITOPS_SHA"];
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ agents: [] })));
    await expect(getLiveAgentRegistry(viewer)).resolves.toMatchObject({
      state: "success",
      data: { provenance: { sourceSha: "f".repeat(40), gitopsSha: null } },
    });
  });

  it.each([
    { userId: null, role: null },
    { userId: "signed-in-analyst", role: "analyst" as const },
  ])("does not fetch on behalf of unauthorized callers (%j)", async (caller) => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    await expect(getLiveAgentRegistry({ ...viewer, ...caller })).resolves.toMatchObject({
      state: "forbidden",
      data: null,
    });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("does not send a registry token over non-loopback HTTP", async () => {
    process["env"]["DISTRESSLENS_AGENT_REGISTRY_URL"] = "http://external.example.test/v1/agents";
    process["env"]["DISTRESSLENS_AGENT_REGISTRY_TOKEN"] = "test-token";
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    await expect(getLiveAgentRegistry(viewer)).resolves.toMatchObject({ state: "error", data: null });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("returns an error instead of serving fixtures when the registry is unreachable", async () => {
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

  it("returns an error for malformed payloads and HTTP failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("no", { status: 500 })));
    await expect(getLiveAgentRegistry(viewer)).resolves.toMatchObject({ state: "error", data: null });

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
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ agents: [{ name: "missing-version" }] }), { status: 200 }),
      ),
    );

    await expect(getLiveAgentRegistry(viewer)).resolves.toMatchObject({ state: "error", data: null });
  });

  it("returns an empty live result without inventing fixture entries", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ agents: [] }), { status: 200 })),
    );

    const result = await getLiveAgentRegistry(viewer);

    expect(result).toMatchObject({ state: "success", data: { entries: [] } });
  });
});
