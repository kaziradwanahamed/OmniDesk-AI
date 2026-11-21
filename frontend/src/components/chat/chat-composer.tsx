"use client";

import { useRef, useState } from "react";
import { ArrowUp, Check, ChevronsUpDown, Loader2 } from "lucide-react";
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

/** Composer that clears only on a successful send; the draft is preserved if
 * onSend throws. Includes the provider/model selector. */
export function ChatComposer({
  onSend,
  options,
  selection,
  onSelect,
}: {
  onSend: (text: string) => Promise<void>;
  options: ModelOption[];
  selection: ModelSelection;
  onSelect: (s: ModelSelection) => void;
}) {
  const [value, setValue] = useState("");
  const [sending, setSending] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);

  function autosize() {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }

  async function submit() {
    const text = value.trim();
    if (!text || sending) return;
    setSending(true);
    try {
      await onSend(text);
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

  return (
    <div className="border-t border-subtle bg-canvas/80 px-4 py-3 backdrop-blur">
      <div className="mx-auto w-full max-w-3xl">
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
            placeholder="Message this conversation…"
            disabled={sending}
            className="block max-h-[200px] w-full resize-none bg-transparent px-4 py-3 text-[15px] text-primary outline-none placeholder:text-tertiary"
          />
          <div className="flex items-center gap-2 px-2.5 pb-2.5">
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

            <div className="ml-auto flex items-center gap-2">
              <span className="hidden items-center gap-1 text-[11px] text-tertiary md:flex">
                <Kbd>Enter</Kbd> send
                <span className="mx-1 text-subtle">·</span>
                <Kbd>⇧</Kbd>
                <Kbd>Enter</Kbd> newline
              </span>
              <Button
                size="icon"
                onClick={submit}
                disabled={!value.trim() || sending}
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
