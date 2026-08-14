import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));

const { resolveSession, update, eq, from, createRequestClient } = vi.hoisted(() => {
  const eq = vi.fn().mockResolvedValue({ error: null });
  const update = vi.fn(() => ({ eq }));
  const from = vi.fn(() => ({ update }));
  return {
    resolveSession: vi.fn(),
    update,
    eq,
    from,
    createRequestClient: vi.fn(() => ({ from })),
  };
});

vi.mock("./session", () => ({ resolveSession }));
vi.mock("./supabase", () => ({ createRequestClient }));

import { updateDisplayName } from "./profile-actions";

function formWith(displayName: string): FormData {
  const form = new FormData();
  form.set("displayName", displayName);
  return form;
}

describe("updateDisplayName", () => {
  beforeEach(() => {
    update.mockClear();
    eq.mockClear();
    from.mockClear();
    resolveSession.mockReset();
    resolveSession.mockResolvedValue({
      context: { userId: "user-1", role: "analyst", aal: "aal1", planeReady: true },
      accessToken: "token-abc",
      user: { displayName: "Old Name", role: "analyst" },
    });
  });

  it("rejects an empty display name without touching the database", async () => {
    const result = await updateDisplayName({ ok: false, message: "" }, formWith("   "));

    expect(result.ok).toBe(false);
    expect(from).not.toHaveBeenCalled();
  });

  it("rejects a guest session", async () => {
    resolveSession.mockResolvedValue({
      context: { userId: null, role: null, aal: "aal1", planeReady: true },
      accessToken: null,
      user: { displayName: "Khách", role: null },
    });

    const result = await updateDisplayName({ ok: false, message: "" }, formWith("New Name"));

    expect(result.ok).toBe(false);
    expect(from).not.toHaveBeenCalled();
  });

  it("writes only display_name, never role, and scopes the update to the caller's own row", async () => {
    const result = await updateDisplayName({ ok: false, message: "" }, formWith("New Name"));

    expect(result.ok).toBe(true);
    expect(update).toHaveBeenCalledWith({ display_name: "New Name" });
    expect(update).not.toHaveBeenCalledWith(expect.objectContaining({ role: expect.anything() }));
    expect(eq).toHaveBeenCalledWith("user_id", "user-1");
  });

  it("returns a generic failure message when the database write errors", async () => {
    eq.mockResolvedValueOnce({ error: { message: "permission denied for table profiles" } });

    const result = await updateDisplayName({ ok: false, message: "" }, formWith("New Name"));

    expect(result.ok).toBe(false);
    expect(result.message).not.toContain("permission denied");
  });
});
