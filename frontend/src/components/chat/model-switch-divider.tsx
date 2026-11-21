import { ProviderDot } from "@/components/shared/provider-badge";
import { PROVIDERS } from "@/lib/providers";
import type { ChatMessage, Provider } from "@/lib/types";

/**
 * Subtle timeline divider shown when the active model changes mid-conversation.
 * Phrasing never implies the new provider natively accessed another provider's
 * private history — it continues using OmniDesk's shared project context.
 *
 * Providers are shown honestly: a known provider gets its colored dot + label,
 * any other source (e.g. the "stub" adapter) gets a neutral dot + its raw name.
 */
export function ModelSwitchDivider({ message }: { message: ChatMessage }) {
  const to = message.event?.to ?? null;
  const known =
    to && to.provider in PROVIDERS
      ? PROVIDERS[to.provider as Provider]
      : null;
  const label = known?.label ?? to?.provider ?? "a new model";

  return (
    <div className="my-5 flex items-center gap-3" role="separator">
      <div className="h-px flex-1 bg-subtle" />
      <div className="flex items-center gap-1.5 rounded-full border border-subtle bg-surface px-3 py-1 text-xs text-secondary">
        {known ? (
          <ProviderDot provider={known.id} />
        ) : to ? (
          <span
            className="inline-block h-2 w-2 shrink-0 rounded-full bg-tertiary"
            aria-hidden
          />
        ) : null}
        <span>
          Continuing this conversation with{" "}
          <span className="font-medium text-primary capitalize">{label}</span>{" "}
          using the shared project context.
        </span>
      </div>
      <div className="h-px flex-1 bg-subtle" />
    </div>
  );
}
