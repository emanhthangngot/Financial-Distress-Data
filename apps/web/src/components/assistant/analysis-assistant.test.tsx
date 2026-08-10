import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AssistantContext } from "@/lib/assistant/assistant-context";
import { AnalysisAssistant } from "./analysis-assistant";

const CONTEXT: AssistantContext = {
  scope: "portfolio",
  route: "/",
  surfaceLabel: "Tổng quan",
  ticker: null,
  selectedTickers: [],
  periodLabel: null,
  filters: [],
  dataVersion: "v1",
  modelVersion: null,
};

describe("AnalysisAssistant", () => {
  it("mounts the launcher collapsed, wiring provider/launcher/panel together", () => {
    render(<AnalysisAssistant context={CONTEXT} />);

    expect(screen.getByRole("button", { name: "Mở trợ lý phân tích" })).toBeInTheDocument();
    // The panel renders nothing while collapsed — it is not a second, hidden
    // dialog sitting in the DOM.
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
