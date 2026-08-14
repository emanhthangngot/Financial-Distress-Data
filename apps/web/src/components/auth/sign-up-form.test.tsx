import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { signUp } from "@/lib/server/sign-up-action";
import { SignUpForm } from "./sign-up-form";

vi.mock("@/lib/server/sign-up-action", () => ({
  signUp: vi.fn(),
}));

const mockedSignUp = vi.mocked(signUp);

describe("SignUpForm", () => {
  it("blocks submission and shows an inline error when the passwords do not match", async () => {
    mockedSignUp.mockClear();
    const user = userEvent.setup();

    render(<SignUpForm />);

    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.type(screen.getByLabelText("Mật khẩu"), "correct-horse");
    await user.type(screen.getByLabelText("Xác nhận mật khẩu"), "different-horse");
    await user.click(screen.getByRole("button", { name: "Đăng ký" }));

    expect(await screen.findByText("Mật khẩu xác nhận không khớp.")).toBeInTheDocument();
    expect(mockedSignUp).not.toHaveBeenCalled();
  });

  it("exposes a display-name field marked optional", () => {
    render(<SignUpForm />);

    expect(screen.getByLabelText(/Tên hiển thị/)).toBeInTheDocument();
  });
});
