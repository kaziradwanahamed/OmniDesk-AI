"use client";

import * as React from "react";
import { useEffect, useState } from "react";
import { Check, Layers, Loader2, NotebookPen, Pin } from "lucide-react";
import { api } from "@/lib/api-client";
import type { ContextPreview, Project, ProjectInstructions } from "@/lib/types";

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-b border-subtle px-4 py-4">
      <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold tracking-wide text-tertiary uppercase">
        <Icon className="h-3.5 w-3.5" />
        {title}
      </h3>
      {children}
    </section>
  );
}

const LAYER_LABELS: Record<string, string> = {
  system: "App system instructions",
  project_instructions: "Project instructions",
  project_status: "Project status",
  active_task: "Active task",
  decisions: "Decisions",
  recent_messages: "Recent messages",
  summary: "Summary",
  file_excerpts: "File excerpts",
};

function layerLabel(key: string): string {
  const [name, count] = key.split(":");
  const base = LAYER_LABELS[name] ?? name;
  return count ? `${base} (${count})` : base;
}

function omittedLabel(item: Record<string, unknown>): string {
  if (item.type === "recent_message") return `Older turn #${item.sequence_no}`;
  if (item.type === "decisions") return "Decisions (trimmed to fit budget)";
  if (item.type === "status") return "Project status (trimmed to fit budget)";
  return String(item.type ?? "item");
}

export function LiveContextPanel({
  project,
  instructions,
  conversationId,
  refreshKey,
}: {
  project: Project | null;
  instructions: ProjectInstructions | null;
  conversationId: string;
  /** Bump to refetch the preview (e.g. after a send or a model switch). */
  refreshKey?: number;
}) {
  const [preview, setPreview] = useState<ContextPreview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      try {
        const p = await api.getContextPreview(conversationId);
        if (active) setPreview(p);
      } catch {
        if (active) setPreview(null);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [conversationId, refreshKey]);

  const pct = preview
    ? Math.min(100, Math.round((preview.estimatedInputTokens / preview.tokenBudget) * 100))
    : 0;

  return (
    <div className="flex h-full flex-col">
      <div className="shrink-0 border-b border-subtle px-4 py-3.5">
        <h2 className="text-sm font-semibold text-primary">Context Included</h2>
        <p className="mt-0.5 text-xs text-secondary">
          Exactly what the backend assembles and sends on the next turn.
        </p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <Section icon={NotebookPen} title="Project">
          {project ? (
            <>
              <p className="text-sm font-medium text-primary">{project.name}</p>
              {project.description ? (
                <p className="mt-1 text-sm text-secondary">{project.description}</p>
              ) : null}
              {project.goals ? (
                <p className="mt-2 text-xs text-tertiary">
                  <span className="font-medium">Goals:</span> {project.goals}
                </p>
              ) : null}
            </>
          ) : (
            <p className="text-sm text-tertiary">—</p>
          )}
        </Section>

        <Section
          icon={Pin}
          title={
            instructions ? `Instructions (v${instructions.version})` : "Instructions"
          }
        >
          {instructions ? (
            <>
              <p className="text-sm leading-relaxed text-secondary">
                {instructions.content}
              </p>
              {instructions.responseStyle ? (
                <p className="mt-2 text-xs text-tertiary">
                  <span className="font-medium">Style:</span>{" "}
                  {instructions.responseStyle}
                </p>
              ) : null}
            </>
          ) : (
            <p className="text-sm text-tertiary">
              No instructions set yet. Add them in Memory &amp; Instructions.
            </p>
          )}
        </Section>

        <Section icon={Layers} title="Token Budget">
          {loading ? (
            <div className="flex justify-center py-3">
              <Loader2 className="h-4 w-4 animate-spin text-tertiary" />
            </div>
          ) : preview ? (
            <>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="text-secondary">
                  ~{preview.estimatedInputTokens.toLocaleString()} /{" "}
                  {preview.tokenBudget.toLocaleString()} tokens
                </span>
                <span className="font-mono text-tertiary">{pct}%</span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-subtle">
                <div
                  className="h-full rounded-full bg-accent transition-[width]"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <ul className="mt-3 space-y-1">
                {preview.includedLayers.map((layer) => (
                  <li
                    key={layer}
                    className="flex items-center gap-1.5 text-xs text-secondary"
                  >
                    <Check className="h-3 w-3 shrink-0 text-success" />
                    {layerLabel(layer)}
                  </li>
                ))}
              </ul>
              {preview.omittedItems.length ? (
                <div className="mt-3 rounded-lg border border-subtle bg-canvas px-3 py-2">
                  <p className="text-xs font-medium text-tertiary">
                    Excluded this turn
                  </p>
                  <ul className="mt-1 space-y-0.5">
                    {preview.omittedItems.map((item, i) => (
                      <li key={i} className="text-xs text-tertiary">
                        · {omittedLabel(item)}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              <p className="mt-3 text-[11px] text-tertiary">
                Estimated client-side budget. Rolling summaries (layer 6) and file
                excerpts (layer 5) arrive in Phases 7 and 9.
              </p>
            </>
          ) : (
            <p className="text-sm text-tertiary">
              Context preview unavailable.
            </p>
          )}
        </Section>
      </div>
    </div>
  );
}
