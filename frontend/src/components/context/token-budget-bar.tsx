"use client";

import { Progress } from "@/components/ui/progress";
import { formatTokens } from "@/lib/format";
import type { ContextSnapshot } from "@/lib/types";

export function TokenBudgetBar({ snapshot }: { snapshot: ContextSnapshot }) {
  const pct =
    snapshot.tokenBudget > 0
      ? Math.round((snapshot.estimatedInputTokens / snapshot.tokenBudget) * 100)
      : 0;
  const tone = pct >= 90 ? "bg-danger" : pct >= 70 ? "bg-warning" : "bg-accent";

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-xs">
        <span className="text-secondary">Estimated input</span>
        <span className="font-mono text-tertiary">
          {formatTokens(snapshot.estimatedInputTokens)} /{" "}
          {formatTokens(snapshot.tokenBudget)} ({pct}%)
        </span>
      </div>
      <Progress
        value={snapshot.estimatedInputTokens}
        max={snapshot.tokenBudget}
        indicatorClassName={tone}
      />
    </div>
  );
}
