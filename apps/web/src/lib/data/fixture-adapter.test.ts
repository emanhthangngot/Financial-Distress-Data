import { describe, expect, it } from "vitest";
import { provenanceLabels, validateProvenance } from "@distresslens/contracts";
import { FIXTURE_REPORT_ID, FIXTURE_USER_ID, FixtureDataPort } from "./fixture-adapter";
import type { RequestContext } from "./port";

const port = new FixtureDataPort();

const analyst: RequestContext = {
  userId: FIXTURE_USER_ID,
  role: "analyst",
  aal: "aal1",
  planeReady: true,
};

const analystPlaneOff: RequestContext = { ...analyst, planeReady: false };

const viewer: RequestContext = {
  userId: "viewer-1",
  role: "platform_viewer",
  aal: "aal2",
  planeReady: true,
};

const signedOut: RequestContext = {
  userId: null,
  role: null,
  aal: "aal1",
  planeReady: true,
};

describe("analyst surfaces", () => {
  it("blocks a signed-out caller before any row is assembled", async () => {
    const result = await port.getAnalystOverview(signedOut);
    expect(result.state).toBe("forbidden");
    expect(result.state !== "success" && result.state !== "loading" && result.data).toBeNull();
  });

  it("blocks a platform_viewer from analyst content", async () => {
    expect((await port.getAnalystOverview(viewer)).state).toBe("forbidden");
    expect((await port.getCompanyDetail(viewer, "NVL")).state).toBe("forbidden");
  });

  it("serves the overview with valid provenance to an analyst", async () => {
    const result = await port.getAnalystOverview(analyst);
    expect(result.state).toBe("success");
    if (result.state !== "success") return;
    expect(validateProvenance(result.data.provenance)).toEqual([]);
    expect(result.data.attention).toHaveLength(8);
  });

  it("returns an empty state for an unknown ticker rather than a crash", async () => {
    const result = await port.getCompanyDetail(analyst, "ZZZ");
    expect(result.state).toBe("empty");
  });

  it("finds a company by ticker, name or sector", async () => {
    const byTicker = await port.searchCompanies(analyst, { query: "hpg", page: 1, pageSize: 10 });
    expect(byTicker.state).toBe("success");
    if (byTicker.state === "success") {
      expect(byTicker.data.rows[0]?.ticker).toBe("HPG");
    }

    const bySector = await port.searchCompanies(analyst, {
      query: "Bất động sản",
      page: 1,
      pageSize: 10,
    });
    expect(bySector.state === "success" && bySector.data.rows.length).toBe(2);
  });

  it("returns the empty state when nothing matches", async () => {
    const result = await port.searchCompanies(analyst, {
      query: "khongtontai",
      page: 1,
      pageSize: 10,
    });
    expect(result.state).toBe("empty");
  });
});

describe("EKS-off degradation", () => {
  it("labels a company page as cached and live-unavailable, never as live", async () => {
    const result = await port.getCompanyDetail(analystPlaneOff, "NVL");
    expect(result.state).toBe("degraded");
    if (result.state === "degraded") {
      expect(result.data).not.toBeNull();
      expect(provenanceLabels(result.data!.provenance)).toContain("CACHED_RESULT");
      expect(provenanceLabels(result.data!.provenance)).toContain("LIVE_UNAVAILABLE");
      expect(result.data!.provenance.cachedAt).not.toBeNull();
    }
  });

  it("never claims a live result while the plane is down", async () => {
    for (const result of [
      await port.getAnalystOverview(analystPlaneOff),
      await port.getCompanyDetail(analystPlaneOff, "NVL"),
      await port.getAgentConversation(analystPlaneOff, ""),
    ]) {
      if (result.state === "success" || result.state === "loading") {
        throw new Error("plane-off request must not resolve to a plain success state");
      }
      expect(validateProvenance(result.data!.provenance)).toEqual([]);
      expect(result.data!.provenance.planeAvailability).toBe("LIVE_UNAVAILABLE");
    }
  });

  it("reports replica readiness as unknown rather than zero when EKS is off", async () => {
    const result = await port.getAgentRegistry({ ...viewer, planeReady: false });
    expect(result.state).toBe("degraded");
    if (result.state === "degraded") {
      expect(result.data!.entries[0]?.replicas.lastHeartbeatAt).toBeNull();
    }
  });
});

describe("saved reports", () => {
  it("serves the owner their own report", async () => {
    const result = await port.getSavedReport(analyst, FIXTURE_REPORT_ID);
    expect(result.state).toBe("success");
  });

  it("gives the same answer for another user's report as for one that does not exist", async () => {
    const otherUser = await port.getSavedReport(
      { ...analyst, userId: "someone-else" },
      FIXTURE_REPORT_ID,
    );
    const missing = await port.getSavedReport(analyst, "rpt-does-not-exist");
    expect(otherUser.state).toBe("forbidden");
    expect(missing.state).toBe("forbidden");
    // Identical copy: a different message would confirm the report exists.
    expect(otherUser.state !== "success" && otherUser.state !== "loading" && otherUser.copy).toEqual(
      missing.state !== "success" && missing.state !== "loading" && missing.copy,
    );
  });
});

describe("operations surfaces", () => {
  it("lets a platform_viewer read the control room at AAL1", async () => {
    const result = await port.getOpsDashboard({ ...viewer, aal: "aal1" });
    expect(result.state).toBe("success");
  });

  it("blocks an analyst from the control room", async () => {
    expect((await port.getOpsDashboard(analyst)).state).toBe("forbidden");
    expect((await port.getAgentRegistry(analyst)).state).toBe("forbidden");
  });

  it("shows OFF with no session id when the plane is down", async () => {
    const result = await port.getOpsDashboard({ ...viewer, planeReady: false });
    expect(result.state).toBe("degraded");
    if (result.state === "degraded") {
      expect(result.data!.session.state).toBe("OFF");
      expect(result.data!.session.id).toBeNull();
    }
  });

  it("exposes a READY session with its full transition history", async () => {
    const result = await port.getOpsDashboard(viewer);
    if (result.state !== "success") throw new Error("expected success");
    expect(result.data.session.state).toBe("READY");
    expect(result.data.session.history).toHaveLength(4);
  });

  it("marks observability deep links unavailable when the plane is off", async () => {
    const result = await port.getOpsDashboard({ ...viewer, planeReady: false });
    if (result.state === "success" || result.state === "loading") throw new Error("expected degraded");
    const grafana = result.data!.observability.find((link) => link.label === "Xem Grafana");
    expect(grafana?.available).toBe(false);
  });
});

describe("agent surfaces", () => {
  it("carries citations and a tool trace with no prompt or credential text", async () => {
    const result = await port.getAgentConversation(analyst, "");
    if (result.state !== "success") throw new Error("expected success");
    const answer = result.data.messages.find((message) => message.role === "agent");
    expect(answer?.citations.length).toBeGreaterThan(0);
    expect(answer?.toolTrace.length).toBeGreaterThan(0);
    const serialized = JSON.stringify(result.data);
    expect(serialized).not.toMatch(/prompt|api[_-]?key|token|secret|password/i);
  });
});
