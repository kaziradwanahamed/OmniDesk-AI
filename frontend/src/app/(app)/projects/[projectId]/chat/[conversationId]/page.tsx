"use client";

import { useParams } from "next/navigation";
import { ChatWorkspace } from "@/components/chat/chat-workspace";

export default function ChatConversationPage() {
  const params = useParams<{ projectId: string; conversationId: string }>();
  return (
    <ChatWorkspace
      projectId={params.projectId}
      conversationId={params.conversationId}
    />
  );
}
