"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, Loader2, X } from "lucide-react";
import { ChatTopBar } from "./chat-top-bar";
import { MessageTimeline } from "./message-timeline";
import {
  ChatComposer,
  type ModelOption,
  type ModelSelection,
} from "./chat-composer";
import { LiveContextPanel } from "./live-context-panel";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { PROVIDERS } from "@/lib/providers";
import { useConversations } from "@/components/conversations/conversations-provider";
import { useProjects } from "@/components/projects/projects-provider";
import { api, ApiError } from "@/lib/api-client";
import type {
  ChatMessage,
  Conversation,
  Project,
  ProjectInstructions,
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

export function ChatWorkspace({
  projectId,
  conversationId,
}: {
  projectId: string;
  conversationId: string;
}) {
  const isDesktop = useMediaQuery("(min-width: 1280px)");
  const { conversations, updateConversationLocal } = useConversations();
  const { projects } = useProjects();

  const [desktopInspector, setDesktopInspector] = useState(true);
  const [mobileInspector, setMobileInspector] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [sendError, setSendError] = useState<{
    category?: string;
    message: string;
  } | null>(null);
  const [instructions, setInstructions] = useState<ProjectInstructions | null>(
    null,
  );
  const [modelOptions, setModelOptions] = useState<ModelOption[]>([
    { provider: "stub", label: "Stub", models: ["stub-echo"] },
  ]);
  const [selection, setSelection] = useState<ModelSelection>({
    provider: "stub",
    modelId: "stub-echo",
  });

  const conversation = conversations.find((c) => c.id === conversationId) ?? null;
  const project = projects.find((p) => p.id === projectId) ?? null;
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      setLoadError(null);
      setSendError(null);
      try {
        const [msgs, instr] = await Promise.all([
          api.getMessages(conversationId),
          api.getInstructions(projectId),
        ]);
        if (!active) return;
        setMessages(msgs);
        setInstructions(instr);
      } catch (e) {
        if (active)
          setLoadError(
            e instanceof ApiError && e.status === 404
              ? "Conversation not found."
              : "Could not load this conversation.",
          );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [conversationId, projectId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const providers = await api.listProviders();
        const opts: ModelOption[] = [
          { provider: "stub", label: "Stub", models: ["stub-echo"] },
        ];
        for (const p of providers) {
          if (p.configured && p.enabledModels.length) {
            const label =
              (PROVIDERS as Record<string, { label: string }>)[p.provider]
                ?.label ?? p.provider;
            opts.push({ provider: p.provider, label, models: p.enabledModels });
          }
        }
        if (active) setModelOptions(opts);
      } catch {
        /* ignore — stub remains available */
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const inspectorOpen = isDesktop ? desktopInspector : mobileInspector;
  function toggleInspector() {
    if (isDesktop) setDesktopInspector((v) => !v);
    else setMobileInspector((v) => !v);
  }

  async function handleSend(text: string) {
    try {
      const { userMessage, assistantMessage } = await api.sendMessage(
        conversationId,
        text,
        selection.provider,
        selection.modelId,
      );
      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setSendError(null);
      if (conversation) {
        updateConversationLocal({
          ...conversation,
          activeProvider: assistantMessage.provider ?? null,
          activeModelId: assistantMessage.modelId ?? null,
          updatedAt: new Date().toISOString(),
        });
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 502) {
        // Provider failed, but the user message was persisted (write-ahead).
        try {
          setMessages(await api.getMessages(conversationId));
        } catch {
          /* ignore refetch failure */
        }
        setSendError({ category: err.category, message: err.message });
        return; // message was sent; let the composer clear
      }
      // Network/other failure — message not saved; preserve the draft.
      setSendError({
        category: err instanceof ApiError ? err.category : undefined,
        message:
          err instanceof ApiError ? err.message : "Could not send message.",
      });
      throw err;
    }
  }

  const topProject: Project = project ?? {
    id: projectId,
    name: "Project",
    description: "",
    status: "active",
    updatedAt: new Date().toISOString(),
  };
  const topConversation: Conversation = conversation ?? {
    id: conversationId,
    projectId,
    title: "Conversation",
    activeProvider: null,
    activeModelId: null,
    updatedAt: new Date().toISOString(),
  };

  const panel = <LiveContextPanel project={project} instructions={instructions} />;

  return (
    <div className="flex min-h-0 flex-1">
      <div className="flex min-w-0 flex-1 flex-col">
        <ChatTopBar
          project={topProject}
          conversation={topConversation}
          inspectorOpen={inspectorOpen}
          onToggleInspector={toggleInspector}
        />

        <div className="min-h-0 flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-tertiary" />
            </div>
          ) : loadError ? (
            <div className="flex h-full items-center justify-center px-4 text-center text-sm text-tertiary">
              {loadError}
            </div>
          ) : messages.length === 0 ? (
            <div className="mx-auto flex h-full max-w-3xl items-center justify-center px-4 text-center">
              <div>
                <p className="text-sm font-medium text-primary">
                  Start the conversation
                </p>
                <p className="mt-1 text-sm text-secondary">
                  Send a message below. Replies come from the stub echo adapter
                  until Phase 4 adds real providers.
                </p>
              </div>
            </div>
          ) : (
            <MessageTimeline messages={messages} />
          )}
          <div ref={bottomRef} />
        </div>

        {sendError ? (
          <div className="mx-auto w-full max-w-3xl px-4">
            <div className="my-2 flex items-start gap-2 rounded-lg border border-danger/40 bg-danger/10 p-3 text-sm">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
              <div className="min-w-0 flex-1">
                <p className="font-medium text-primary">
                  {sendError.category
                    ? sendError.category.replaceAll("_", " ")
                    : "Send failed"}
                </p>
                <p className="text-secondary">{sendError.message}</p>
                <p className="mt-0.5 text-xs text-tertiary">
                  Your message and history are preserved. Manual model switching
                  across real providers arrives in Phase 4.
                </p>
              </div>
              <button
                type="button"
                aria-label="Dismiss"
                onClick={() => setSendError(null)}
                className="rounded p-1 text-tertiary transition-colors hover:text-primary"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        ) : null}

        <ChatComposer
          onSend={handleSend}
          options={modelOptions}
          selection={selection}
          onSelect={setSelection}
        />
      </div>

      {desktopInspector ? (
        <aside className="hidden w-[340px] shrink-0 flex-col border-l border-subtle bg-surface xl:flex">
          {panel}
        </aside>
      ) : null}

      <Sheet open={mobileInspector} onOpenChange={setMobileInspector}>
        <SheetContent side="right" className="w-[360px]">
          <SheetTitle className="sr-only">Context Included</SheetTitle>
          {panel}
        </SheetContent>
      </Sheet>
    </div>
  );
}
