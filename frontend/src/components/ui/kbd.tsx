import * as React from "react";
import { cn } from "@/lib/cn";

export function Kbd({ className, ...props }: React.HTMLAttributes<HTMLElement>) {
  return (
    <kbd
      className={cn(
        "inline-flex h-5 min-w-5 items-center justify-center rounded border border-subtle bg-elevated px-1.5 font-mono text-[11px] leading-none text-tertiary",
        className,
      )}
      {...props}
    />
  );
}
