"use client";

import { useEffect, useRef, useState } from "react";
import { quickActionsFor } from "@/lib/assistant/assistant-context";
import {
  AssistantIcon,
  CloseIcon,
  CollapseIcon,
  ExpandIcon,
  SendIcon,
} from "@/components/shell/icons";
import { DisclaimerBanner } from "@/components/shell/disclaimer-banner";
import { AssistantMessage } from "./assistant-message";
import { useAssistant } from "./assistant-provider";

/**
 * The assistant surface.
 *
 * Docked, it is a support-widget rectangle anchored bottom-right: wide enough
 * to read an explanation, narrow enough that the dashboard behind it stays
 * usable, which is the whole reason the assistant is not a page. Expanded, it
 * takes the viewport and reads like a normal working surface for a long
 * analysis. Below `lg` the docked mode becomes a bottom sheet, because a 400px
 * side panel on a 390px screen is a full-screen dialog pretending otherwise.
 *
 * It is a modal dialog only when expanded or on a small screen. Docked on
 * desktop it deliberately is not: an analyst reads the table and asks about it
 * in the same breath, and a focus trap would make that impossible.
 */
export function AssistantPanel() {
  const { mode, context, turns, pending, close, setMode, ask, clearThread } = useAssistant();
  const [draft, setDraft] = useState("");
  const panelRef = useRef<HTMLDivElement | null>(null);
  const threadRef = useRef<HTMLDivElement | null>(null);
  const open = mode !== "collapsed";
  const expanded = mode === "expanded";

  // Escape closes from anywhere inside the panel, which is what a keyboard user
  // reaches for before hunting the close button.
  useEffect(() => {
    if (!open) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        close();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, close]);

  // While the sheet covers the page, the page behind it must not scroll —
  // otherwise flicking inside the sheet drags the dashboard away underneath.
  // Docked on a desktop canvas the panel is not modal, so nothing is locked.
  useEffect(() => {
    if (!open) {
      return;
    }
    const modal = expanded || !window.matchMedia("(min-width: 1024px)").matches;
    if (!modal) {
      return;
    }
    document.body.classList.add("scroll-locked");
    return () => document.body.classList.remove("scroll-locked");
  }, [open, expanded]);

  // New turns arrive at the bottom; scroll them into view rather than leaving
  // the analyst to discover the answer below the fold.
  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight });
  }, [turns.length, pending]);

  if (!open) {
    return null;
  }

  const quickActions = quickActionsFor(context);

  return (
    <>
      {/* The scrim exists only where the panel is modal. */}
      <div
        aria-hidden="true"
        onClick={close}
        className={[
          "fixed inset-0 z-(--z-assistant) bg-ink-900/35",
          expanded ? "" : "lg:hidden",
        ].join(" ")}
      />

      <div
        ref={panelRef}
        role="dialog"
        aria-modal={expanded ? true : undefined}
        aria-label={`Trợ lý phân tích — ${context.surfaceLabel}`}
        className={[
          "fixed z-(--z-assistant) flex flex-col overflow-hidden border border-line-hairline bg-paper-1 shadow-(--shadow-overlay)",
          expanded
            ? "inset-3 rounded-lg lg:inset-8"
            : [
                // Mobile: bottom sheet with room for the safe area.
                "inset-x-0 bottom-0 max-h-[85dvh] rounded-t-xl pb-[env(safe-area-inset-bottom)]",
                // Desktop: the support-widget rectangle.
                "lg:inset-auto lg:bottom-6 lg:right-6 lg:max-h-[min(680px,calc(100dvh-96px))] lg:w-[404px] lg:rounded-lg lg:pb-0",
              ].join(" "),
        ].join(" ")}
      >
        <header className="flex items-center gap-2 border-b border-line-hairline bg-paper-0 px-4 py-3">
          <span aria-hidden="true" className="text-ai-500">
            <AssistantIcon width={20} height={20} />
          </span>
          <div className="min-w-0">
            <h2 className="truncate text-[15px] font-semibold">Trợ lý phân tích</h2>
            <p className="truncate text-[12px] text-text-muted">
              Ngữ cảnh: {context.surfaceLabel}
            </p>
          </div>

          <div className="ml-auto flex items-center">
            <PanelControl
              onClick={() => setMode(expanded ? "docked" : "expanded")}
              label={expanded ? "Thu nhỏ trợ lý" : "Phóng to trợ lý"}
            >
              {expanded ? <CollapseIcon /> : <ExpandIcon />}
            </PanelControl>
            {/* One dismiss control, not two: "minimise" and "close" would do the
                same thing here, since the thread survives either way. */}
            <PanelControl onClick={close} label="Thu gọn trợ lý về góc màn hình">
              <CloseIcon />
            </PanelControl>
          </div>
        </header>

        {/* Context strip: the analyst can see exactly what the assistant knows
            about the page, which is also the answer to "what did it send". */}
        <div className="flex flex-wrap items-center gap-1.5 border-b border-line-hairline bg-paper-0 px-4 py-2 text-[12px] text-text-muted">
          {[
            context.ticker,
            context.periodLabel,
            ...context.filters,
            context.modelVersion,
          ]
            .filter((value): value is string => value !== null && value !== "")
            .map((value) => (
              <span
                key={value}
                className="rounded-sm border border-line-hairline bg-paper-2 px-1.5 py-0.5 font-mono text-[11px] text-text-body"
              >
                {value}
              </span>
            ))}
          {turns.length > 0 ? (
            <button
              type="button"
              onClick={clearThread}
              className="ml-auto rounded-sm px-1.5 py-0.5 text-[12px] text-text-muted underline underline-offset-2 hover:text-text-body"
            >
              Xóa hội thoại
            </button>
          ) : null}
        </div>

        <div
          ref={threadRef}
          className={`flex-1 overflow-y-auto px-4 py-3 ${expanded ? "lg:px-8" : ""}`}
        >
          <div className={expanded ? "mx-auto max-w-[760px]" : ""}>
            {turns.length === 0 ? (
              <div className="flex flex-col gap-3">
                <p className="text-[14px] text-text-body">
                  Trợ lý đọc số liệu đang hiển thị trên trang này. Chọn một câu hỏi hoặc tự nhập.
                </p>
                <ul className="flex flex-col gap-2">
                  {quickActions.map((action) => (
                    <li key={action.id}>
                      <button
                        type="button"
                        onClick={() => void ask(action.prompt)}
                        disabled={pending}
                        className="tap-target w-full rounded-md border border-line-hairline bg-paper-0 px-3.5 py-2.5 text-left text-[14px] text-text-body transition-colors duration-(--duration-fast) ease-(--ease-standard) hover:border-ai-300 hover:bg-ai-050 disabled:cursor-not-allowed disabled:text-text-muted"
                      >
                        {action.label}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <ul className="flex flex-col gap-3">
                {turns.map((turn) => (
                  <AssistantMessage key={turn.id} turn={turn} />
                ))}
                {pending ? (
                  <li
                    aria-live="polite"
                    className="rounded-lg border border-line-hairline bg-paper-0 px-3.5 py-3 text-[14px] text-text-muted"
                  >
                    Đang gửi câu hỏi…
                  </li>
                ) : null}
              </ul>
            )}
          </div>
        </div>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            void ask(draft);
            setDraft("");
          }}
          className="border-t border-line-hairline bg-paper-0 px-4 py-3"
        >
          <div className={expanded ? "mx-auto max-w-[760px]" : ""}>
            <label htmlFor="assistant-input" className="sr-only">
              Câu hỏi cho trợ lý phân tích
            </label>
            <div className="flex items-end gap-2">
              <textarea
                id="assistant-input"
                rows={2}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Hỏi về rủi ro, chỉ tiêu hoặc thay đổi trong kỳ"
                className="min-h-[44px] w-full resize-none rounded-md border border-line-hairline bg-paper-0 px-3 py-2.5 text-[14px] text-text-body placeholder:text-text-muted focus:border-primary-500 focus:outline-none"
              />
              <button
                type="submit"
                disabled={pending || draft.trim() === ""}
                aria-label="Gửi câu hỏi"
                className="tap-target flex items-center justify-center rounded-md bg-ai-500 px-3 text-paper-0 transition-colors duration-(--duration-fast) ease-(--ease-standard) hover:bg-ai-600 disabled:cursor-not-allowed disabled:bg-paper-3 disabled:text-text-muted"
              >
                <SendIcon />
              </button>
            </div>
            {/* The assistant is a decision-support surface, so it carries the
                shared disclaimer rather than a paraphrase of it. */}
            <div className="mt-2">
              <DisclaimerBanner surface="agent_chat" variant="inline" />
            </div>
          </div>
        </form>
      </div>
    </>
  );
}

function PanelControl({
  onClick,
  label,
  children,
}: {
  onClick: () => void;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className="tap-target flex items-center justify-center rounded-md px-2 text-text-muted transition-colors duration-(--duration-fast) ease-(--ease-standard) hover:bg-paper-2 hover:text-text-body"
    >
      {children}
    </button>
  );
}
