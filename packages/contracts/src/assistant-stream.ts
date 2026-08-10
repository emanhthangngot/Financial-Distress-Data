import type { AgentMessageState, Citation, ToolTraceEntry } from "./agent";

/**
 * Assistant SSE frame contract and a tolerant line-based codec.
 *
 * The route handler and the streaming transport share this single typed frame
 * union so the wire protocol cannot drift from the UI states. Everything here
 * is submit-agnostic: the frames carry rendered text, tool entries, citations
 * and quota counters — never a prompt, upstream token, or endpoint URL.
 */

export const ASSISTANT_ERROR_CODES = [
  "UPSTREAM_UNAVAILABLE",
  "UPSTREAM_TIMEOUT",
  "MALFORMED_RESPONSE",
  "UPSTREAM_REFUSED",
  "ABORTED",
] as const;
export type AssistantErrorCode = (typeof ASSISTANT_ERROR_CODES)[number];

/** The assistant-only plane state alongside the existing agent message states. */
export type AssistantPlaneOffState = "eks_off";

export type AssistantFrame =
  | {
      type: "state";
      state: AgentMessageState | AssistantPlaneOffState;
      reason: string | null;
    }
  | { type: "token"; text: string }
  | { type: "tool"; entry: ToolTraceEntry }
  | { type: "citation"; citation: Citation }
  | { type: "quota"; remaining: number; resetsAt: string }
  | {
      type: "done";
      agentVersion: string | null;
      modelVersion: string | null;
    }
  | { type: "error"; code: AssistantErrorCode; reason: string };

/** Discriminates on `type` so unknown frame kinds can be skipped, not throw. */
export function isAssistantFrame(value: unknown): value is AssistantFrame {
  if (typeof value !== "object" || value === null) return false;
  const type = (value as { type?: unknown }).type;
  return (
    type === "state" ||
    type === "token" ||
    type === "tool" ||
    type === "citation" ||
    type === "quota" ||
    type === "done" ||
    type === "error"
  );
}

/**
 * Serialize one frame as a single SSE `data:` event. Events end with a blank
 * line so a reader splitting on newlines can treat each event atomically.
 */
export function encodeSseFrame(frame: AssistantFrame): string {
  return `data: ${JSON.stringify(frame)}\n\n`;
}

/**
 * Parse a received buffer into the complete frames it contains plus whatever
 * partial line has not yet terminated (returned as `rest` so the caller can
 * prepend it to the next chunk, reassembling a frame split across packets).
 *
 * Tolerant by design: blank lines are separators, lines without the `data:`
 * prefix are ignored, JSON that fails to parse is skipped, and a recognized but
 * unknown `type` is dropped rather than treated as fatal.
 */
export function decodeSseChunk(buffer: string): {
  frames: AssistantFrame[];
  rest: string;
} {
  const frames: AssistantFrame[] = [];
  const lines = buffer.split("\n");
  const rest = lines.pop() ?? "";

  for (const line of lines) {
    const trimmed = line.trimEnd();
    if (trimmed === "") continue;
    if (!trimmed.startsWith("data:")) continue;
    const payload = trimmed.slice("data:".length).trimStart();
    if (payload === "") continue;

    try {
      const parsed: unknown = JSON.parse(payload);
      if (isAssistantFrame(parsed)) frames.push(parsed);
      // A valid-JSON but unknown/duplicate field is skipped silently.
    } catch {
      // Malformed JSON in a data line: skip, never fatal.
    }
  }

  return { frames, rest };
}