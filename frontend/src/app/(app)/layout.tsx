import * as React from "react";
import { AppFrame } from "@/components/layout/app-frame";
import { AuthProvider } from "@/components/auth/auth-provider";
import { ProjectsProvider } from "@/components/projects/projects-provider";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthProvider>
      <ProjectsProvider>
        <AppFrame>{children}</AppFrame>
      </ProjectsProvider>
    </AuthProvider>
  );
}
