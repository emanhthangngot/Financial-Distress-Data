"use client";

import type { AssistantContext } from "@/lib/assistant/assistant-context";
import { AssistantLauncher } from "./assistant-launcher";
import { AssistantPanel } from "./assistant-panel";
import { AssistantProvider } from "./assistant-provider";

/**
 * The whole assistant, mounted once per shell.
 *
 * Pages pass the context they are showing; nothing else about the assistant is
 * a page's concern. Keeping this one entry point is what stops an AI affordance
 * from being pasted into individual surfaces and drifting apart.
 */
export function AnalysisAssistant({ context }: { context: AssistantContext }) {
  return (
    <AssistantProvider context={context}>
      <AssistantLauncher />
      <AssistantPanel />
    </AssistantProvider>
  );
}
