"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2,
  CircleDashed,
  Info,
  Loader2,
  Plug,
  XCircle,
} from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ProviderDot } from "@/components/shared/provider-badge";
import { PROVIDERS } from "@/lib/providers";
import {
  api,
  ApiError,
  type ProviderConfigUI,
  type TestConnectionResult,
} from "@/lib/api-client";
import { cn } from "@/lib/cn";

function OpenAIProviderCard({
  config,
  onChanged,
}: {
  config: ProviderConfigUI;
  onChanged: (c: ProviderConfigUI) => void;
}) {
  const meta = PROVIDERS.openai;
  const [keyDraft, setKeyDraft] = useState("");
  const [savingKey, setSavingKey] = useState(false);
  const [keyError, setKeyError] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [test, setTest] = useState<TestConnectionResult | null>(null);
  const [enabled, setEnabled] = useState<Set<string>>(
    new Set(config.enabledModels),
  );
  const [savingModels, setSavingModels] = useState(false);
  const [savedModels, setSavedModels] = useState(false);

  async function saveKey() {
    if (!keyDraft.trim()) return;
    setSavingKey(true);
    setKeyError(null);
    try {
      onChanged(await api.setProviderKey("openai", keyDraft.trim()));
      setKeyDraft("");
      setTest(null);
    } catch (e) {
      setKeyError(e instanceof ApiError ? e.message : "Could not save key.");
    } finally {
      setSavingKey(false);
    }
  }

  async function removeKey() {
    try {
      const updated = await api.deleteProviderKey("openai");
      onChanged(updated);
      setTest(null);
    } catch {
      /* ignore */
    }
  }

  async function runTest() {
    setTesting(true);
    try {
      const result = await api.testProvider("openai");
      setTest(result);
    } catch (e) {
      setTest({
        ok: false,
        models: [],
        category: null,
        message: e instanceof ApiError ? e.message : "Test failed.",
      });
    } finally {
      setTesting(false);
    }
  }

  async function saveModels() {
    setSavingModels(true);
    setSavedModels(false);
    try {
      onChanged(await api.setEnabledModels("openai", [...enabled]));
      setSavedModels(true);
      setTimeout(() => setSavedModels(false), 2000);
    } catch {
      /* ignore */
    } finally {
      setSavingModels(false);
    }
  }

  function toggle(model: string) {
    setEnabled((prev) => {
      const next = new Set(prev);
      if (next.has(model)) next.delete(model);
      else next.add(model);
      return next;
    });
  }

  const conn = testing
    ? { label: "Testing…", cls: "text-accent", Icon: Loader2, spin: true }
    : test?.ok
      ? { label: "Connected", cls: "text-success", Icon: CheckCircle2, spin: false }
      : test && !test.ok
        ? { label: "Failed", cls: "text-danger", Icon: XCircle, spin: false }
        : { label: "Untested", cls: "text-tertiary", Icon: CircleDashed, spin: false };

  const availableModels = test?.ok ? test.models : config.enabledModels;

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ProviderDot provider="openai" />
          <span className="font-semibold text-primary">{meta.label}</span>
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full border border-subtle px-2 py-0.5 text-xs",
              conn.cls,
            )}
          >
            <conn.Icon className={cn("h-3 w-3", conn.spin && "animate-spin")} />
            {conn.label}
          </span>
        </div>
      </div>

      <div className="mt-4 space-y-4">
        {/* API key */}
        <div>
          <label className="mb-1 block text-xs font-medium text-secondary">
            API key
          </label>
          {config.configured ? (
            <div className="flex items-center gap-2">
              <code className="flex h-9 flex-1 items-center rounded-md border border-subtle bg-canvas px-3 font-mono text-sm text-secondary">
                ••••••••{config.keyHint}
              </code>
              <Button variant="ghost" size="sm" onClick={removeKey}>
                Remove
              </Button>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <Input
                  type="password"
                  value={keyDraft}
                  onChange={(e) => setKeyDraft(e.target.value)}
                  placeholder="Paste your OpenAI API key (sk-…)"
                />
                <Button
                  size="sm"
                  onClick={saveKey}
                  disabled={savingKey || !keyDraft.trim()}
                >
                  {savingKey ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  Save
                </Button>
              </div>
              {keyError ? (
                <p className="mt-1 text-xs text-danger">{keyError}</p>
              ) : null}
            </>
          )}
        </div>

        {/* Test connection */}
        <div className="flex items-center justify-between">
          <p className="text-xs text-tertiary">
            Test the key to load your available models from OpenAI.
          </p>
          <Button
            variant="secondary"
            size="sm"
            onClick={runTest}
            disabled={!config.configured || testing}
          >
            <Plug className="h-3.5 w-3.5" />
            Test connection
          </Button>
        </div>
        {test && !test.ok ? (
          <p className="text-xs text-danger">
            {test.category ? `${test.category.replaceAll("_", " ")}: ` : ""}
            {test.message}
          </p>
        ) : null}

        {/* Enabled models */}
        {availableModels.length ? (
          <div>
            <div className="mb-1 flex items-center justify-between">
              <label className="text-xs font-medium text-secondary">
                Enabled models{" "}
                <span className="text-tertiary">
                  ({enabled.size} selected)
                </span>
              </label>
              <div className="flex items-center gap-2">
                {savedModels ? (
                  <span className="text-xs text-success">Saved</span>
                ) : null}
                <Button
                  size="sm"
                  onClick={saveModels}
                  disabled={savingModels}
                >
                  {savingModels ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : null}
                  Save models
                </Button>
              </div>
            </div>
            <div className="max-h-56 space-y-0.5 overflow-y-auto rounded-md border border-subtle p-1">
              {availableModels.map((model) => (
                <label
                  key={model}
                  className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-surface"
                >
                  <input
                    type="checkbox"
                    checked={enabled.has(model)}
                    onChange={() => toggle(model)}
                    className="accent-[var(--accent)]"
                  />
                  <span className="font-mono text-xs text-primary">{model}</span>
                </label>
              ))}
            </div>
          </div>
        ) : config.configured ? (
          <p className="text-xs text-tertiary">
            No models loaded yet. Run “Test connection” to fetch the models your
            key can access.
          </p>
        ) : null}
      </div>
    </Card>
  );
}

function ComingSoonCard({ provider }: { provider: "anthropic" | "gemini" }) {
  const meta = PROVIDERS[provider];
  return (
    <Card className="flex items-center justify-between p-4 opacity-70">
      <div className="flex items-center gap-2">
        <ProviderDot provider={provider} />
        <span className="font-semibold text-primary">{meta.label}</span>
      </div>
      <span className="rounded-full border border-subtle px-2 py-0.5 text-xs text-tertiary">
        Available in Phase 5
      </span>
    </Card>
  );
}

export default function ProvidersPage() {
  const [configs, setConfigs] = useState<ProviderConfigUI[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const list = await api.listProviders();
        if (active) setConfigs(list);
      } catch {
        /* ignore */
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const openai =
    configs.find((c) => c.provider === "openai") ??
    ({
      provider: "openai",
      configured: false,
      keyHint: null,
      enabledModels: [],
      isEnabled: true,
    } satisfies ProviderConfigUI);

  function onOpenAIChanged(updated: ProviderConfigUI) {
    setConfigs((prev) => {
      const rest = prev.filter((c) => c.provider !== "openai");
      return [updated, ...rest];
    });
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
              keys you supply, encrypted server-side and never exposed to the
              browser. Provider quotas and rate limits still apply.
            </p>
          </div>

          {loading ? (
            <div className="flex justify-center py-10">
              <Loader2 className="h-6 w-6 animate-spin text-tertiary" />
            </div>
          ) : (
            <>
              <OpenAIProviderCard config={openai} onChanged={onOpenAIChanged} />
              <ComingSoonCard provider="anthropic" />
              <ComingSoonCard provider="gemini" />
            </>
          )}
        </div>
      </div>
    </>
  );
}
