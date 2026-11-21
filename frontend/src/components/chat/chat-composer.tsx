"use client";

import { useRef, useState } from "react";
import {
  ArrowUp,
  Check,
  ChevronsUpDown,
  Columns3,
  Info,
  Loader2,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { PROVIDERS } from "@/lib/providers";
import { cn } from "@/lib/cn";

export interface ModelOption {
  provider: string;
  label: string;
  models: string[];
}
export interface ModelSelection {
  provider: string;
  modelId: string;
}

function dotClass(provider: string): string {
  const known = (PROVIDERS as Record<string, { dot: string }>)[provider];
  return known ? known.dot : "text-tertiary";
}

/** Composer that clears only on a successful send; the draft is preserved if the
 * send throws. Supports single-model (default) and opt-in multi-model fan-out. */
export function ChatComposer({
  onSend,
  onSendMulti,
  options,
  selection,
  onSelect,
  multiMode,
  onMultiModeChange,
  multiTargets,
  onMultiTargetsChange,
}: {
  onSend: (text: string) => Promise<void>;
  onSendMulti: (text: string, targets: ModelSelection[]) => Promise<void>;
  options: ModelOption[];
  selection: ModelSelection;
  onSelect: (s: ModelSelection) => void;
  multiMode: boolean;
  onMultiModeChange: (v: boolean) => void;
  multiTargets: ModelSelection[];
  onMultiTargetsChange: (t: ModelSelection[]) => void;
}) {
  const [value, setValue] = useState("");
  const [sending, setSending] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);

  const flat = options.flatMap((o) =>
    o.models.map((m) => ({ provider: o.provider, label: o.label, modelId: m })),
  );
  const isPicked = (p: string, m: string) =>
    multiTargets.some((t) => t.provider === p && t.modelId === m);
  function toggleTarget(p: string, m: string) {
    if (isPicked(p, m)) {
      onMultiTargetsChange(
        multiTargets.filter((t) => !(t.provider === p && t.modelId === m)),
      );
    } else {
      onMultiTargetsChange([...multiTargets, { provider: p, modelId: m }]);
    }
  }

  function autosize() {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }

  const canSend =
    value.trim() && !sending && (!multiMode || multiTargets.length >= 2);

  async function submit() {
    const text = value.trim();
    if (!text || sending) return;
    if (multiMode && multiTargets.length < 2) return;
    setSending(true);
    try {
      if (multiMode) await onSendMulti(text, multiTargets);
      else await onSend(text);
      setValue("");
      requestAnimationFrame(() => {
        if (ref.current) ref.current.style.height = "auto";
      });
    } catch {
      /* keep the draft on failure */
    } finally {
      setSending(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void submit();
    }
  }

  const multiLabel = multiTargets.map((t) => t.modelId).join(", ");

  return (
    <div className="border-t border-subtle bg-canvas/80 px-4 py-3 backdrop-blur">
      <div className="mx-auto w-full max-w-3xl">
        {multiMode ? (
          <div className="mb-2 rounded-lg border border-subtle bg-surface p-2.5">
            <div className="mb-1.5 flex items-center justify-between">
              <span className="text-xs font-medium text-secondary">
                Multi-model — pick 2+ models
              </span>
              <span className="text-[11px] text-tertiary">
                {multiTargets.length} selected
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {flat.map((f) => {
                const picked = isPicked(f.provider, f.modelId);
                return (
                  <button
                    key={`${f.provider}:${f.modelId}`}
                    type="button"
                    onClick={() => toggleTarget(f.provider, f.modelId)}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition-colors",
                      picked
                        ? "border-accent/50 bg-accent/10 text-primary"
                        : "border-subtle text-secondary hover:border-strong",
                    )}
                  >
                    <span
                      className={cn(
                        "inline-block h-2 w-2 rounded-full bg-current",
                        dotClass(f.provider),
                      )}
                      aria-hidden
                    />
                    <span className="font-mono text-[11px]">{f.modelId}</span>
                    {picked ? <Check className="h-3 w-3 text-accent" /> : null}
                  </button>
                );
              })}
            </div>
            {multiTargets.length >= 1 ? (
              <div className="mt-2 flex items-start gap-1.5 text-[11px] text-tertiary">
                <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>
                  Sends {multiTargets.length} separate API request
                  {multiTargets.length === 1 ? "" : "s"}
                  {multiLabel ? ` (${multiLabel})` : ""}. Each provider bills
                  independently under your own API keys.
                </span>
              </div>
            ) : null}
          </div>
        ) : null}

        <div className="rounded-xl border border-subtle bg-surface shadow-sm transition-colors focus-within:border-strong">
          <textarea
            ref={ref}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              autosize();
            }}
            onKeyDown={onKeyDown}
            rows={1}
            placeholder={
              multiMode
                ? "Message all selected models…"
                : "Message this conversation…"
            }
            disabled={sending}
            className="block max-h-[200px] w-full resize-none bg-transparent px-4 py-3 text-[15px] text-primary outline-none placeholder:text-tertiary"
          />
          <div className="flex items-center gap-2 px-2.5 pb-2.5">
            {multiMode ? (
              <span className="text-xs text-tertiary">
                {multiTargets.length < 2
                  ? "Select at least 2 models"
                  : `${multiTargets.length} models`}
              </span>
            ) : (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    className="inline-flex h-8 items-center gap-1.5 rounded-md border border-subtle bg-surface px-2.5 text-sm text-primary outline-none transition-colors hover:border-strong focus-visible:ring-2 focus-visible:ring-accent/40"
                  >
                    <span
                      className={cn(
                        "inline-block h-2 w-2 rounded-full bg-current",
                        dotClass(selection.provider),
                      )}
                      aria-hidden
                    />
                    <span className="font-mono text-[11px] text-tertiary">
                      {selection.modelId}
                    </span>
                    <ChevronsUpDown className="h-3.5 w-3.5 text-tertiary" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  align="start"
                  className="max-h-72 min-w-[13rem] overflow-y-auto"
                >
                  {options.map((opt) => (
                    <div key={opt.provider}>
                      <DropdownMenuLabel className="flex items-center gap-1.5">
                        <span
                          className={cn(
                            "inline-block h-2 w-2 rounded-full bg-current",
                            dotClass(opt.provider),
                          )}
                        />
                        {opt.label}
                      </DropdownMenuLabel>
                      {opt.models.map((m) => (
                        <DropdownMenuItem
                          key={`${opt.provider}:${m}`}
                          onSelect={() =>
                            onSelect({ provider: opt.provider, modelId: m })
                          }
                          className="justify-between"
                        >
                          <span className="font-mono text-xs">{m}</span>
                          {selection.provider === opt.provider &&
                          selection.modelId === m ? (
                            <Check className="h-3.5 w-3.5 text-accent" />
                          ) : null}
                        </DropdownMenuItem>
                      ))}
                    </div>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            )}

            <button
              type="button"
              onClick={() => onMultiModeChange(!multiMode)}
              aria-pressed={multiMode}
              className={cn(
                "inline-flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-xs transition-colors",
                multiMode
                  ? "border-accent/50 bg-accent/10 text-primary"
                  : "border-subtle text-secondary hover:border-strong",
              )}
            >
              <Columns3 className="h-3.5 w-3.5" />
              Multi-model
            </button>

            <div className="ml-auto flex items-center gap-2">
              <span className="hidden items-center gap-1 text-[11px] text-tertiary md:flex">
                <Kbd>Enter</Kbd> send
              </span>
              <Button
                size="icon"
                onClick={submit}
                disabled={!canSend}
                aria-label="Send message"
              >
                {sending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ArrowUp className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
