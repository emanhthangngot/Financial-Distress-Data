import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { RequestContext } from "@/lib/data/port";
import { DenialAction } from "./denial-action";

const guestContext: RequestContext = { userId: null, role: null, aal: "aal1", planeReady: true };
const signedInContext: RequestContext = {
  userId: "user-1",
  role: "analyst",
  aal: "aal1",
  planeReady: true,
};

describe("DenialAction", () => {
  it("shows a sign-in link for a guest's forbidden state", () => {
    render(<DenialAction state="forbidden" context={guestContext} reloadHref="/companies" />);

    expect(screen.getByRole("link", { name: "Đăng nhập" })).toHaveAttribute("href", "/sign-in");
  });

  it("shows a reload link for a signed-in user's forbidden state (role denial, not anonymity)", () => {
    render(<DenialAction state="forbidden" context={signedInContext} reloadHref="/companies" />);

    expect(screen.getByRole("link", { name: "Tải lại" })).toHaveAttribute("href", "/companies");
  });

  it("shows a reload link for a non-forbidden state even for a guest", () => {
    render(<DenialAction state="error" context={guestContext} reloadHref="/companies" />);

    expect(screen.getByRole("link", { name: "Tải lại" })).toHaveAttribute("href", "/companies");
  });
});
