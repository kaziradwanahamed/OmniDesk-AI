"use client";

import { AlertTriangle, RefreshCw, X } from "lucide-react";
import { ProviderModelSelector } from "./provider-model-selector";
import { Button } from "@/components/ui/button";
import type { Provider, ProviderError, ProviderModel } from "@/lib/types";

const CATEGORY_LABEL: Record<ProviderError["category"], string> = {
  AUTH_INVALID_KEY: "Invalid API key",
  RATE_LIMITED: "Rate limited",
  QUOTA_EXCEEDED: "Quota exceeded",
  BILLING_REQUIRED: "Billing required",
  CONTEXT_TOO_LARGE: "Context too large",
  MODEL_UNAVAILABLE: "Provider unavailable",
  TIMEOUT: "Request timed out",
};

export function ErrorRecoveryBanner({
  error,
  available,
  selection,
  onSelect,
  onRetry,
  onDismiss,
}: {
  error: ProviderError;
  available: Record<Provider, string[]>;
  selection: ProviderModel | null;
  onSelect: (value: ProviderModel) => void;
  onRetry: () => void;
  onDismiss: () => void;
}) {
  return (
    <div className="mx-auto my-3 w-full max-w-3xl rounded-lg border border-danger/40 bg-danger/10 p-3">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-primary">
              {CATEGORY_LABEL[error.category]}
            </span>
            <span className="rounded bg-danger/15 px-1.5 py-0.5 font-mono text-[10px] text-danger">
              {error.category}
            </span>
          </div>
          <p className="mt-0.5 text-sm text-secondary">
            {error.message}
            {error.retryAfterSeconds
              ? ` Retry after ~${error.retryAfterSeconds}s.`
              : ""}
          </p>
          <p className="mt-1 text-xs text-tertiary">
            Your draft and history are preserved. Switching providers does not
            bypass provider limits or quotas.
          </p>
          <div className="mt-2.5 flex flex-wrap items-center gap-2">
            <ProviderModelSelector
              value={selection}
              available={available}
              onChange={onSelect}
            />
            <Button size="sm" variant="secondary" onClick={onRetry}>
              <RefreshCw className="h-3.5 w-3.5" />
              Switch model &amp; retry
            </Button>
          </div>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss"
          className="rounded p-1 text-tertiary transition-colors hover:text-primary"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
