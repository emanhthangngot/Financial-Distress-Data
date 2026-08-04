"use client";

import { AssistantIcon } from "@/components/shell/icons";
import { useAssistant } from "./assistant-provider";

/**
 * The floating launcher, fixed to the bottom-right corner.
 *
 * It is a pill rather than a bare circle: the label "Trợ lý phân tích" says
 * what it does without a hover, which is the difference between a support
 * widget an analyst opens and a mystery button they ignore. It collapses to a
 * circle below the `sm` breakpoint, where the label would crowd the content.
 *
 * Motion is a 150ms hover lift and nothing else — no pulse, no glow. A
 * permanently animating control in the corner of a risk dashboard reads as an
 * alert that never resolves.
 */
export function AssistantLauncher() {
  const { mode, open, turns, registerLauncher } = useAssistant();
  const collapsed = mode === "collapsed";

  // The badge marks an answer the analyst has not read yet in this thread. It
  // counts nothing else, so it cannot become ambient notification noise.
  const unread = turns.at(-1)?.role === "assistant";

  return (
    <button
      ref={registerLauncher}
      type="button"
      onClick={() => open("docked")}
      aria-label="Mở trợ lý phân tích"
      data-print-hidden
      // The launcher stays mounted while the panel is open, hidden rather than
      // unmounted. Unmounting it detached the node the panel focuses on close,
      // which silently dropped a keyboard user at the top of the document.
      aria-hidden={collapsed ? undefined : true}
      tabIndex={collapsed ? undefined : -1}
      className={[
        "tap-target fixed bottom-6 right-6 z-(--z-assistant) flex items-center gap-2.5 rounded-xl bg-ai-500 px-4 py-3 text-[14px] font-semibold text-paper-0 shadow-(--shadow-assistant)",
        "transition-[background-color,opacity] duration-(--duration-fast) ease-(--ease-standard) hover:bg-ai-600",
        collapsed ? "" : "pointer-events-none opacity-0",
      ].join(" ")}
    >
      <span aria-hidden="true" className="relative">
        <AssistantIcon width={22} height={22} />
        {unread ? (
          <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border-2 border-ai-500 bg-paper-0" />
        ) : null}
      </span>
      {/* Label on a desktop canvas, icon-only below it: a labelled pill on a
          phone sits over the content it is meant to help read. */}
      <span className="hidden lg:inline">Trợ lý phân tích</span>
    </button>
  );
}
