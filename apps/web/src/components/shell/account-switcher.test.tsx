import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AccountSwitcher } from "./account-switcher";

describe("AccountSwitcher", () => {
  it("renders nothing for an empty account list", () => {
    const { container } = render(<AccountSwitcher accounts={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders one entry per account with its role label", () => {
    render(
      <AccountSwitcher
        accounts={[
          { email: "analyst@distresslens.local", role: "analyst", label: "Analyst demo" },
          { email: "admin@distresslens.local", role: "platform_admin", label: "Admin demo" },
        ]}
      />,
    );

    expect(screen.getByText("Analyst demo")).toBeInTheDocument();
    expect(screen.getByText("Chuyên viên phân tích")).toBeInTheDocument();
    expect(screen.getByText("Admin demo")).toBeInTheDocument();
    expect(screen.getByText("Quản trị viên")).toBeInTheDocument();
  });
});
