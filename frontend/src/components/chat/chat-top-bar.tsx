"use client";

import { PanelRightClose, PanelRightOpen } from "lucide-react";
import { ModelTag } from "@/components/shared/provider-badge";
import { Button } from "@/components/ui/button";
import { SidebarToggle } from "@/components/layout/sidebar-toggle";
import type { Conversation, Project } from "@/lib/types";

export function ChatTopBar({
  project,
  conversation,
  inspectorOpen,
  onToggleInspector,
}: {
  project: Project;
  conversation: Conversation;
  inspectorOpen: boolean;
  onToggleInspector: () => void;
}) {
  return (
    <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-3 border-b border-subtle bg-canvas/80 px-4 backdrop-blur">
      <SidebarToggle />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-sm">
          <span className="truncate font-medium text-primary">
            {project.name}
          </span>
          <span className="text-tertiary">/</span>
          <span className="truncate text-secondary">{conversation.title}</span>
        </div>
      </div>
      {conversation.activeProvider ? (
        <ModelTag
          provider={conversation.activeProvider}
          modelId={conversation.activeModelId}
          className="hidden sm:inline-flex"
        />
      ) : null}
      <Button
        variant="ghost"
        size="icon-sm"
        onClick={onToggleInspector}
        aria-label={inspectorOpen ? "Hide context inspector" : "Show context inspector"}
        aria-pressed={inspectorOpen}
      >
        {inspectorOpen ? (
          <PanelRightClose className="h-4 w-4" />
        ) : (
          <PanelRightOpen className="h-4 w-4" />
        )}
      </Button>
    </header>
  );
}
