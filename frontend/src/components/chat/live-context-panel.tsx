"use client";

import * as React from "react";
import { useEffect, useState } from "react";
import {
  Check,
  FileText,
  Layers,
  Loader2,
  NotebookPen,
  Pencil,
  Pin,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError } from "@/lib/api-client";
import type {
  ContextPreview,
  Project,
  ProjectInstructions,
  SummaryStatus,
} from "@/lib/types";

function Section({
  icon: Icon,
  title,
  action,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="border-b border-subtle px-4 py-4">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-tertiary uppercase">
          <Icon className="h-3.5 w-3.5" />
          {title}
        </h3>
        {action}
      </div>
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
  if (item.type === "summary") return "Summary (trimmed to fit budget)";
  if (item.type === "decisions") return "Decisions (trimmed to fit budget)";
  if (item.type === "status") return "Project status (trimmed to fit budget)";
  if (item.type === "file_excerpt")
    return `File excerpt (${item.file ?? "file"}, chunk ${Number(item.chunk_index ?? 0) + 1}) trimmed`;
  return String(item.type ?? "item");
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
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
  /** Bump to refetch (e.g. after a send or a model switch). */
  refreshKey?: number;
}) {
  const [preview, setPreview] = useState<ContextPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [summaryStatus, setSummaryStatus] = useState<SummaryStatus | null>(null);

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [working, setWorking] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  async function reload() {
    const [p, s] = await Promise.allSettled([
      api.getContextPreview(conversationId),
      api.getSummary(conversationId),
    ]);
    setPreview(p.status === "fulfilled" ? p.value : null);
    setSummaryStatus(s.status === "fulfilled" ? s.value : null);
  }

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      setEditing(false);
      setSummaryError(null);
      const [p, s] = await Promise.allSettled([
        api.getContextPreview(conversationId),
        api.getSummary(conversationId),
      ]);
      if (!active) return;
      setPreview(p.status === "fulfilled" ? p.value : null);
      setSummaryStatus(s.status === "fulfilled" ? s.value : null);
      setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, [conversationId, refreshKey]);

  const summary = summaryStatus?.summary ?? null;

  async function refreshSummary() {
    setWorking(true);
    setSummaryError(null);
    try {
      setSummaryStatus(await api.refreshSummary(conversationId));
      await reload();
    } catch (e) {
      setSummaryError(
        e instanceof ApiError
          ? `${e.category ? e.category.replaceAll("_", " ") + ": " : ""}${e.message}`
          : "Could not generate summary.",
      );
    } finally {
      setWorking(false);
    }
  }

  async function saveSummary() {
    setWorking(true);
    setSummaryError(null);
    try {
      await api.editSummary(conversationId, draft);
      setEditing(false);
      await reload();
    } catch (e) {
      setSummaryError(e instanceof ApiError ? e.message : "Could not save summary.");
    } finally {
      setWorking(false);
    }
  }

  async function clearSummary() {
    setWorking(true);
    setSummaryError(null);
    try {
      await api.clearSummary(conversationId);
      await reload();
    } catch (e) {
      setSummaryError(e instanceof ApiError ? e.message : "Could not clear summary.");
    } finally {
      setWorking(false);
    }
  }

  const pct = preview
    ? Math.min(100, Math.round((preview.estimatedInputTokens / preview.tokenBudget) * 100))
    : 0;
  const summarized = Boolean(summary);
  const trimmedCount = preview
    ? preview.omittedItems.filter((o) => o.type === "recent_message").length
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
            <p className="text-sm leading-relaxed text-secondary">
              {instructions.content}
            </p>
          ) : (
            <p className="text-sm text-tertiary">
              No instructions set yet. Add them in Memory &amp; Instructions.
            </p>
          )}
        </Section>

        {/* L6 — rolling conversation summary */}
        <Section
          icon={Sparkles}
          title={summary ? `Summary (v${summary.version})` : "Summary"}
          action={
            <div className="flex items-center gap-1">
              {summary ? (
                <Button
                  size="icon-sm"
                  variant="ghost"
                  aria-label="Edit summary"
                  disabled={working}
                  onClick={() => {
                    setDraft(summary.content);
                    setEditing((v) => !v);
                  }}
                >
                  <Pencil className="h-3.5 w-3.5" />
                </Button>
              ) : null}
              <Button
                size="icon-sm"
                variant="ghost"
                aria-label="Generate or refresh summary"
                disabled={working}
                onClick={refreshSummary}
              >
                {working ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="h-3.5 w-3.5" />
                )}
              </Button>
            </div>
          }
        >
          {editing && summary ? (
            <div className="space-y-2">
              <Textarea
                rows={6}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
              />
              <div className="flex justify-end gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={working}
                  onClick={() => setEditing(false)}
                >
                  Cancel
                </Button>
                <Button size="sm" disabled={working || !draft.trim()} onClick={saveSummary}>
                  {working ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  Save
                </Button>
              </div>
            </div>
          ) : summary ? (
            <>
              <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                <Badge
                  className={
                    summary.userEdited
                      ? "border-accent/40 text-accent"
                      : "border-subtle text-tertiary"
                  }
                >
                  {summary.userEdited
                    ? "User-edited"
                    : `AI · ${summary.provider ?? "model"}`}
                </Badge>
                <span className="text-[11px] text-tertiary">
                  Covers {summary.coveredMessageCount} msgs · {formatDate(summary.updatedAt)}
                </span>
              </div>
              <p className="text-sm leading-relaxed whitespace-pre-wrap text-secondary">
                {summary.content}
              </p>
              <button
                type="button"
                onClick={clearSummary}
                disabled={working}
                className="mt-2 text-[11px] text-tertiary underline-offset-2 hover:text-danger hover:underline disabled:opacity-50"
              >
                Clear summary
              </button>
            </>
          ) : (
            <>
              <p className="text-sm text-tertiary">
                No summary yet. Older turns are sent in full.
              </p>
              {summaryStatus?.needsSummary ? (
                <div className="mt-2 flex items-start gap-2 rounded-lg border border-info/30 bg-info/10 p-2.5 text-xs text-secondary">
                  <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-info" />
                  <span>
                    {summaryStatus.unsummarizedCount} messages are unsummarized.
                    Generate a rolling summary to keep context tight.
                  </span>
                </div>
              ) : null}
              <Button
                size="sm"
                variant="secondary"
                className="mt-2"
                disabled={working}
                onClick={refreshSummary}
              >
                {working ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                Generate summary
              </Button>
            </>
          )}
          {summaryError ? (
            <p className="mt-2 text-xs text-danger">{summaryError}</p>
          ) : null}
        </Section>

        {/* L5 — retrieved file excerpts (pinned + query-matched) */}
        <Section
          icon={FileText}
          title={
            preview && preview.fileExcerpts.length
              ? `File Excerpts (${preview.fileExcerpts.length})`
              : "File Excerpts"
          }
        >
          {preview && preview.fileExcerpts.length ? (
            <ul className="space-y-1.5">
              {preview.fileExcerpts.map((e, i) => (
                <li
                  key={`${e.filename}:${e.chunkIndex}:${i}`}
                  className="flex items-center justify-between gap-2 text-xs"
                >
                  <span className="flex min-w-0 items-center gap-1.5 text-secondary">
                    <FileText className="h-3 w-3 shrink-0 text-tertiary" />
                    <span className="truncate font-mono">
                      {e.filename} · chunk {e.chunkIndex + 1}
                    </span>
                    <Badge
                      className={
                        e.pinned
                          ? "border-accent/40 text-accent"
                          : "border-subtle text-tertiary"
                      }
                    >
                      {e.pinned ? "pinned" : "matched"}
                    </Badge>
                  </span>
                  <span className="shrink-0 font-mono text-tertiary">
                    ~{e.tokenEst.toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-tertiary">
              No file excerpts. Pin a project file (Files tab) to always ground
              answers in it, or they surface here when relevant to your message.
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
                    className="flex items-center justify-between gap-2 text-xs"
                  >
                    <span className="flex items-center gap-1.5 text-secondary">
                      <Check className="h-3 w-3 shrink-0 text-success" />
                      {layerLabel(layer)}
                    </span>
                    <span className="font-mono text-tertiary">
                      ~{(preview.layerTokens[layer] ?? 0).toLocaleString()}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-[11px] text-tertiary">
                {summarized
                  ? "Older turns are compacted into the summary (L6)."
                  : trimmedCount > 0
                    ? `${trimmedCount} older turn(s) trimmed to fit the budget.`
                    : "All turns fit; nothing trimmed."}
              </p>
              {preview.omittedItems.length ? (
                <div className="mt-2 rounded-lg border border-subtle bg-canvas px-3 py-2">
                  <p className="text-xs font-medium text-tertiary">Excluded this turn</p>
                  <ul className="mt-1 space-y-0.5">
                    {preview.omittedItems.map((item, i) => (
                      <li key={i} className="text-xs text-tertiary">
                        · {omittedLabel(item)}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              <p className="mt-2 text-[11px] text-tertiary">
                Conservative estimate across all 8 layers (L1–L8), including any
                retrieved file excerpts (L5).
              </p>
            </>
          ) : (
            <p className="text-sm text-tertiary">Context preview unavailable.</p>
          )}
        </Section>
      </div>
    </div>
  );
}
