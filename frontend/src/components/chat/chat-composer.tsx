"use client";

import { useRef, useState } from "react";
import { ArrowUp, Info, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";

/** Composer that clears only on a successful send; if onSend throws, the draft
 * is preserved so the user can retry. */
export function ChatComposer({
  onSend,
}: {
  onSend: (text: string) => Promise<void>;
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
            <span
              className="inline-flex items-center gap-1 rounded-md border border-subtle bg-surface px-2 py-0.5 text-[11px] text-tertiary"
              title="Phase 3 uses a stub echo adapter; real AI providers arrive in Phase 4."
            >
              <Info className="h-3 w-3" />
              Stub echo adapter
            </span>
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
