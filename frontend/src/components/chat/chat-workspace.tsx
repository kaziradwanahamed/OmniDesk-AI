"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, Loader2, RefreshCw, X } from "lucide-react";
import { ChatTopBar } from "./chat-top-bar";
import { MessageTimeline } from "./message-timeline";
import {
  ChatComposer,
  type ModelOption,
  type ModelSelection,
} from "./chat-composer";
import type { MultiModelError } from "./multi-model-grid";
import { LiveContextPanel } from "./live-context-panel";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { PROVIDERS } from "@/lib/providers";
import { useConversations } from "@/components/conversations/conversations-provider";
import { useProjects } from "@/components/projects/projects-provider";
import { api, ApiError } from "@/lib/api-client";
import type {
  ChatMessage,
  Conversation,
  MessageGroupInfo,
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
  const [retry, setRetry] = useState<{ messageId: string; content: string } | null>(
    null,
  );
  const [retrying, setRetrying] = useState(false);
  const [groups, setGroups] = useState<Record<string, MessageGroupInfo>>({});
  const [groupErrors, setGroupErrors] = useState<
    Record<string, MultiModelError[]>
  >({});
  const [busyGroupId, setBusyGroupId] = useState<string | null>(null);
  const [multiMode, setMultiMode] = useState(false);
  const [multiTargets, setMultiTargets] = useState<ModelSelection[]>([]);
  const [ctxVersion, setCtxVersion] = useState(0);

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
        const [msgs, instr, grps] = await Promise.all([
          api.getMessages(conversationId),
          api.getInstructions(projectId),
          api.listGroups(conversationId),
        ]);
        if (!active) return;
        setMessages(msgs);
        setInstructions(instr);
        setGroups(Object.fromEntries(grps.map((g) => [g.id, g])));
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

  const willSwitch =
    !!conversation?.activeProvider &&
    (conversation.activeProvider !== selection.provider ||
      conversation.activeModelId !== selection.modelId);

  /** Explicitly switch the active model (recording a system_event divider) when
   * the composer selection differs from the conversation's active model. The
   * first turn (no active model yet) switches silently — nothing to switch from. */
  async function maybeSwitch(): Promise<void> {
    if (!conversation || !willSwitch) return;
    const res = await api.switchModel(
      conversationId,
      selection.provider,
      selection.modelId,
    );
    updateConversationLocal({
      ...conversation,
      activeProvider: res.conversation.activeProvider,
      activeModelId: res.conversation.activeModelId,
      updatedAt: res.conversation.updatedAt,
    });
  }

  function syncActive(provider: string | null, modelId: string | null) {
    if (conversation) {
      updateConversationLocal({
        ...conversation,
        activeProvider: provider,
        activeModelId: modelId,
        updatedAt: new Date().toISOString(),
      });
    }
  }

  function captureRetry(msgs: ChatMessage[]) {
    const lastUser = [...msgs].reverse().find((m) => m.role === "user");
    setRetry(
      lastUser ? { messageId: lastUser.id, content: lastUser.content } : null,
    );
  }

  /** Refetch the canonical timeline + groups and bump the context inspector. */
  async function reload(): Promise<ChatMessage[]> {
    const [msgs, grps] = await Promise.all([
      api.getMessages(conversationId),
      api.listGroups(conversationId),
    ]);
    setMessages(msgs);
    setGroups(Object.fromEntries(grps.map((g) => [g.id, g])));
    setCtxVersion((v) => v + 1);
    return msgs;
  }

  async function handleSend(text: string) {
    // 1. Switch the model first (divider) if the selection changed.
    try {
      await maybeSwitch();
    } catch (err) {
      setSendError({
        category: err instanceof ApiError ? err.category : undefined,
        message:
          err instanceof ApiError ? err.message : "Could not switch model.",
      });
      throw err; // nothing sent — keep the draft
    }
    // 2. Send through the (possibly new) active model.
    try {
      await api.sendMessage(conversationId, text, selection.provider, selection.modelId);
      await reload();
      setSendError(null);
      setRetry(null);
      syncActive(selection.provider, selection.modelId);
    } catch (err) {
      if (err instanceof ApiError && err.status === 502) {
        // Provider failed, but the user message was persisted (write-ahead).
        try {
          captureRetry(await reload());
        } catch {
          /* ignore refetch failure */
        }
        setSendError({ category: err.category, message: err.message });
        return; // message was saved; let the composer clear
      }
      setSendError({
        category: err instanceof ApiError ? err.category : undefined,
        message:
          err instanceof ApiError ? err.message : "Could not send message.",
      });
      throw err; // network/other — message not saved; preserve the draft
    }
  }

  /** "Switch Model & Retry": reuse the preserved user message (no duplicate),
   * switching to the newly-selected model first when it changed. */
  async function handleRetry() {
    if (!retry || retrying) return;
    setRetrying(true);
    try {
      await maybeSwitch();
      await api.sendMessage(
        conversationId,
        retry.content,
        selection.provider,
        selection.modelId,
        retry.messageId,
      );
      await reload();
      setSendError(null);
      setRetry(null);
      syncActive(selection.provider, selection.modelId);
    } catch (err) {
      if (err instanceof ApiError && err.status === 502) {
        try {
          await reload();
        } catch {
          /* ignore */
        }
        setSendError({ category: err.category, message: err.message });
        // keep `retry` so the user can pick yet another model
      } else {
        setSendError({
          category: err instanceof ApiError ? err.category : undefined,
          message: err instanceof ApiError ? err.message : "Retry failed.",
        });
      }
    } finally {
      setRetrying(false);
    }
  }

  function handleMultiModeChange(v: boolean) {
    setMultiMode(v);
    if (v && multiTargets.length === 0) setMultiTargets([selection]);
  }

  async function handleMultiSend(text: string, targets: ModelSelection[]) {
    try {
      const result = await api.multiSend(conversationId, text, targets);
      const errs: MultiModelError[] = result.responses
        .filter((r) => r.error)
        .map((r) => ({
          provider: r.provider,
          modelId: r.modelId,
          category: r.error!.category,
          message: r.error!.message,
        }));
      setGroupErrors((prev) => ({ ...prev, [result.group.id]: errs }));
      await reload();
      setSendError(null);
      setRetry(null);
      const firstOk = result.responses.find((r) => r.message)?.message;
      if (firstOk) syncActive(firstOk.provider ?? null, firstOk.modelId ?? null);
    } catch (err) {
      setSendError({
        category: err instanceof ApiError ? err.category : undefined,
        message:
          err instanceof ApiError ? err.message : "Multi-model send failed.",
      });
      throw err; // keep the draft
    }
  }

  async function handleGroupSelect(groupId: string, messageId: string) {
    setBusyGroupId(groupId);
    try {
      const g = await api.selectGroupMessage(groupId, messageId);
      setGroups((prev) => ({ ...prev, [g.id]: g }));
      const msg = messages.find((m) => m.id === messageId);
      if (msg) syncActive(msg.provider ?? null, msg.modelId ?? null);
      setCtxVersion((v) => v + 1);
    } catch {
      /* ignore */
    } finally {
      setBusyGroupId(null);
    }
  }

  async function handleCritique(
    groupId: string,
    subjectId: string,
    target: ModelSelection,
  ) {
    setBusyGroupId(groupId);
    try {
      await api.compare(conversationId, subjectId, target.provider, target.modelId);
      await reload();
    } catch (err) {
      setSendError({
        category: err instanceof ApiError ? err.category : undefined,
        message: err instanceof ApiError ? err.message : "Critique failed.",
      });
    } finally {
      setBusyGroupId(null);
    }
  }

  async function handleSynthesize(
    groupId: string,
    sourceIds: string[],
    target: ModelSelection,
  ) {
    setBusyGroupId(groupId);
    try {
      const res = await api.synthesize(
        conversationId,
        sourceIds,
        target.provider,
        target.modelId,
      );
      await reload();
      syncActive(res.message.provider ?? null, res.message.modelId ?? null);
    } catch (err) {
      setSendError({
        category: err instanceof ApiError ? err.category : undefined,
        message: err instanceof ApiError ? err.message : "Synthesis failed.",
      });
    } finally {
      setBusyGroupId(null);
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

  const panel = (
    <LiveContextPanel
      project={project}
      instructions={instructions}
      conversationId={conversationId}
      refreshKey={ctxVersion}
    />
  );

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
                  Send a message below, or enable Multi-model to ask several
                  configured models at once and compare them.
                </p>
              </div>
            </div>
          ) : (
            <MessageTimeline
              messages={messages}
              groups={groups}
              groupErrors={groupErrors}
              targets={modelOptions.filter((o) => o.provider !== "stub")}
              busyGroupId={busyGroupId}
              onSelect={handleGroupSelect}
              onCritique={handleCritique}
              onSynthesize={handleSynthesize}
            />
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
                {retry ? (
                  <>
                    <p className="mt-0.5 text-xs text-tertiary">
                      Your message and history are preserved. Pick a different
                      model in the composer below, then retry.
                    </p>
                    <div className="mt-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={handleRetry}
                        disabled={retrying}
                      >
                        {retrying ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <RefreshCw className="h-3.5 w-3.5" />
                        )}
                        {willSwitch
                          ? `Switch to ${selection.modelId} & Retry`
                          : `Retry with ${selection.modelId}`}
                      </Button>
                    </div>
                  </>
                ) : (
                  <p className="mt-0.5 text-xs text-tertiary">
                    Your draft is preserved. Pick another configured model in the
                    composer below and resend.
                  </p>
                )}
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
          onSendMulti={handleMultiSend}
          options={modelOptions}
          selection={selection}
          onSelect={setSelection}
          multiMode={multiMode}
          onMultiModeChange={handleMultiModeChange}
          multiTargets={multiTargets}
          onMultiTargetsChange={setMultiTargets}
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
