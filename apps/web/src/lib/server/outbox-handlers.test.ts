import { describe, expect, it } from "vitest";
import type { OutboxEventRow } from "./outbox-worker";
import {
  NoOutboxHandlerError,
  createDefaultOutboxHandlerRegistry,
  createOutboxHandlerRegistry,
  noInfrastructureHandler,
} from "./outbox-handlers";

function event(overrides: Partial<OutboxEventRow> = {}): OutboxEventRow {
  return {
    id: "event-1",
    session_id: "session-1",
    target_state: "REQUESTED",
    attempts: 0,
    fencing_token: "token-1",
    ...overrides,
  };
}

describe("createOutboxHandlerRegistry", () => {
  it("dispatches a registered state to its handler", async () => {
    const registry = createOutboxHandlerRegistry();
    registry.register("PROVISIONING", async () => "provisioned");

    await expect(registry.handle(event({ target_state: "PROVISIONING" }))).resolves.toBe(
      "provisioned",
    );
  });

  it("throws a named error for an unregistered target state", async () => {
    const registry = createOutboxHandlerRegistry();

    await expect(registry.handle(event({ target_state: "SYNCING" }))).rejects.toBeInstanceOf(
      NoOutboxHandlerError,
    );
  });

  it("names the unhandled state in the error message", async () => {
    const registry = createOutboxHandlerRegistry();

    await expect(registry.handle(event({ target_state: "CAPTURING" }))).rejects.toThrow(
      /CAPTURING/,
    );
  });
});

describe("noInfrastructureHandler", () => {
  it("states no infrastructure was contacted and names the target state", async () => {
    const result = await noInfrastructureHandler(event({ target_state: "DESTROYING" }));

    expect(result).toMatch(/no infrastructure contacted/);
    expect(result).toMatch(/DESTROYING/);
  });
});

describe("createDefaultOutboxHandlerRegistry", () => {
  it("registers the placeholder for every lifecycle target state", async () => {
    const registry = createDefaultOutboxHandlerRegistry();

    for (const target of [
      "REQUESTED",
      "PROVISIONING",
      "SYNCING",
      "CAPTURING",
      "DESTROYING",
    ] as const) {
      await expect(registry.handle(event({ target_state: target }))).resolves.toMatch(
        /no infrastructure contacted/,
      );
    }
  });
});
