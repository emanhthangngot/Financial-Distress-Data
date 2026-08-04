import { DISCLAIMER_TEXT } from "@distresslens/contracts";
import type { AssistantTurn } from "@/lib/assistant/assistant-transport";

/**
 * One turn in the assistant thread.
 *
 * An answer never arrives as bare prose. It carries the model and agent version
 * that produced it, the sources it cited, and the tools it ran — the three
 * things that let an analyst decide how much weight to give it. A non-complete
 * answer says what happened and what to do next instead of trailing off.
 */

const STATE_NOTE: Record<string, { label: string; tone: string }> = {
  streaming: { label: "Đang trả lời", tone: "text-text-muted" },
  tool_running: { label: "Đang truy vấn dữ liệu", tone: "text-text-muted" },
  timeout: { label: "Quá thời gian chờ", tone: "text-risk-watch-ink" },
  policy_blocked: { label: "Bị chính sách chặn", tone: "text-risk-watch-ink" },
  unavailable: { label: "Chưa kết nối dịch vụ", tone: "text-risk-watch-ink" },
  error: { label: "Lỗi", tone: "text-risk-high-ink" },
};

export function AssistantMessage({ turn }: { turn: AssistantTurn }) {
  if (turn.role === "user") {
    return (
      <li className="flex justify-end">
        <p className="max-w-[85%] rounded-lg rounded-br-sm bg-primary-050 px-3.5 py-2.5 text-[14px] text-text-strong">
          {turn.body}
        </p>
      </li>
    );
  }

  const note = STATE_NOTE[turn.state];

  return (
    <li className="flex flex-col gap-2 rounded-lg border border-line-hairline bg-paper-0 px-3.5 py-3">
      {note !== undefined ? (
        <p className={`text-[12px] font-semibold uppercase tracking-[0.06em] ${note.tone}`}>
          {note.label}
        </p>
      ) : null}

      <p className="text-[14px] leading-relaxed text-text-body">{turn.body}</p>

      {turn.nextAction !== null ? (
        <p className="text-[13px] text-text-muted">{turn.nextAction}</p>
      ) : null}

      {turn.citations.length > 0 ? (
        <ol className="flex flex-col gap-1 border-t border-line-hairline pt-2 text-[13px]">
          {turn.citations.map((citation) => (
            <li key={citation.sourceId} className="flex gap-2">
              <span className="shrink-0 font-mono text-[12px] text-text-muted">
                [{citation.ordinal}]
              </span>
              <span className="min-w-0">
                {citation.url === null ? (
                  <span className="text-text-body">{citation.title}</span>
                ) : (
                  <a
                    href={citation.url}
                    className="text-primary-600 underline underline-offset-2 hover:text-primary-700"
                  >
                    {citation.title}
                  </a>
                )}
                <span className="text-text-muted"> · {citation.publisher}</span>
              </span>
            </li>
          ))}
        </ol>
      ) : null}

      {turn.toolTrace.length > 0 ? (
        <details className="border-t border-line-hairline pt-2">
          <summary className="text-[13px] text-text-muted">
            Các bước đã chạy ({turn.toolTrace.length})
          </summary>
          <ol className="mt-2 flex flex-col gap-1.5">
            {turn.toolTrace.map((entry) => (
              <li key={entry.id} className="flex items-baseline gap-2 text-[13px]">
                <span className="font-mono text-[12px] text-text-muted">{entry.toolName}</span>
                <span className="text-text-body">{entry.summary}</span>
                <span className="ml-auto shrink-0 font-mono text-[12px] text-text-muted">
                  {entry.durationMs} ms
                </span>
              </li>
            ))}
          </ol>
        </details>
      ) : null}

      {turn.modelVersion !== null || turn.agentVersion !== null ? (
        <p className="font-mono text-[11px] text-text-muted">
          {[turn.agentVersion, turn.modelVersion].filter((value) => value !== null).join(" · ")}
        </p>
      ) : null}

      {turn.state === "complete" ? (
        <p className="border-t border-line-hairline pt-2 text-[12px] text-text-muted">
          {DISCLAIMER_TEXT}
        </p>
      ) : null}
    </li>
  );
}
