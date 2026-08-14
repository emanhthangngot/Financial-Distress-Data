import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { UserMenu } from "./user-menu";

vi.mock("@/lib/server/profile-actions", () => ({
  updateDisplayName: vi.fn(),
}));

describe("UserMenu", () => {
  it("renders a sign-in / sign-up pair for a guest instead of an account menu", () => {
    render(<UserMenu displayName="Khách" role={null} />);

    expect(screen.getByRole("link", { name: "Đăng nhập" })).toHaveAttribute("href", "/sign-in");
    expect(screen.getByRole("link", { name: "Đăng ký" })).toHaveAttribute("href", "/sign-up");
    expect(screen.queryByText("Mở menu tài khoản")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Đăng xuất" })).not.toBeInTheDocument();
  });

  it("renders the account menu with role label and sign-out for a signed-in user", () => {
    render(<UserMenu displayName="Nguyễn Minh Anh" role="analyst" />);

    expect(screen.queryByRole("link", { name: "Đăng nhập" })).not.toBeInTheDocument();
    expect(screen.getByText("Chuyên viên phân tích")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Đăng xuất/ })).toHaveAttribute("href", "/sign-out");
  });

  it("renders no account switcher section when no demo accounts are configured", () => {
    render(<UserMenu displayName="Nguyễn Minh Anh" role="analyst" demoAccounts={[]} />);

    expect(screen.queryByText("Chuyển hồ sơ")).not.toBeInTheDocument();
  });

  it("lists demo accounts with a link that signs out and prefills the next sign-in", () => {
    render(
      <UserMenu
        displayName="Nguyễn Minh Anh"
        role="analyst"
        demoAccounts={[
          { email: "operator@distresslens.local", role: "platform_operator", label: "Operator demo" },
        ]}
      />,
    );

    expect(screen.getByText("Chuyển hồ sơ")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /Operator demo/ });
    expect(link.getAttribute("href")).toBe(
      "/sign-out?next=%2Fsign-in%3Femail%3Doperator%2540distresslens.local",
    );
  });
});
