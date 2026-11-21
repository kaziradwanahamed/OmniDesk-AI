"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { api } from "@/lib/api-client";
import type { Conversation } from "@/lib/types";

interface ConversationsCtx {
  projectId: string | null;
  conversations: Conversation[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  addConversation: (c: Conversation) => void;
  updateConversationLocal: (c: Conversation) => void;
  removeConversation: (id: string) => void;
}

const Ctx = createContext<ConversationsCtx | null>(null);

export function useConversations(): ConversationsCtx {
  const ctx = useContext(Ctx);
  if (!ctx)
    throw new Error("useConversations must be used within ConversationsProvider");
  return ctx;
}

export function ConversationsProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const projectId = pathname.match(/^\/projects\/([^/]+)/)?.[1] ?? null;

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      if (!projectId) {
        if (active) setConversations([]);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const list = await api.listConversations(projectId);
        if (active) setConversations(list);
      } catch (e) {
        if (active) {
          setError(e instanceof Error ? e.message : "Failed to load conversations");
          setConversations([]);
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId]);

  async function refresh() {
    if (!projectId) return;
    setLoading(true);
    try {
      setConversations(await api.listConversations(projectId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load conversations");
    } finally {
      setLoading(false);
    }
  }

  const addConversation = (c: Conversation) =>
    setConversations((prev) => [c, ...prev.filter((x) => x.id !== c.id)]);
  const updateConversationLocal = (c: Conversation) =>
    setConversations((prev) => prev.map((x) => (x.id === c.id ? c : x)));
  const removeConversation = (id: string) =>
    setConversations((prev) => prev.filter((x) => x.id !== id));

  return (
    <Ctx.Provider
      value={{
        projectId,
        conversations,
        loading,
        error,
        refresh,
        addConversation,
        updateConversationLocal,
        removeConversation,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}
