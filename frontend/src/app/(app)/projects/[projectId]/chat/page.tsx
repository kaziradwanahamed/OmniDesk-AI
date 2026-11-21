"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, MessageSquarePlus } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import { useConversations } from "@/components/conversations/conversations-provider";
import { api } from "@/lib/api-client";

export default function ChatIndexPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = params.projectId;
  const router = useRouter();
  const { conversations, loading, addConversation } = useConversations();
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!loading && conversations.length > 0) {
      router.replace(`/projects/${projectId}/chat/${conversations[0].id}`);
    }
  }, [loading, conversations, projectId, router]);

  async function create() {
    setCreating(true);
    try {
      const c = await api.createConversation(projectId, "New conversation");
      addConversation(c);
      router.replace(`/projects/${projectId}/chat/${c.id}`);
    } catch {
      setCreating(false);
    }
  }

  if (loading || conversations.length > 0) {
    return (
      <>
        <PageHeader title="Chat" />
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-tertiary" />
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader title="Chat" />
      <div className="mx-auto w-full max-w-2xl px-4 py-10">
        <EmptyState
          icon={MessageSquarePlus}
          title="No conversations yet"
          description="Start a conversation to chat within this project. Phase 3 uses a stub echo adapter; real AI providers arrive in Phase 4."
          action={
            <Button onClick={create} disabled={creating}>
              {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              New conversation
            </Button>
          }
        />
      </div>
    </>
  );
}
