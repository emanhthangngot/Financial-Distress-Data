import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DISCLAIMER_SURFACES, DISCLAIMER_TEXT } from "@distresslens/contracts";
import { DisclaimerBanner } from "./disclaimer-banner";

describe("DisclaimerBanner", () => {
  it.each(DISCLAIMER_SURFACES)("renders the disclaimer text on the %s surface", (surface) => {
    render(<DisclaimerBanner surface={surface} />);

    expect(screen.getByText(DISCLAIMER_TEXT)).toBeInTheDocument();
  });

  it("renders as a landmark aside in the block variant", () => {
    render(<DisclaimerBanner surface="company" />);

    expect(screen.getByRole("complementary")).toHaveTextContent(DISCLAIMER_TEXT);
  });

  it("renders as inline text carrying the surface, not a landmark, in the inline variant", () => {
    render(<DisclaimerBanner surface="agent_chat" variant="inline" />);

    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    expect(screen.getByText(DISCLAIMER_TEXT)).toHaveAttribute(
      "data-disclaimer-surface",
      "agent_chat",
    );
  });
});
