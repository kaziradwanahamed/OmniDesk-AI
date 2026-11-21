"use client";

import { useEffect, useRef, useState } from "react";
import { Info, X } from "lucide-react";
import { ChatTopBar } from "./chat-top-bar";
import { MessageTimeline } from "./message-timeline";
import { Composer } from "./composer";
import { ErrorRecoveryBanner } from "./error-recovery-banner";
import { MultiModelGrid, type MultiModelColumn } from "./multi-model-grid";
import { ContextInspector } from "@/components/context/context-inspector";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import {
  PREVIEW_MODELS,
  PREVIEW_NOTICE,
  sampleDecisions,
  sampleInstructions,
  sampleMessages,
  sampleSnapshot,
  sampleSummary,
  sampleTasks,
} from "@/lib/sample";
import type {
  ChatMessage,
  Conversation,
  Project,
  ProviderError,
  ProviderModel,
} from "@/lib/types";

function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(true);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const onChange = () => setMatches(mq.matches);
    onChange();
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [query]);
  return matches;
}

const PREVIEW_COLUMNS: MultiModelColumn[] = [
  {
    provider: "openai",
    modelId: "preview-model",
    status: "completed",
    content:
      "Use a **token bucket** keyed per principal in Redis with a small burst allowance.",
  },
  {
    provider: "anthropic",
    modelId: "preview-model",
    status: "completed",
    content:
      "Prefer a token bucket, then layer a sliding-window counter for the hard per-minute cap.",
  },
  {
    provider: "gemini",
    modelId: "preview-model",
    status: "failed",
    errorLabel: "Rate limited (429)",
  },
];

export function ChatWorkspace({
  project,
  conversation,
}: {
  project: Project;
  conversation: Conversation;
}) {
  const isDesktop = useMediaQuery("(min-width: 1280px)");
  const [desktopInspector, setDesktopInspector] = useState(true);
  const [mobileInspector, setMobileInspector] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(sampleMessages);
  const [multiModel, setMultiModel] = useState(false);
  const [error, setError] = useState<ProviderError | null>(null);
  const [showPreview, setShowPreview] = useState(true);
  const [selection, setSelection] = useState<ProviderModel>({
    provider: conversation.activeProvider ?? "anthropic",
    modelId: conversation.activeModelId ?? "preview-model",
  });

  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, multiModel]);

  const activeTask = sampleTasks.find((t) => t.isActive) ?? null;
  const inspectorOpen = isDesktop ? desktopInspector : mobileInspector;

  function toggleInspector() {
    if (isDesktop) setDesktopInspector((v) => !v);
    else setMobileInspector((v) => !v);
  }

  function handleSend(text: string) {
    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
        createdAt: new Date().toISOString(),
      },
    ]);
    // No provider backend is wired yet — surface this honestly via the error
    // recovery flow rather than fabricating a response.
    setError({
      category: "MODEL_UNAVAILABLE",
      message:
        "Preview mode — no provider backend is connected yet. A real response streams once a provider is wired (Phase 4).",
    });
  }

  const inspector = (
    <ContextInspector
      instructions={sampleInstructions}
      activeTask={activeTask}
      decisions={sampleDecisions}
      summary={sampleSummary}
      snapshot={sampleSnapshot}
    />
  );

  return (
    <div className="flex min-h-0 flex-1">
      <div className="flex min-w-0 flex-1 flex-col">
        <ChatTopBar
          project={project}
          conversation={conversation}
          inspectorOpen={inspectorOpen}
          onToggleInspector={toggleInspector}
        />

        {showPreview ? (
          <div className="flex items-center gap-2 border-b border-subtle bg-accent/5 px-4 py-2 text-xs text-secondary">
            <Info className="h-3.5 w-3.5 shrink-0 text-accent" />
            <span className="min-w-0 flex-1">{PREVIEW_NOTICE}</span>
            <button
              type="button"
              aria-label="Dismiss preview notice"
              onClick={() => setShowPreview(false)}
              className="rounded p-0.5 text-tertiary hover:text-primary"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : null}

        <div className="min-h-0 flex-1 overflow-y-auto">
          {multiModel ? (
            <MultiModelGrid columns={PREVIEW_COLUMNS} />
          ) : (
            <MessageTimeline messages={messages} />
          )}
          <div ref={bottomRef} />
        </div>

        {error ? (
          <div className="px-4">
            <ErrorRecoveryBanner
              error={error}
              available={PREVIEW_MODELS}
              selection={selection}
              onSelect={setSelection}
              onRetry={() => setError(null)}
              onDismiss={() => setError(null)}
            />
          </div>
        ) : null}

        <Composer
          selection={selection}
          available={PREVIEW_MODELS}
          onSelect={setSelection}
          multiModel={multiModel}
          onToggleMultiModel={setMultiModel}
          streaming={false}
          onSend={handleSend}
          onStop={() => {}}
          budgetUsed={sampleSnapshot.estimatedInputTokens}
          budgetTotal={sampleSnapshot.tokenBudget}
          onOpenInspector={toggleInspector}
        />
      </div>

      {desktopInspector ? (
        <aside className="hidden w-[340px] shrink-0 flex-col border-l border-subtle bg-surface xl:flex">
          {inspector}
        </aside>
      ) : null}

      <Sheet open={mobileInspector} onOpenChange={setMobileInspector}>
        <SheetContent side="right" className="w-[360px]">
          <SheetTitle className="sr-only">Context Included</SheetTitle>
          {inspector}
        </SheetContent>
      </Sheet>
    </div>
  );
}
