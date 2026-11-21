import * as React from "react";
import { cn } from "@/lib/cn";

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: {
  icon?: React.ComponentType<{ className?: string }>;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-subtle px-6 py-12 text-center",
        className,
      )}
    >
      {Icon ? (
        <div className="flex h-11 w-11 items-center justify-center rounded-full border border-subtle bg-elevated text-tertiary">
          <Icon className="h-5 w-5" />
        </div>
      ) : null}
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-primary">{title}</h3>
        {description ? (
          <p className="mx-auto max-w-sm text-sm text-secondary">{description}</p>
        ) : null}
      </div>
      {action}
    </div>
  );
}
