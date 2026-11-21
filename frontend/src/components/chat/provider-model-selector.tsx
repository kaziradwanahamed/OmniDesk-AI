"use client";

import { Check, ChevronsUpDown } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ProviderDot } from "@/components/shared/provider-badge";
import { PROVIDERS, PROVIDER_ORDER } from "@/lib/providers";
import { cn } from "@/lib/cn";
import type { Provider, ProviderModel } from "@/lib/types";

export function ProviderModelSelector({
  value,
  available,
  onChange,
  align = "start",
  className,
}: {
  value: ProviderModel | null;
  available: Record<Provider, string[]>;
  onChange: (value: ProviderModel) => void;
  align?: "start" | "end";
  className?: string;
}) {
  const hasAny = PROVIDER_ORDER.some((p) => (available[p]?.length ?? 0) > 0);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex h-8 items-center gap-1.5 rounded-md border border-subtle bg-surface px-2.5 text-sm text-primary outline-none transition-colors hover:border-strong focus-visible:ring-2 focus-visible:ring-accent/40",
            className,
          )}
        >
          {value ? (
            <>
              <ProviderDot provider={value.provider} />
              <span>{PROVIDERS[value.provider].label}</span>
              <span className="font-mono text-[11px] text-tertiary">
                {value.modelId}
              </span>
            </>
          ) : (
            <span className="text-secondary">Select model</span>
          )}
          <ChevronsUpDown className="h-3.5 w-3.5 text-tertiary" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align={align} className="min-w-[14rem]">
        {hasAny ? (
          PROVIDER_ORDER.map((p) => {
            const models = available[p] ?? [];
            if (!models.length) return null;
            return (
              <div key={p}>
                <DropdownMenuLabel className="flex items-center gap-1.5">
                  <ProviderDot provider={p} />
                  {PROVIDERS[p].label}
                </DropdownMenuLabel>
                {models.map((m) => (
                  <DropdownMenuItem
                    key={m}
                    onSelect={() => onChange({ provider: p, modelId: m })}
                    className="justify-between"
                  >
                    <span className="font-mono text-xs">{m}</span>
                    {value?.provider === p && value?.modelId === m ? (
                      <Check className="h-3.5 w-3.5 text-accent" />
                    ) : null}
                  </DropdownMenuItem>
                ))}
              </div>
            );
          })
        ) : (
          <div className="px-3 py-6 text-center text-xs text-tertiary">
            No models enabled.
            <br />
            Configure in Provider Settings.
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
