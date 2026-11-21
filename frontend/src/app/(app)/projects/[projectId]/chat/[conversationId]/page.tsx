"use client";

import { useParams } from "next/navigation";
import { ChatWorkspace } from "@/components/chat/chat-workspace";
import { sampleConversations, sampleProjects } from "@/lib/sample";

export default function ChatPage() {
  const params = useParams<{ projectId: string; conversationId: string }>();

  const project =
    sampleProjects.find((p) => p.id === params.projectId) ?? sampleProjects[0];
  const conversation =
    sampleConversations.find((c) => c.id === params.conversationId) ??
    sampleConversations.find((c) => c.projectId === project.id) ??
    sampleConversations[0];

  return <ChatWorkspace project={project} conversation={conversation} />;
}
