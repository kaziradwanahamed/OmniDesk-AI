"use client";

import { useState } from "react";
import { AlertTriangle, Check, GitCompare, Loader2, Sparkles } from "lucide-react";
import { Markdown } from "./markdown";
import type { ModelOption, ModelSelection } from "./chat-composer";
import { ModelTag } from "@/components/shared/provider-badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import type { ChatMessage } from "@/lib/types";

export interface MultiModelError {
  provider: string;
  modelId: string;
  category: string;
  message: string;
}

function operationOf(m: ChatMessage): string | null {
  const op = m.metadata?.operation;
  return typeof op === "string" ? op : null;
}

function targetKey(s: ModelSelection): string {
  return `${s.provider}::${s.modelId}`;
}

export function MultiModelGrid({
  responses,
  errors = [],
  selectedMessageId,
  targets,
  onSelect,
  onCritique,
  onSynthesize,
  busy = false,
}: {
  responses: ChatMessage[];
  errors?: MultiModelError[];
  selectedMessageId: string | null;
  targets: ModelOption[];
  onSelect: (messageId: string) => void;
  onCritique: (subjectMessageId: string, target: ModelSelection, focus?: string) => void;
  onSynthesize: (sourceMessageIds: string[], target: ModelSelection) => void;
  busy?: boolean;
}) {
  const flat: ModelSelection[] = targets.flatMap((o) =>
    o.models.map((m) => ({ provider: o.provider, modelId: m })),
  );
  const [target, setTarget] = useState<string>(
    flat.length ? targetKey(flat[0]) : "",
  );
  const picked =
    flat.find((s) => targetKey(s) === target) ?? flat[0] ?? null;

  // Original parallel answers (no operation) are the synthesis sources.
  const sources = responses.filter((m) => operationOf(m) === null);

  return (
    <div className="w-full py-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-medium text-tertiary">
          Multi-model responses · a partial failure never discards successful
          answers
        </span>
        {flat.length ? (
          <div className="flex items-center gap-2">
            <select
              aria-label="Target model for compare/synthesize"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              className="h-8 rounded-md border border-subtle bg-surface px-2 font-mono text-[11px] text-primary outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
            >
              {flat.map((s) => (
                <option key={targetKey(s)} value={targetKey(s)}>
                  {s.provider} · {s.modelId}
                </option>
              ))}
            </select>
            <Button
              size="sm"
              variant="secondary"
              disabled={busy || !picked || sources.length < 2}
              onClick={() => picked && onSynthesize(sources.map((m) => m.id), picked)}
            >
              {busy ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Sparkles className="h-3.5 w-3.5" />
              )}
              Synthesize
            </Button>
          </div>
        ) : null}
      </div>

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {responses.map((m) => {
          const op = operationOf(m);
          const selected = m.id === selectedMessageId;
          return (
            <div
              key={m.id}
              className={cn(
                "flex flex-col rounded-xl border bg-surface",
                selected ? "border-accent ring-1 ring-accent/40" : "border-subtle",
              )}
            >
              <div className="flex items-center justify-between gap-2 border-b border-subtle px-3 py-2">
                <ModelTag provider={m.provider} modelId={m.modelId} />
                <div className="flex items-center gap-1.5">
                  {op === "critique" ? (
                    <span className="rounded-full border border-info/40 px-2 py-0.5 text-[10px] font-medium text-info">
                      Critique
                    </span>
                  ) : op === "synthesis" ? (
                    <span className="rounded-full border border-accent/40 px-2 py-0.5 text-[10px] font-medium text-accent">
                      Synthesis
                    </span>
                  ) : null}
                  {selected ? (
                    <span className="inline-flex items-center gap-1 rounded-full border border-accent/40 px-2 py-0.5 text-[10px] font-medium text-accent">
                      <Check className="h-3 w-3" />
                      In context
                    </span>
                  ) : null}
                </div>
              </div>
              <div className="min-h-24 flex-1 p-3 text-sm">
                <Markdown content={m.content} />
              </div>
              <div className="flex items-center justify-between gap-2 border-t border-subtle px-3 py-2">
                <span className="font-mono text-[10px] text-tertiary">
                  {m.usage?.totalTokens != null
                    ? `${m.usage.totalTokens} tok`
                    : "tokens n/a"}
                </span>
                <div className="flex items-center gap-1.5">
                  {op === null && picked ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={busy}
                      onClick={() => onCritique(m.id, picked)}
                      title={`Critique with ${picked.modelId}`}
                    >
                      <GitCompare className="h-3.5 w-3.5" />
                      Critique
                    </Button>
                  ) : null}
                  <Button
                    size="sm"
                    variant={selected ? "secondary" : "ghost"}
                    disabled={busy || selected}
                    onClick={() => onSelect(m.id)}
                  >
                    {selected ? "In context" : "Use in context"}
                  </Button>
                </div>
              </div>
            </div>
          );
        })}

        {errors.map((e) => (
          <div
            key={`${e.provider}:${e.modelId}`}
            className="flex flex-col rounded-xl border border-danger/40 bg-danger/5"
          >
            <div className="flex items-center justify-between border-b border-danger/30 px-3 py-2">
              <ModelTag provider={e.provider} modelId={e.modelId} />
              <span className="text-[10px] font-medium text-danger">
                {e.category.replaceAll("_", " ")}
              </span>
            </div>
            <div className="flex min-h-24 flex-1 items-start gap-2 p-3 text-sm text-danger">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{e.message}</span>
            </div>
            <div className="border-t border-danger/30 px-3 py-2 text-[10px] text-tertiary">
              Not saved — successful answers above are unaffected.
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
