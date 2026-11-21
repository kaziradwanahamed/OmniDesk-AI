import { ProviderDot } from "@/components/shared/provider-badge";
import { PROVIDERS } from "@/lib/providers";
import type { ChatMessage } from "@/lib/types";

/**
 * Subtle timeline divider shown when the active model changes mid-conversation.
 * Phrasing never implies the new provider natively accessed another provider's
 * private history — it continues using OmniDesk's shared project context.
 */
export function ModelSwitchDivider({ message }: { message: ChatMessage }) {
  const to = message.event?.to ?? null;
  const label = to ? PROVIDERS[to.provider].label : "a new model";

  return (
    <div className="my-5 flex items-center gap-3" role="separator">
      <div className="h-px flex-1 bg-subtle" />
      <div className="flex items-center gap-1.5 rounded-full border border-subtle bg-surface px-3 py-1 text-xs text-secondary">
        {to ? <ProviderDot provider={to.provider} /> : null}
        <span>
          Continuing this conversation with{" "}
          <span className="font-medium text-primary">{label}</span> using the
          shared project context.
        </span>
      </div>
      <div className="h-px flex-1 bg-subtle" />
    </div>
  );
}
