import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DISCLAIMER_TEXT } from "@distresslens/contracts";
import type { AssistantTransport, AssistantTurn } from "@/lib/assistant/assistant-transport";
import type { AssistantContext } from "@/lib/assistant/assistant-context";
import { AssistantProvider } from "./assistant-provider";
import { AssistantLauncher } from "./assistant-launcher";
import { AssistantPanel } from "./assistant-panel";

const CONTEXT: AssistantContext = {
  scope: "company",
  route: "/companies/ACME",
  surfaceLabel: "ACME",
  ticker: "ACME",
  selectedTickers: [],
  periodLabel: "30 ngày",
  filters: [],
  dataVersion: "v1",
  modelVersion: "m1",
};

function turnWithState(state: AssistantTurn["state"], overrides: Partial<AssistantTurn> = {}): AssistantTurn {
  return {
    id: `turn-${state}`,
    role: "assistant",
    body: `Câu trả lời ở trạng thái ${state}`,
    createdAt: new Date().toISOString(),
    state,
    citations: [],
    toolTrace: [],
    agentVersion: null,
    modelVersion: null,
    nextAction: null,
    ...overrides,
  };
}

function stubTransport(turn: AssistantTurn): { transport: AssistantTransport; abort: ReturnType<typeof vi.fn> } {
  const abort = vi.fn();
  const transport: AssistantTransport = {
    send: vi.fn().mockResolvedValue(turn),
    abort,
  };
  return { transport, abort };
}

async function openPanel(transport: AssistantTransport, quotaRemaining: number | null = null) {
  const user = userEvent.setup();
  render(
    <AssistantProvider context={CONTEXT} transport={transport} quotaRemaining={quotaRemaining}>
      <AssistantLauncher />
      <AssistantPanel />
    </AssistantProvider>,
  );
  await user.click(screen.getByRole("button", { name: "Mở trợ lý phân tích" }));
  return user;
}

async function ask(user: ReturnType<typeof userEvent.setup>, question: string) {
  const input = screen.getByLabelText("Câu hỏi cho trợ lý phân tích");
  await user.type(input, question);
  await user.click(screen.getByRole("button", { name: "Gửi câu hỏi" }));
}

const STATE_LABEL: Record<string, string> = {
  streaming: "Đang trả lời",
  tool_running: "Đang truy vấn dữ liệu",
  timeout: "Quá thời gian chờ",
  policy_blocked: "Bị chính sách chặn",
  unavailable: "Chưa kết nối dịch vụ",
  error: "Lỗi",
};

describe("AssistantPanel", () => {
  it.each(Object.entries(STATE_LABEL))(
    "renders the state copy for a %s answer",
    async (state, label) => {
      const { transport } = stubTransport(turnWithState(state as AssistantTurn["state"]));
      const user = await openPanel(transport);

      await ask(user, "Vì sao điểm rủi ro tăng?");

      await waitFor(() => expect(screen.getByText(label)).toBeInTheDocument());
    },
  );

  it("renders the disclaimer under a complete answer", async () => {
    const { transport } = stubTransport(turnWithState("complete"));
    const user = await openPanel(transport);

    await ask(user, "Vì sao điểm rủi ro tăng?");

    await waitFor(() => expect(screen.getAllByText(DISCLAIMER_TEXT).length).toBeGreaterThan(0));
  });

  it("shows the quota line when the port reports remaining budget", async () => {
    const { transport } = stubTransport(turnWithState("complete"));
    await openPanel(transport, 7);

    expect(screen.getByText("Còn 7 lượt phân tích AI")).toBeInTheDocument();
  });

  it("hides the quota line when the port reports no budget state", async () => {
    const { transport } = stubTransport(turnWithState("complete"));
    await openPanel(transport, null);

    expect(screen.queryByText(/lượt phân tích AI/)).not.toBeInTheDocument();
  });

  it("calls the transport's abort when the analyst cancels a pending question", async () => {
    let resolveSend: (turn: AssistantTurn) => void = () => {};
    const abort = vi.fn();
    const transport: AssistantTransport = {
      send: vi.fn().mockImplementation(
        () =>
          new Promise<AssistantTurn>((resolve) => {
            resolveSend = resolve;
          }),
      ),
      abort,
    };

    const user = await openPanel(transport);
    await ask(user, "Câu hỏi đang chờ trả lời");

    const cancelButton = await screen.findByRole("button", { name: "Dừng trợ lý" });
    await user.click(cancelButton);

    expect(abort).toHaveBeenCalledTimes(1);

    // Let the in-flight promise settle so it does not leak into another test.
    resolveSend(turnWithState("complete"));
  });

  it("renders citations, tool trace and version info on a complete answer", async () => {
    const { transport } = stubTransport(
      turnWithState("complete", {
        agentVersion: "agent-1",
        modelVersion: "model-1",
        citations: [
          { sourceId: "src-1", ordinal: 1, title: "Báo cáo tài chính Q3", publisher: "ACME", url: "https://example.com" },
          { sourceId: "src-2", ordinal: 2, title: "Ghi chú nội bộ", publisher: "ACME", url: null },
        ],
        toolTrace: [
          {
            id: "tool-1",
            toolName: "search_filings",
            status: "SUCCEEDED",
            summary: "Tra cứu hồ sơ",
            startedAt: new Date().toISOString(),
            durationMs: 120,
          },
        ],
      }),
    );
    const user = await openPanel(transport);

    await ask(user, "Nguồn nào cho kết luận này?");

    await waitFor(() => expect(screen.getByText("Báo cáo tài chính Q3")).toBeInTheDocument());
    expect(screen.getByText("Ghi chú nội bộ")).toBeInTheDocument();
    expect(screen.getByText("search_filings")).toBeInTheDocument();
    expect(screen.getByText("agent-1 · model-1")).toBeInTheDocument();
  });

  it("shows a recovery message when the transport rejects", async () => {
    const transport: AssistantTransport = {
      send: vi.fn().mockRejectedValue(new Error("network error")),
    };
    const user = await openPanel(transport);

    await ask(user, "Câu hỏi sẽ thất bại");

    await waitFor(() =>
      expect(
        screen.getByText("Không gửi được câu hỏi tới trợ lý phân tích."),
      ).toBeInTheDocument(),
    );
  });

  it("closes on Escape and returns focus to the launcher", async () => {
    const { transport } = stubTransport(turnWithState("complete"));
    const user = await openPanel(transport);

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mở trợ lý phân tích" })).toHaveFocus();
  });

  it("expands and collapses back via the panel control", async () => {
    const { transport } = stubTransport(turnWithState("complete"));
    const user = await openPanel(transport);

    await user.click(screen.getByRole("button", { name: "Phóng to trợ lý" }));
    expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");

    await user.click(screen.getByRole("button", { name: "Thu nhỏ trợ lý" }));
    expect(screen.getByRole("dialog")).not.toHaveAttribute("aria-modal");
  });

  it("does not lock page scroll for a docked panel on a desktop-width viewport", async () => {
    const originalMatchMedia = window.matchMedia;
    window.matchMedia = (query: string) =>
      ({
        matches: true,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as MediaQueryList;

    try {
      const { transport } = stubTransport(turnWithState("complete"));
      await openPanel(transport);

      expect(document.body.classList.contains("scroll-locked")).toBe(false);
    } finally {
      window.matchMedia = originalMatchMedia;
    }
  });
});
