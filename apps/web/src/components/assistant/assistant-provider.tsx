"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  assistantThreadKey,
  type AssistantContext as AssistantPageContext,
} from "@/lib/assistant/assistant-context";
import {
  StreamingAssistantTransport,
} from "@/lib/assistant/streaming-transport";
import type { AssistantTransport, AssistantTurn } from "@/lib/assistant/assistant-transport";

/**
 * Assistant state: which view mode is showing, which page context the assistant
 * is looking at, and one conversation thread per context.
 *
 * Threads are keyed by scope and ticker rather than kept as a single rolling
 * conversation, so asking about HPG and then opening NVL does not leave the
 * analyst reading an answer about the wrong company. Returning to HPG restores
 * that thread.
 *
 * Threads live for the session only. Nothing is written to storage, because the
 * questions an analyst asks about a portfolio are as sensitive as the portfolio.
 */

export type AssistantViewMode = "collapsed" | "docked" | "expanded";

interface AssistantStore {
  mode: AssistantViewMode;
  context: AssistantPageContext;
  turns: readonly AssistantTurn[];
  pending: boolean;
  open(mode?: AssistantViewMode): void;
  close(): void;
  setMode(mode: AssistantViewMode): void;
  ask(question: string): Promise<void>;
  cancel(): void;
  clearThread(): void;
  /** Remaining AI budget to show before it is spent; null hides the line. */
  quotaRemaining: number | null;
  /** The launcher registers itself so focus returns there when the panel closes. */
  registerLauncher(node: HTMLButtonElement | null): void;
}

const AssistantStoreContext = createContext<AssistantStore | null>(null);

/**
 * The transport wired by default. The route always exists (even when the plane
 * is off it answers truthfully with an `eks_off` frame), so the streaming
 * transport is the default; `UNAVAILABLE_TRANSPORT` stays as the explicit
 * fallback for a build where the route is deliberately absent.
 */
export const STREAMING_TRANSPORT: AssistantTransport = new StreamingAssistantTransport(
  "/api/assistant/stream",
);

export function useAssistant(): AssistantStore {
  const store = useContext(AssistantStoreContext);
  if (store === null) {
    throw new Error("useAssistant must be used inside AssistantProvider");
  }
  return store;
}

export function AssistantProvider({
  context,
  transport = STREAMING_TRANSPORT,
  quotaRemaining = null,
  children,
}: {
  context: AssistantPageContext;
  transport?: AssistantTransport;
  /** Remaining AI budget for the quota line; null (or omitted) hides it. */
  quotaRemaining?: number | null;
  children: ReactNode;
}) {
  const [mode, setMode] = useState<AssistantViewMode>("collapsed");
  const [threads, setThreads] = useState<Record<string, readonly AssistantTurn[]>>({});
  const [pending, setPending] = useState(false);
  const launcherRef = useRef<HTMLButtonElement | null>(null);

  const threadKey = assistantThreadKey(context);
  // Memoised so the empty-thread fallback is not a new array on every render,
  // which would make the store identity change on every render too.
  const turns = useMemo<readonly AssistantTurn[]>(
    () => threads[threadKey] ?? [],
    [threads, threadKey],
  );

  const open = useCallback((next: AssistantViewMode = "docked") => {
    setMode(next);
  }, []);

  const close = useCallback(() => {
    setMode("collapsed");
    // Focus returns to the control that opened the panel, otherwise a keyboard
    // user lands back at the top of the document.
    launcherRef.current?.focus();
  }, []);

  const clearThread = useCallback(() => {
    setThreads((current) => ({ ...current, [threadKey]: [] }));
  }, [threadKey]);

  const cancel = useCallback(() => {
    transport.abort?.();
  }, [transport]);

  const ask = useCallback(
    async (question: string) => {
      const trimmed = question.trim();
      if (trimmed === "" || pending) {
        return;
      }

      const asked: AssistantTurn = {
        id: `turn-${Date.now()}-user`,
        role: "user",
        body: trimmed,
        createdAt: new Date().toISOString(),
        state: "complete",
        citations: [],
        toolTrace: [],
        agentVersion: null,
        modelVersion: null,
        nextAction: null,
      };

      const history = threads[threadKey] ?? [];
      setThreads((current) => ({ ...current, [threadKey]: [...history, asked] }));
      setPending(true);

      try {
        const answer = await transport.send({ context, question: trimmed, history });
        setThreads((current) => ({
          ...current,
          [threadKey]: [...(current[threadKey] ?? []), answer],
        }));
      } catch {
        // A transport failure is a state the analyst can act on, not a silent
        // dropped message: the question stays visible above this answer.
        setThreads((current) => ({
          ...current,
          [threadKey]: [
            ...(current[threadKey] ?? []),
            {
              id: `turn-${Date.now()}-error`,
              role: "assistant",
              body: "Không gửi được câu hỏi tới trợ lý phân tích.",
              createdAt: new Date().toISOString(),
              state: "error",
              citations: [],
              toolTrace: [],
              agentVersion: null,
              modelVersion: null,
              nextAction: "Thử lại sau ít phút, hoặc xem số liệu và nguồn dữ liệu trên trang.",
            },
          ],
        }));
      } finally {
        setPending(false);
      }
    },
    [context, pending, threadKey, threads, transport],
  );

  const registerLauncher = useCallback((node: HTMLButtonElement | null) => {
    launcherRef.current = node;
  }, []);

  const store = useMemo<AssistantStore>(
    () => ({
      mode,
      context,
      turns,
      pending,
      quotaRemaining,
      open,
      close,
      setMode,
      ask,
      cancel,
      clearThread,
      registerLauncher,
    }),
    [mode, context, turns, pending, quotaRemaining, open, close, ask, cancel, clearThread, registerLauncher],
  );

  return <AssistantStoreContext.Provider value={store}>{children}</AssistantStoreContext.Provider>;
}
