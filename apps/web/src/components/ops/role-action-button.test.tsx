import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { requestSessionTransition } from "@/lib/server/session-actions";
import { RoleActionButton } from "./role-action-button";

vi.mock("@/lib/server/session-actions", () => ({
  requestSessionTransition: vi.fn(),
}));

const mockedTransition = vi.mocked(requestSessionTransition);

describe("RoleActionButton", () => {
  it("disables the control for a role the action denies", () => {
    render(
      <RoleActionButton action="session.provision" role="platform_viewer" aal="aal2" label="Cấp phát" />,
    );

    const button = screen.getByRole("button", { name: "Cấp phát" });
    expect(button).toBeDisabled();
  });

  it("enables the control for a role the action allows at AAL2", () => {
    render(
      <RoleActionButton
        action="session.provision"
        role="platform_operator"
        aal="aal2"
        label="Cấp phát"
        transition={{ targetState: "REQUESTED", sessionId: "s1", fencingToken: "t1" }}
      />,
    );

    expect(screen.getByRole("button", { name: "Cấp phát" })).toBeEnabled();
  });

  it("disables an otherwise-allowed control for a cost-cap denial and shows the reason", () => {
    render(
      <RoleActionButton
        action="session.provision"
        role="platform_operator"
        aal="aal2"
        label="Cấp phát"
        blockedReason="Vượt trần chi phí tháng này."
      />,
    );

    const button = screen.getByRole("button", { name: "Cấp phát" });
    expect(button).toBeDisabled();
    expect(screen.getByText("Vượt trần chi phí tháng này.")).toBeInTheDocument();
  });

  it("exposes the disabled reason to assistive technology via aria-describedby", () => {
    render(
      <RoleActionButton action="session.provision" role="platform_viewer" aal="aal2" label="Cấp phát" />,
    );

    const button = screen.getByRole("button", { name: "Cấp phát" });
    const describedBy = button.getAttribute("aria-describedby");
    expect(describedBy).not.toBeNull();
    expect(document.getElementById(describedBy as string)).not.toBeNull();
  });

  it("stays enabled at AAL1 under the demo-environment step-up relaxation", () => {
    // STEP_UP_REQUIRED = false in @distresslens/contracts; see its doc comment
    // for the revert path.
    render(
      <RoleActionButton
        action="session.provision"
        role="platform_operator"
        aal="aal1"
        label="Cấp phát"
        transition={{ targetState: "REQUESTED", sessionId: "s1", fencingToken: "t1" }}
      />,
    );

    expect(screen.getByRole("button", { name: "Cấp phát" })).toBeEnabled();
  });

  it("renders a plain enabled control for an action that is not a state transition", () => {
    render(
      <RoleActionButton
        action="session.export_evidence"
        role="platform_operator"
        aal="aal2"
        label="Xuất evidence"
      />,
    );

    expect(screen.getByRole("button", { name: "Xuất evidence" })).toBeEnabled();
  });

  it("submits the transition and shows the server action's result message", async () => {
    mockedTransition.mockResolvedValue({ ok: true, message: "Đã gửi yêu cầu cấp phát." });
    const user = userEvent.setup();

    render(
      <RoleActionButton
        action="session.provision"
        role="platform_operator"
        aal="aal2"
        label="Cấp phát"
        transition={{ targetState: "REQUESTED", sessionId: "s1", fencingToken: "t1" }}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Cấp phát" }));

    await waitFor(() =>
      expect(screen.getByText("Đã gửi yêu cầu cấp phát.")).toBeInTheDocument(),
    );
    expect(mockedTransition).toHaveBeenCalled();
  });

  it("shows a failed transition's message with the error tone", async () => {
    mockedTransition.mockResolvedValue({ ok: false, message: "Fencing token đã cũ." });
    const user = userEvent.setup();

    render(
      <RoleActionButton
        action="session.provision"
        role="platform_operator"
        aal="aal2"
        label="Cấp phát"
        transition={{ targetState: "REQUESTED", sessionId: "s1", fencingToken: "t1" }}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Cấp phát" }));

    await waitFor(() => {
      const message = screen.getByText("Fencing token đã cũ.");
      expect(message).toHaveClass("text-risk-high-ink");
    });
  });
});
