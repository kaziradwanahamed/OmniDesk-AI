import * as React from "react";
import { AppFrame } from "@/components/layout/app-frame";
import { AuthProvider } from "@/components/auth/auth-provider";
import { ProjectsProvider } from "@/components/projects/projects-provider";
import { ConversationsProvider } from "@/components/conversations/conversations-provider";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthProvider>
      <ProjectsProvider>
        <ConversationsProvider>
          <AppFrame>{children}</AppFrame>
        </ConversationsProvider>
      </ProjectsProvider>
    </AuthProvider>
  );
}
