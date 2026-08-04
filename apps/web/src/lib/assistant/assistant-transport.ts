import type { AgentMessageState, Citation, ToolTraceEntry } from "@distresslens/contracts";
import type { AssistantContext } from "./assistant-context";

/**
 * The boundary between the assistant UI and whatever answers it.
 *
 * Phase 2 has not shipped the agent request path yet: there is no route handler
 * that authorises a request, enforces the AI quota and streams from the
 * evidence plane. Rather than fake an answer, the UI talks to this interface
 * and the default implementation reports the integration as missing, with the
 * state the real transport will use when it lands.
 *
 * When the backend arrives, implement `AssistantTransport` against the route
 * handler and pass it to the provider. No component changes.
 */

export interface AssistantTurn {
  id: string;
  role: "user" | "assistant";
  body: string;
  createdAt: string;
  state: AgentMessageState | "unavailable";
  citations: readonly Citation[];
  toolTrace: readonly ToolTraceEntry[];
  agentVersion: string | null;
  modelVersion: string | null;
  /** Rendered under a non-complete answer to say what to do next. */
  nextAction: string | null;
}

export interface AssistantRequest {
  context: AssistantContext;
  question: string;
  /** Prior turns in this thread, oldest first. */
  history: readonly AssistantTurn[];
}

export interface AssistantTransport {
  send(request: AssistantRequest): Promise<AssistantTurn>;
}

/**
 * The transport used until the agent request path exists.
 *
 * It answers honestly: the question was recorded, no model ran, and here is
 * what the analyst can do instead. It never invents an analysis, because a
 * plausible-looking fabricated risk explanation is the single worst failure
 * this product can ship.
 */
export const UNAVAILABLE_TRANSPORT: AssistantTransport = {
  async send({ question }): Promise<AssistantTurn> {
    return {
      id: `turn-${Date.now()}`,
      role: "assistant",
      body: "Dịch vụ phân tích chưa được kết nối trong bản dựng này, nên câu hỏi chưa được gửi tới mô hình.",
      createdAt: new Date().toISOString(),
      state: "unavailable",
      citations: [],
      toolTrace: [],
      agentVersion: null,
      modelVersion: null,
      nextAction:
        question.trim() === ""
          ? "Nhập câu hỏi về doanh nghiệp hoặc danh mục đang xem."
          : "Xem số liệu và nguồn dữ liệu ngay trên trang, hoặc mở báo cáo đã lưu.",
    };
  },
};
