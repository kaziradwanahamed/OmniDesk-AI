"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { Markdown } from "./markdown";
import { ProviderBadge } from "@/components/shared/provider-badge";
import { TimeAgo } from "@/components/shared/time-ago";
import { formatTokens } from "@/lib/format";
import type { ChatMessage } from "@/lib/types";

export function AssistantMessage({ message }: { message: ChatMessage }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  }

  return (
    <div className="group/msg w-full py-5">
      <div className="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1">
        {message.provider ? (
          <ProviderBadge
            provider={message.provider}
            modelId={message.modelId ?? undefined}
          />
        ) : null}
        <TimeAgo
          iso={message.createdAt}
          className="font-mono text-[11px] text-tertiary"
        />
        {message.usage?.totalTokens != null ? (
          <span className="font-mono text-[11px] text-tertiary">
            · {formatTokens(message.usage.totalTokens)} tok
          </span>
        ) : null}
        {message.latencyMs != null ? (
          <span className="font-mono text-[11px] text-tertiary">
            · {(message.latencyMs / 1000).toFixed(1)}s
          </span>
        ) : null}
        <button
          type="button"
          onClick={copy}
          className="ml-auto inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] text-tertiary opacity-0 transition hover:text-primary focus-visible:opacity-100 group-hover/msg:opacity-100"
        >
          {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <Markdown content={message.content} />
      {message.status === "streaming" ? (
        <span className="omni-cursor align-middle" aria-hidden />
      ) : null}
    </div>
  );
}
