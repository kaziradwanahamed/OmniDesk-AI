"use client";

import { useRef, useState } from "react";
import { ArrowUp, Layers, Square } from "lucide-react";
import { ProviderModelSelector } from "./provider-model-selector";
import { ContextBudgetPill } from "./context-budget-pill";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { Switch } from "@/components/ui/switch";
import type { Provider, ProviderModel } from "@/lib/types";

export function Composer({
  selection,
  available,
  onSelect,
  multiModel,
  onToggleMultiModel,
  streaming,
  onSend,
  onStop,
  budgetUsed,
  budgetTotal,
  onOpenInspector,
}: {
  selection: ProviderModel | null;
  available: Record<Provider, string[]>;
  onSelect: (value: ProviderModel) => void;
  multiModel: boolean;
  onToggleMultiModel: (value: boolean) => void;
  streaming: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
  budgetUsed: number;
  budgetTotal: number;
  onOpenInspector: () => void;
}) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  function autosize() {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }

  function submit() {
    const text = value.trim();
    if (!text || streaming) return;
    onSend(text);
    setValue("");
    requestAnimationFrame(() => {
      if (ref.current) ref.current.style.height = "auto";
    });
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
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
            placeholder="Message the shared project conversation…"
            className="block max-h-[200px] w-full resize-none bg-transparent px-4 py-3 text-[15px] text-primary outline-none placeholder:text-tertiary"
          />
          <div className="flex flex-wrap items-center gap-2 px-2.5 pb-2.5">
            <ProviderModelSelector
              value={selection}
              available={available}
              onChange={onSelect}
            />
            <ContextBudgetPill
              used={budgetUsed}
              budget={budgetTotal}
              onClick={onOpenInspector}
            />
            <label className="inline-flex cursor-pointer items-center gap-1.5 text-xs text-secondary">
              <Switch checked={multiModel} onCheckedChange={onToggleMultiModel} />
              <span className="inline-flex items-center gap-1">
                <Layers className="h-3.5 w-3.5" />
                Multi-model
              </span>
            </label>
            <div className="ml-auto flex items-center gap-2">
              <span className="hidden items-center gap-1 text-[11px] text-tertiary md:flex">
                <Kbd>Enter</Kbd> send
                <span className="mx-1 text-subtle">·</span>
                <Kbd>⇧</Kbd>
                <Kbd>Enter</Kbd> newline
              </span>
              {streaming ? (
                <Button
                  size="icon"
                  variant="secondary"
                  onClick={onStop}
                  aria-label="Stop generating"
                >
                  <Square className="h-4 w-4" />
                </Button>
              ) : (
                <Button
                  size="icon"
                  onClick={submit}
                  disabled={!value.trim()}
                  aria-label="Send message"
                >
                  <ArrowUp className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
