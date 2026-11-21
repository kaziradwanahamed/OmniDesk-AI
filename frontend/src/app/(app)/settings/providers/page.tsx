"use client";

import { useState } from "react";
import {
  CheckCircle2,
  CircleDashed,
  Info,
  Loader2,
  XCircle,
} from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { ProviderDot } from "@/components/shared/provider-badge";
import { PROVIDERS, PROVIDER_ORDER } from "@/lib/providers";
import { defaultProviderConfigs } from "@/lib/sample";
import { cn } from "@/lib/cn";
import type { ConnectionStatus, Provider, ProviderConfig } from "@/lib/types";

const CONN: Record<
  ConnectionStatus,
  { label: string; cls: string; Icon: React.ComponentType<{ className?: string }> }
> = {
  connected: {
    label: "Connected",
    cls: "text-success",
    Icon: CheckCircle2,
  },
  untested: { label: "Untested", cls: "text-tertiary", Icon: CircleDashed },
  testing: { label: "Testing…", cls: "text-accent", Icon: Loader2 },
  invalid: { label: "Invalid key", cls: "text-danger", Icon: XCircle },
};

export default function ProvidersPage() {
  const [configs, setConfigs] = useState<ProviderConfig[]>(
    defaultProviderConfigs(),
  );
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  function update(provider: Provider, patch: Partial<ProviderConfig>) {
    setConfigs((cs) =>
      cs.map((c) => (c.provider === provider ? { ...c, ...patch } : c)),
    );
  }

  function saveKey(provider: Provider) {
    const value = (drafts[provider] ?? "").trim();
    if (!value) return;
    update(provider, {
      configured: true,
      keyHint: value.slice(-4),
      connection: "untested",
    });
    setDrafts((d) => ({ ...d, [provider]: "" }));
  }

  function testConnection(provider: Provider) {
    update(provider, { connection: "testing" });
    // No backend yet — reset to untested; real verification runs in Phase 4.
    setTimeout(() => update(provider, { connection: "untested" }), 900);
  }

  return (
    <>
      <PageHeader
        title="Provider Settings"
        description="Bring your own official API keys"
      />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
          <div className="flex items-start gap-2.5 rounded-lg border border-info/30 bg-info/10 p-3 text-sm">
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-info" />
            <p className="text-secondary">
              API billing is separate from your consumer ChatGPT, Claude, or
              Gemini subscriptions. OmniDesk uses the official provider APIs with
              keys you supply, stored server-side and never exposed to the
              browser. Provider quotas and rate limits still apply.
            </p>
          </div>

          {PROVIDER_ORDER.map((p) => {
            const cfg = configs.find((c) => c.provider === p)!;
            const meta = PROVIDERS[p];
            const conn = CONN[cfg.connection];
            return (
              <Card key={p} className="p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <ProviderDot provider={p} />
                    <span className="font-semibold text-primary">
                      {meta.label}
                    </span>
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 rounded-full border border-subtle px-2 py-0.5 text-xs",
                        conn.cls,
                      )}
                    >
                      <conn.Icon
                        className={cn(
                          "h-3 w-3",
                          cfg.connection === "testing" && "animate-spin",
                        )}
                      />
                      {conn.label}
                    </span>
                  </div>
                  <label className="flex items-center gap-2 text-xs text-secondary">
                    Enabled
                    <Switch
                      checked={cfg.isEnabled}
                      onCheckedChange={(v) => update(p, { isEnabled: v })}
                    />
                  </label>
                </div>

                <div className="mt-4 space-y-3">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-secondary">
                      API key
                    </label>
                    {cfg.configured ? (
                      <div className="flex items-center gap-2">
                        <code className="flex h-9 flex-1 items-center rounded-md border border-subtle bg-canvas px-3 font-mono text-sm text-secondary">
                          ••••••••{cfg.keyHint}
                        </code>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            update(p, {
                              configured: false,
                              keyHint: null,
                              connection: "untested",
                            })
                          }
                        >
                          Remove
                        </Button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <Input
                          type="password"
                          value={drafts[p] ?? ""}
                          onChange={(e) =>
                            setDrafts((d) => ({ ...d, [p]: e.target.value }))
                          }
                          placeholder={`Paste your ${meta.label} API key`}
                        />
                        <Button
                          size="sm"
                          onClick={() => saveKey(p)}
                          disabled={!(drafts[p] ?? "").trim()}
                        >
                          Save
                        </Button>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center justify-between">
                    <p className="text-xs text-tertiary">
                      {cfg.enabledModels.length
                        ? `${cfg.enabledModels.length} model(s) enabled`
                        : "No models enabled yet — models can be enabled once a key is verified by the backend (Phase 4)."}
                    </p>
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={!cfg.configured || cfg.connection === "testing"}
                      onClick={() => testConnection(p)}
                    >
                      Test connection
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </div>
    </>
  );
}
