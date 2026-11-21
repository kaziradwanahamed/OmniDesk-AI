import { cn } from "@/lib/cn";
import { PROVIDERS } from "@/lib/providers";
import type { Provider } from "@/lib/types";

export function ProviderDot({
  provider,
  className,
}: {
  provider: Provider;
  className?: string;
}) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-block h-2 w-2 shrink-0 rounded-full bg-current",
        PROVIDERS[provider].dot,
        className,
      )}
    />
  );
}

export function ProviderBadge({
  provider,
  modelId,
  className,
}: {
  provider: Provider;
  modelId?: string | null;
  className?: string;
}) {
  const meta = PROVIDERS[provider];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border border-subtle bg-surface px-2 py-0.5 text-xs font-medium",
        className,
      )}
    >
      <ProviderDot provider={provider} />
      <span className="text-primary">{meta.label}</span>
      {modelId ? (
        <span className="font-mono text-[11px] text-tertiary">{modelId}</span>
      ) : null}
    </span>
  );
}
