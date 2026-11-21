"use client";

import { AlertTriangle, GitCompare, Sparkles } from "lucide-react";
import { Markdown } from "./markdown";
import { ProviderBadge } from "@/components/shared/provider-badge";
import { Button } from "@/components/ui/button";
import type { Provider } from "@/lib/types";

export interface MultiModelColumn {
  provider: Provider;
  modelId: string;
  status: "completed" | "failed";
  content?: string;
  errorLabel?: string;
}

export function MultiModelGrid({
  columns,
  onCritique,
  onSynthesize,
}: {
  columns: MultiModelColumn[];
  onCritique?: () => void;
  onSynthesize?: () => void;
}) {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-medium text-tertiary">
          Multi-model responses · a partial failure never discards successful
          answers
        </span>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="secondary" onClick={onCritique}>
            <GitCompare className="h-3.5 w-3.5" />
            Critique
          </Button>
          <Button size="sm" variant="secondary" onClick={onSynthesize}>
            <Sparkles className="h-3.5 w-3.5" />
            Synthesize
          </Button>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {columns.map((col) => (
          <div
            key={`${col.provider}:${col.modelId}`}
            className="flex flex-col rounded-xl border border-subtle bg-surface"
          >
            <div className="flex items-center justify-between border-b border-subtle px-3 py-2">
              <ProviderBadge provider={col.provider} modelId={col.modelId} />
            </div>
            <div className="min-h-24 p-3">
              {col.status === "failed" ? (
                <div className="flex items-center gap-2 text-sm text-danger">
                  <AlertTriangle className="h-4 w-4" />
                  {col.errorLabel ?? "Provider error"}
                </div>
              ) : (
                <Markdown content={col.content ?? ""} />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
