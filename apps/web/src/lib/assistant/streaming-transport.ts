import {
  decodeSseChunk,
  encodeSseFrame,
  type AgentMessageState,
  type AssistantFrame,
  type Citation,
  type ToolTraceEntry,
} from "@distresslens/contracts";
import type {
  AssistantRequest,
  AssistantTransport,
  AssistantTurn,
} from "./assistant-transport";

/**
 * The streaming assistant transport: one POST to the assistant stream route,
 * frames parsed with the shared codec and reduced into the `AssistantTurn` the
 * UI already renders.
 *
 * Deliberately a separate module from the provider: the provider keeps its
 * current API, and the transport is unit-tested against a fake `fetch` without
 * a React tree. The request body carries only question, history and context —
 * never a token, because nothing the transport knows is a credential.
 *
 * A client-side deadline aborts the request independent of the server's, so a
 * broken route cannot hang the panel past the analyst's patience.
 */

/** Independent of the server's `ASSISTANT_TIMEOUT_MS`; the UI gives up first. */
export const ASSISTANT_CLIENT_TIMEOUT_MS = 90_000;

const EKS_OFF_BODY =
  "Các chỉ số và nguồn dữ liệu vẫn khả dụng, phân tích AI trực tiếp tạm chưa bật.";
const EKS_OFF_NEXT_ACTION = "Xem số liệu và nguồn dữ liệu ngay trên trang.";
const TIMEOUT_BODY = "Trợ lý không trả lời trong thời gian cho phép.";
const TIMEOUT_NEXT_ACTION = "Hỏi lại với phạm vi hẹp hơn, hoặc thử lại sau ít phút.";
const ERROR_BODY = "Không gửi được yêu cầu tới trợ lý phân tích.";
const ERROR_NEXT_ACTION = "Thử lại. Nếu lặp lại, xem trạng thái hệ thống ở trang Vận hành.";

export class StreamingAssistantTransport implements AssistantTransport {
  private controller: AbortController | null = null;

  constructor(private readonly endpoint: string) {}

  /** Cancel the in-flight request. No-op when idle. */
  abort(): void {
    this.controller?.abort();
  }

  async send(request: AssistantRequest): Promise<AssistantTurn> {
    const controller = new AbortController();
    this.controller = controller;
    const timer = setTimeout(() => controller.abort(), ASSISTANT_CLIENT_TIMEOUT_MS);

    try {
      const response = await fetch(this.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: request.question,
          history: request.history,
          context: request.context,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        return await this.reduceNonOk(response);
      }
      return await this.reduceStream(response, controller.signal);
    } catch {
      const aborted = controller.signal.aborted;
      return this.turn(
        aborted ? "timeout" : "error",
        aborted ? TIMEOUT_BODY : ERROR_BODY,
        [],
        [],
        null,
        null,
        aborted ? TIMEOUT_NEXT_ACTION : ERROR_NEXT_ACTION,
      );
    } finally {
      clearTimeout(timer);
      this.controller = null;
    }
  }

  private async reduceStream(response: Response, signal: AbortSignal): Promise<AssistantTurn> {
    if (response.body === null) {
      throw new Error("empty streaming response");
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    let state: AgentMessageState | "unavailable" = "streaming";
    let body = "";
    const citations: Citation[] = [];
    const toolTrace: ToolTraceEntry[] = [];
    let agentVersion: string | null = null;
    let modelVersion: string | null = null;
    let nextAction: string | null = null;

    try {
      while (true) {
        const { done, value } = await readChunk(reader, signal);
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const { frames, rest } = decodeSseChunk(buffer);
        buffer = rest;
        for (const frame of frames) {
          this.reduceFrame(frame, {
            state: (next) => {
              state = next;
            },
            body: (text) => {
              body += text;
            },
            citation: (citation) => {
              citations.push(citation);
            },
            tool: (entry) => {
              toolTrace.push(entry);
            },
            done: (agent, model) => {
              agentVersion = agent;
              modelVersion = model;
              // A terminal state (unavailable, timeout, error, policy_blocked)
              // set by a state frame outranks the closing done frame.
              if (state === "streaming") state = "complete";
            },
            nextAction: (action) => {
              nextAction = action;
            },
          });
        }
      }
    } finally {
      reader.releaseLock();
    }

    if (state === "streaming") state = "complete";
    return this.turn(state, body, citations, toolTrace, agentVersion, modelVersion, nextAction);
  }

  private async reduceNonOk(response: Response): Promise<AssistantTurn> {
    const { frames } = decodeSseChunk(await response.text());
    const stateFrame = frames.find((frame): frame is Extract<AssistantFrame, { type: "state" }> =>
      frame.type === "state",
    );
    const quotaFrame = frames.find((frame): frame is Extract<AssistantFrame, { type: "quota" }> =>
      frame.type === "quota",
    );

    if (response.status === 429) {
      const resetCopy = quotaFrame
        ? `Hạn mức được đặt lại lúc ${formatResetTime(quotaFrame.resetsAt)}.`
        : null;
      return this.turn(
        "policy_blocked",
        stateFrame?.reason ?? "Bạn đã dùng hết lượt phân tích AI của kỳ này.",
        [],
        [],
        null,
        null,
        resetCopy,
      );
    }

    if (response.status === 403) {
      return this.turn(
        "policy_blocked",
        stateFrame?.reason ?? "Tài khoản không được phép gửi yêu cầu này.",
        [],
        [],
        null,
        null,
        "Yêu cầu cấp quyền analyst, hoặc xem phân tích đã lưu trong Báo cáo.",
      );
    }

    return this.turn("error", ERROR_BODY, [], [], null, null, ERROR_NEXT_ACTION);
  }

  private reduceFrame(
    frame: AssistantFrame,
    sink: {
      state: (state: AgentMessageState | "unavailable") => void;
      body: (text: string) => void;
      citation: (citation: Citation) => void;
      tool: (entry: ToolTraceEntry) => void;
      done: (agent: string | null, model: string | null) => void;
      nextAction: (action: string) => void;
    },
  ): void {
    switch (frame.type) {
      case "state":
        if (frame.state === "eks_off") {
          sink.state("unavailable");
          sink.body(EKS_OFF_BODY);
          sink.nextAction(EKS_OFF_NEXT_ACTION);
        } else if (frame.state === "timeout") {
          sink.state("timeout");
          if (!frame.reason) sink.body(TIMEOUT_BODY);
          sink.nextAction(TIMEOUT_NEXT_ACTION);
        } else if (frame.state === "policy_blocked") {
          sink.state("policy_blocked");
          if (frame.reason) sink.body(frame.reason);
          sink.nextAction("Đặt lại câu hỏi ở phạm vi phân tích tài chính của doanh nghiệp.");
        } else {
          sink.state(frame.state);
        }
        break;
      case "token":
        sink.body(frame.text);
        break;
      case "citation":
        sink.citation(frame.citation);
        break;
      case "tool":
        sink.tool(frame.entry);
        break;
      case "done":
        sink.done(frame.agentVersion, frame.modelVersion);
        break;
      case "error":
        sink.state("error");
        sink.body(frame.reason);
        sink.nextAction(ERROR_NEXT_ACTION);
        break;
      case "quota":
        // The quota line is surfaced through the 429 copy; a mid-stream quota
        // frame is ignored here rather than rendered twice.
        break;
    }
  }

  private turn(
    state: AgentMessageState | "unavailable",
    body: string,
    citations: readonly Citation[],
    toolTrace: readonly ToolTraceEntry[],
    agentVersion: string | null,
    modelVersion: string | null,
    nextAction: string | null,
  ): AssistantTurn {
    return {
      id: `turn-${Date.now()}-assistant`,
      role: "assistant",
      body,
      createdAt: new Date().toISOString(),
      state,
      citations,
      toolTrace,
      agentVersion,
      modelVersion,
      nextAction,
    };
  }
}

function formatResetTime(iso: string): string {
  try {
    return new Intl.DateTimeFormat("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

/**
 * Read one chunk, resolving on stream end or rejecting when the caller aborts.
 * Racing the read against the signal means an abort frees a `reader.read()` that
 * the upstream never answers — the panel cannot hang on a silent route.
 */
function readChunk(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  signal: AbortSignal,
): Promise<{ done: boolean; value?: Uint8Array }> {
  if (signal.aborted) return Promise.reject(new DOMException("aborted", "AbortError"));
  return new Promise((resolve, reject) => {
    const onAbort = () => reject(new DOMException("aborted", "AbortError"));
    signal.addEventListener("abort", onAbort, { once: true });
    reader.read().then(
      (result) => {
        signal.removeEventListener("abort", onAbort);
        resolve(result);
      },
      (error: unknown) => {
        signal.removeEventListener("abort", onAbort);
        reject(error);
      },
    );
  });
}

export function encodeFixtureFrames(frames: readonly AssistantFrame[]): string {
  return frames.map(encodeSseFrame).join("");
}