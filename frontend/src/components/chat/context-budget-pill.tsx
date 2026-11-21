"use client";

import { Gauge } from "lucide-react";
import { cn } from "@/lib/cn";
import { formatTokens } from "@/lib/format";

export function ContextBudgetPill({
  used,
  budget,
  onClick,
}: {
  used: number;
  budget: number;
  onClick?: () => void;
}) {
  const pct = budget > 0 ? Math.min(100, Math.round((used / budget) * 100)) : 0;
  const tone =
    pct >= 90 ? "text-danger" : pct >= 70 ? "text-warning" : "text-tertiary";

  return (
    <button
      type="button"
      onClick={onClick}
      title="Context budget — open the Context Included inspector"
      className="inline-flex h-8 items-center gap-1.5 rounded-md border border-subtle bg-surface px-2.5 text-xs text-secondary outline-none transition-colors hover:border-strong focus-visible:ring-2 focus-visible:ring-accent/40"
    >
      <Gauge className={cn("h-3.5 w-3.5", tone)} />
      <span className="font-mono">
        {formatTokens(used)} / {formatTokens(budget)}
      </span>
    </button>
  );
}
