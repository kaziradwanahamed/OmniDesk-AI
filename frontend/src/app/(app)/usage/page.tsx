"use client";

import { useEffect, useState } from "react";
import { Info, Loader2, RefreshCw } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ModelTag } from "@/components/shared/provider-badge";
import { api, ApiError, type UsageSummaryUI } from "@/lib/api-client";

function fmt(n: number): string {
  return n.toLocaleString();
}

export default function UsagePage() {
  const [usage, setUsage] = useState<UsageSummaryUI | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const u = await api.getUsage();
        if (active) setUsage(u);
      } catch (e) {
        if (active)
          setError(e instanceof ApiError ? e.message : "Could not load usage.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [reloadKey]);

  const kpis = [
    { label: "Total tokens", value: usage ? fmt(usage.totalTokens) : "N/A" },
    { label: "Input tokens", value: usage ? fmt(usage.inputTokens) : "N/A" },
    { label: "Output tokens", value: usage ? fmt(usage.outputTokens) : "N/A" },
    { label: "Estimated cost", value: "Not configured" },
  ];
  const rows = usage?.byModel ?? [];

  return (
    <>
      <PageHeader
        title="Usage"
        description="Verified provider metadata only"
        actions={
          <Button
            size="sm"
            variant="secondary"
            onClick={() => setReloadKey((k) => k + 1)}
            disabled={loading}
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Refresh
          </Button>
        }
      />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-5xl space-y-5 px-4 py-6">
          {error ? (
            <div className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
              {error}
            </div>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {kpis.map((k) => (
              <Card key={k.label} className="p-4">
                <p className="text-xs font-medium text-tertiary">{k.label}</p>
                <p className="mt-1 font-mono text-xl font-semibold text-primary">
                  {k.value}
                </p>
              </Card>
            ))}
          </div>

          <div className="flex items-start gap-2.5 rounded-lg border border-info/30 bg-info/10 p-3 text-sm">
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-info" />
            <p className="text-secondary">
              Usage appears here from verified provider response metadata after
              your first request. Costs are shown only when you configure
              per-1M-token pricing per model — OmniDesk never fabricates token
              counts or prices.
            </p>
          </div>

          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead className="bg-elevated">
                  <tr>
                    {["Provider / Model", "Requests", "Input", "Output", "Total", "Est. cost"].map(
                      (h) => (
                        <th
                          key={h}
                          className="border-b border-subtle px-3 py-2 text-left font-semibold text-primary"
                        >
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr>
                      <td colSpan={6} className="px-3 py-10 text-center">
                        <Loader2 className="mx-auto h-5 w-5 animate-spin text-tertiary" />
                      </td>
                    </tr>
                  ) : rows.length === 0 ? (
                    <tr>
                      <td
                        colSpan={6}
                        className="px-3 py-10 text-center text-sm text-tertiary"
                      >
                        No usage recorded yet.
                      </td>
                    </tr>
                  ) : (
                    rows.map((r, i) => (
                      <tr key={`${r.provider}:${r.modelId}:${i}`}>
                        <td className="border-b border-subtle px-3 py-2">
                          <ModelTag provider={r.provider} modelId={r.modelId ?? "—"} />
                        </td>
                        <td className="border-b border-subtle px-3 py-2 font-mono text-tertiary">
                          {fmt(r.requestCount)}
                        </td>
                        <td className="border-b border-subtle px-3 py-2 font-mono text-secondary">
                          {fmt(r.inputTokens)}
                        </td>
                        <td className="border-b border-subtle px-3 py-2 font-mono text-secondary">
                          {fmt(r.outputTokens)}
                        </td>
                        <td className="border-b border-subtle px-3 py-2 font-mono text-primary">
                          {fmt(r.totalTokens)}
                        </td>
                        <td className="border-b border-subtle px-3 py-2 text-tertiary">
                          N/A
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
