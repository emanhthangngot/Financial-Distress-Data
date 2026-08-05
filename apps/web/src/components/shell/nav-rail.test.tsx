import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { NavRail, type NavGroup } from "./nav-rail";

vi.mock("next/navigation", () => ({
  usePathname: () => "/companies",
}));

const ANALYST_GROUPS: readonly NavGroup[] = [
  {
    label: "Phân tích",
    items: [
      { label: "Tổng quan", href: "/", icon: null },
      { label: "Doanh nghiệp", href: "/companies", icon: null },
      { label: "So sánh", href: null, icon: null, unavailableNote: "Sắp có" },
    ],
  },
];

const PLATFORM_GROUPS: readonly NavGroup[] = [
  {
    label: "Vận hành",
    items: [{ label: "Evidence", href: "/ops/evidence", icon: null }],
  },
];

describe("NavRail", () => {
  it("renders only the items passed to it — an analyst rail never carries platform items", () => {
    render(<NavRail groups={ANALYST_GROUPS} label="Điều hướng phân tích" />);

    expect(screen.getByRole("link", { name: "Doanh nghiệp" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Evidence" })).not.toBeInTheDocument();
  });

  it("renders only the items passed to it — a platform rail never carries analyst items", () => {
    render(<NavRail groups={PLATFORM_GROUPS} label="Điều hướng vận hành" />);

    expect(screen.getByRole("link", { name: "Evidence" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Doanh nghiệp" })).not.toBeInTheDocument();
  });

  it("marks the active route with aria-current", () => {
    render(<NavRail groups={ANALYST_GROUPS} label="Điều hướng phân tích" />);

    expect(screen.getByRole("link", { name: "Doanh nghiệp" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Tổng quan" })).not.toHaveAttribute("aria-current");
  });

  it("renders an unshipped item as disabled, not as a 404-bound link", () => {
    render(<NavRail groups={ANALYST_GROUPS} label="Điều hướng phân tích" />);

    expect(screen.queryByRole("link", { name: /So sánh/ })).not.toBeInTheDocument();
    const disabled = screen.getByText("So sánh").closest("[aria-disabled]");
    expect(disabled).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText("Sắp có")).toBeInTheDocument();
  });

  it("renders a disabled item with no note when none is given", () => {
    render(
      <NavRail
        groups={[{ label: "Phân tích", items: [{ label: "Sổ đăng ký", href: null, icon: null }] }]}
        label="Điều hướng phân tích"
      />,
    );

    expect(screen.getByText("Sổ đăng ký").closest("[aria-disabled]")).toBeInTheDocument();
  });

  it("renders an unlabelled group without a section heading", () => {
    render(
      <NavRail
        groups={[{ label: null, items: [{ label: "Tổng quan", href: "/", icon: null }] }]}
        label="Điều hướng phân tích"
      />,
    );

    expect(screen.queryByRole("heading")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Tổng quan" })).toBeInTheDocument();
  });

  it("renders footer items in their own group", () => {
    render(
      <NavRail
        groups={ANALYST_GROUPS}
        footerItems={[{ label: "Cài đặt", href: "/settings", icon: null }]}
        label="Điều hướng phân tích"
      />,
    );

    expect(screen.getByRole("link", { name: "Cài đặt" })).toBeInTheDocument();
  });
});
