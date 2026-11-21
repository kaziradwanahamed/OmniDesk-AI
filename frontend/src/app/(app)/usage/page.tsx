import { Info } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";

const KPIS = [
  { label: "Total tokens", value: "N/A" },
  { label: "Input tokens", value: "N/A" },
  { label: "Output tokens", value: "N/A" },
  { label: "Estimated cost", value: "Not configured" },
];

export default function UsagePage() {
  return (
    <>
      <PageHeader
        title="Usage"
        description="Verified provider metadata only"
      />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-5xl space-y-5 px-4 py-6">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {KPIS.map((k) => (
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
                    {["Provider", "Model", "Input", "Output", "Total", "Est. cost"].map(
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
                  <tr>
                    <td
                      colSpan={6}
                      className="px-3 py-10 text-center text-sm text-tertiary"
                    >
                      No usage recorded yet.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
