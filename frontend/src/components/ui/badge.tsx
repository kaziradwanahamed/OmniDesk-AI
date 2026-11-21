import * as React from "react";
import { cn } from "@/lib/cn";

export function Badge({
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border border-subtle bg-surface px-2 py-0.5 text-xs font-medium text-secondary",
        className,
      )}
      {...props}
    />
  );
}
