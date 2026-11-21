import * as React from "react";
import { SidebarToggle } from "./sidebar-toggle";

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-3 border-b border-subtle bg-canvas/80 px-4 backdrop-blur">
      <SidebarToggle />
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-sm font-semibold text-primary">{title}</h1>
        {description ? (
          <p className="truncate text-xs text-secondary">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </header>
  );
}
